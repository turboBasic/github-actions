import os
import sys
from collections.abc import Mapping
from pathlib import Path

from . import annotate, emit, emit_environment, repository_directory

MANIFESTS = {
    "uv": "uv.lock",
    "cargo": "Cargo.lock",
    "go": "go.mod",
    "npm": "package-lock.json",
}

PRUNED_DIRECTORIES = {".git", ".venv", "node_modules", "target", "venv"}

OVERRIDES = {
    "uv": "TBGA_UV_CACHE_PATH",
    "cargo-home": "TBGA_CARGO_HOME_PATH",
    "cargo-target": "TBGA_CARGO_TARGET_CACHE_PATH",
    "go-module": "TBGA_GO_MODULE_CACHE_PATH",
    "go-build": "TBGA_GO_BUILD_CACHE_PATH",
    "npm": "TBGA_NPM_CACHE_PATH",
}

PATH_ERRORS = (OSError, RuntimeError, ValueError)


def discover(root: Path) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = {name: [] for name in MANIFESTS}
    names = {manifest: ecosystem for ecosystem, manifest in MANIFESTS.items()}
    for directory, children, files in os.walk(root):
        base = Path(directory)
        children[:] = sorted(
            child
            for child in children
            if child not in PRUNED_DIRECTORIES and not (base / child).is_symlink()
        )
        for file in files:
            if ecosystem := names.get(file):
                found[ecosystem].append(base / file)
    return {name: sorted(paths) for name, paths in found.items()}


def _home(environment: Mapping[str, str]) -> Path:
    return Path(environment.get("HOME") or environment.get("USERPROFILE") or Path.home())


def _cache_home(environment: Mapping[str, str], system: str, home: Path) -> Path:
    if system == "win32":
        return Path(environment.get("LOCALAPPDATA") or home / "AppData/Local")
    if system == "darwin":
        return home / "Library/Caches"
    return Path(environment.get("XDG_CACHE_HOME") or home / ".cache")


def _native_path(value: str | Path, root: Path, home: Path) -> Path:
    try:
        return _path(str(value), root, home)
    except PATH_ERRORS:
        return (root / "cache").resolve()


def _path(value: str, root: Path, home: Path) -> Path:
    if "\n" in value or "\r" in value or "\0" in value:
        raise ValueError("cache path must be a single path")
    if value == "~":
        path = home
    elif value.startswith("~/") or value.startswith("~\\"):
        path = home / value[2:]
    else:
        path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _selected_path(
    name: str,
    default: list[Path],
    root: Path,
    home: Path,
    environment: Mapping[str, str],
) -> list[Path]:
    override = environment.get(OVERRIDES[name], "")
    if not override:
        return default
    try:
        return [_path(override, root, home)]
    except PATH_ERRORS:
        return default


def _go_path(environment: Mapping[str, str], home: Path, system: str) -> Path:
    if environment.get("GOMODCACHE"):
        return Path(environment["GOMODCACHE"])
    gopath = environment.get("GOPATH", "")
    if gopath:
        separator = ";" if system == "win32" else ":"
        return Path(gopath.split(separator)[0]) / "pkg/mod"
    return home / "go/pkg/mod"


def _native_paths(
    root: Path, environment: Mapping[str, str], system: str, found: dict[str, list[Path]]
) -> dict[str, list[Path]]:
    home = _home(environment)
    cache_home = _cache_home(environment, system, home)
    cargo_home = _native_path(environment.get("CARGO_HOME") or home / ".cargo", root, home)
    local_app_data = Path(environment.get("LOCALAPPDATA") or home / "AppData/Local")
    uv = _native_path(
        environment.get("UV_CACHE_DIR")
        or (local_app_data / "uv/cache" if system == "win32" else cache_home / "uv"),
        root,
        home,
    )
    cargo_target = environment.get("CARGO_TARGET_DIR") or environment.get(
        "CARGO_BUILD_TARGET_DIR", ""
    )
    target_paths = (
        [_native_path(cargo_target, root, home)]
        if cargo_target
        else [lockfile.parent / "target" for lockfile in found["cargo"]]
    )
    gocache = _native_path(environment.get("GOCACHE") or cache_home / "go-build", root, home)
    npm_cache = environment.get("npm_config_cache") or environment.get("NPM_CONFIG_CACHE", "")
    npm = _native_path(
        npm_cache or (local_app_data / "npm-cache" if system == "win32" else home / ".npm"),
        root,
        home,
    )
    return {
        "uv": [uv],
        "cargo-home": [cargo_home],
        "cargo-target": target_paths,
        "go-module": [_native_path(_go_path(environment, home, system), root, home)],
        "go-build": [gocache],
        "npm": [npm],
    }


def plan(root: Path, environment: Mapping[str, str], system: str) -> dict[str, str]:
    found = discover(root)
    native = _native_paths(root, environment, system, found)
    outputs = {f"{name}-found": str(bool(paths)).lower() for name, paths in found.items()}
    home = _home(environment)
    for ecosystem, manifests in found.items():
        if not manifests:
            continue
        locations = (
            ("uv",)
            if ecosystem == "uv"
            else ("cargo-home", "cargo-target")
            if ecosystem == "cargo"
            else ("go-module", "go-build")
            if ecosystem == "go"
            else ("npm",)
        )
        for name in locations:
            paths = _selected_path(name, native[name], root, home, environment)
            if name == "cargo-home":
                outputs["cargo-registry-path"] = str(paths[0] / "registry")
                outputs["cargo-git-path"] = str(paths[0] / "git")
            else:
                outputs[f"{name}-path"] = "\n".join(str(path) for path in paths)
    return outputs


def run() -> int:
    root = Path(repository_directory()).resolve()
    outputs = plan(root, os.environ, sys.platform)
    for name, value in outputs.items():
        if not name.endswith("-path"):
            continue
        for path in value.splitlines():
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
            except OSError:
                annotate(
                    "warning", f"Could not prepare the {name} cache directory; cache use may fail"
                )
    emit(**outputs)
    selected: dict[str, str] = {}
    for input_name, variable, output_name in (
        ("uv", "UV_CACHE_DIR", "uv-path"),
        ("cargo-home", "CARGO_HOME", "cargo-registry-path"),
        ("cargo-target", "CARGO_TARGET_DIR", "cargo-target-path"),
        ("go-module", "GOMODCACHE", "go-module-path"),
        ("go-build", "GOCACHE", "go-build-path"),
        ("npm", "npm_config_cache", "npm-path"),
    ):
        if os.environ.get(OVERRIDES[input_name]) and output_name in outputs:
            selected[variable] = (
                str(Path(outputs[output_name]).parent)
                if input_name == "cargo-home"
                else outputs[output_name]
            )
    emit_environment(**selected)
    return 0
