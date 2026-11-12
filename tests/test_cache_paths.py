from pathlib import Path

import pytest

from tbga import cache_paths


def touch(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_discover_reads_supported_manifests_recursively_and_skips_generated_dirs(
    tmp_path: Path,
) -> None:
    touch(tmp_path, "uv.lock")
    touch(tmp_path, "crates/Cargo.lock")
    touch(tmp_path, "tools/go.mod")
    touch(tmp_path, "frontend/package-lock.json")
    touch(tmp_path, "node_modules/dependency/package-lock.json")
    touch(tmp_path, "target/dependency/Cargo.lock")

    found = cache_paths.discover(tmp_path)

    assert found == {
        "uv": [tmp_path / "uv.lock"],
        "cargo": [tmp_path / "crates/Cargo.lock"],
        "go": [tmp_path / "tools/go.mod"],
        "npm": [tmp_path / "frontend/package-lock.json"],
    }


def test_empty_checkout_has_no_language_cache_outputs(tmp_path: Path) -> None:
    outputs = cache_paths.plan(tmp_path, {"HOME": str(tmp_path / "home")}, "linux")

    assert outputs == {
        "uv-found": "false",
        "cargo-found": "false",
        "go-found": "false",
        "npm-found": "false",
    }


def test_defaults_are_native_paths_and_cargo_target_follows_each_lockfile(tmp_path: Path) -> None:
    home = tmp_path / "home"
    touch(tmp_path, "Cargo.lock")
    touch(tmp_path, "crates/cli/Cargo.lock")
    touch(tmp_path, "go.mod")
    touch(tmp_path, "package-lock.json")
    touch(tmp_path, "uv.lock")
    env = {"HOME": str(home), "XDG_CACHE_HOME": str(home / ".cache")}

    outputs = cache_paths.plan(tmp_path, env, "linux")

    assert outputs == {
        "uv-found": "true",
        "uv-path": str(home / ".cache/uv"),
        "cargo-found": "true",
        "cargo-registry-path": str(home / ".cargo/registry"),
        "cargo-git-path": str(home / ".cargo/git"),
        "cargo-target-path": f"{tmp_path}/target\n{tmp_path}/crates/cli/target",
        "go-found": "true",
        "go-module-path": str(home / "go/pkg/mod"),
        "go-build-path": str(home / ".cache/go-build"),
        "npm-found": "true",
        "npm-path": str(home / ".npm"),
    }
    assert "credentials.toml" not in outputs["cargo-registry-path"]
    assert "config.toml" not in outputs["cargo-git-path"]


def test_one_override_changes_only_its_cache_location(tmp_path: Path) -> None:
    touch(tmp_path, "uv.lock")
    touch(tmp_path, "package-lock.json")
    home = tmp_path / "home"
    env = {
        "HOME": str(home),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "TBGA_NPM_CACHE_PATH": "custom/npm-cache",
    }

    outputs = cache_paths.plan(tmp_path, env, "linux")

    assert outputs["npm-path"] == str(tmp_path / "custom/npm-cache")
    assert outputs["uv-path"] == str(home / ".cache/uv")
    assert outputs["npm-found"] == "true"


def test_native_environment_overrides_are_respected(tmp_path: Path) -> None:
    touch(tmp_path, "uv.lock")
    touch(tmp_path, "Cargo.lock")
    touch(tmp_path, "go.mod")
    touch(tmp_path, "package-lock.json")
    env = {
        "HOME": str(tmp_path / "home"),
        "UV_CACHE_DIR": str(tmp_path / "uv"),
        "CARGO_HOME": str(tmp_path / "cargo"),
        "CARGO_TARGET_DIR": str(tmp_path / "target-cache"),
        "GOMODCACHE": str(tmp_path / "go-modules"),
        "GOCACHE": str(tmp_path / "go-build"),
        "npm_config_cache": str(tmp_path / "npm"),
        "TBGA_UV_CACHE_PATH": str(tmp_path / "uv-override"),
        "TBGA_CARGO_HOME_PATH": str(tmp_path / "cargo-override"),
        "TBGA_CARGO_TARGET_CACHE_PATH": str(tmp_path / "target-override"),
        "TBGA_GO_MODULE_CACHE_PATH": str(tmp_path / "go-module-override"),
        "TBGA_GO_BUILD_CACHE_PATH": str(tmp_path / "go-build-override"),
        "TBGA_NPM_CACHE_PATH": str(tmp_path / "npm-override"),
    }

    outputs = cache_paths.plan(tmp_path, env, "linux")

    assert outputs["uv-path"] == str(tmp_path / "uv-override")
    assert outputs["cargo-registry-path"] == str(tmp_path / "cargo-override/registry")
    assert outputs["cargo-git-path"] == str(tmp_path / "cargo-override/git")
    assert outputs["cargo-target-path"] == str(tmp_path / "target-override")
    assert outputs["go-module-path"] == str(tmp_path / "go-module-override")
    assert outputs["go-build-path"] == str(tmp_path / "go-build-override")
    assert outputs["npm-path"] == str(tmp_path / "npm-override")


def test_malformed_override_falls_back_to_native_default(tmp_path: Path) -> None:
    touch(tmp_path, "uv.lock")
    home = tmp_path / "home"

    outputs = cache_paths.plan(
        tmp_path,
        {
            "HOME": str(home),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "TBGA_UV_CACHE_PATH": "custom\npath",
        },
        "linux",
    )

    assert outputs["uv-path"] == str(home / ".cache/uv")


def test_windows_defaults_follow_local_app_data(tmp_path: Path) -> None:
    touch(tmp_path, "uv.lock")
    touch(tmp_path, "package-lock.json")
    home = tmp_path / "home"
    local = tmp_path / "local"

    outputs = cache_paths.plan(
        tmp_path,
        {"HOME": str(home), "LOCALAPPDATA": str(local)},
        "win32",
    )

    assert outputs["uv-path"] == str(local / "uv/cache")
    assert outputs["npm-path"] == str(local / "npm-cache")


def test_run_creates_locations_and_emits_outputs_without_command_line_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cache_paths.sys, "platform", "darwin")
    touch(tmp_path, "go.mod")
    output_file = tmp_path / "output"
    environment_file = tmp_path / "environment"
    home = tmp_path / "home"
    custom_modules = tmp_path / "custom-modules"
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setenv("GITHUB_ENV", str(environment_file))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TBGA_GO_MODULE_CACHE_PATH", str(custom_modules))
    monkeypatch.setenv("GOCACHE", "")

    assert cache_paths.run() == 0
    content = output_file.read_text(encoding="utf-8")

    assert "go-found<<" in content
    assert "go-module-path<<" in content
    assert "go-build-path<<" in content
    assert str(custom_modules) in environment_file.read_text(encoding="utf-8")
    assert custom_modules.is_dir()
    assert (home / "Library/Caches/go-build").is_dir()


@pytest.mark.parametrize(
    ("manifest", "input_name", "environment_name"),
    [
        ("uv.lock", "TBGA_UV_CACHE_PATH", "UV_CACHE_DIR"),
        ("Cargo.lock", "TBGA_CARGO_HOME_PATH", "CARGO_HOME"),
        ("Cargo.lock", "TBGA_CARGO_TARGET_CACHE_PATH", "CARGO_TARGET_DIR"),
        ("go.mod", "TBGA_GO_MODULE_CACHE_PATH", "GOMODCACHE"),
        ("go.mod", "TBGA_GO_BUILD_CACHE_PATH", "GOCACHE"),
        ("package-lock.json", "TBGA_NPM_CACHE_PATH", "npm_config_cache"),
    ],
)
def test_each_path_override_redirects_its_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: str,
    input_name: str,
    environment_name: str,
) -> None:
    touch(tmp_path, manifest)
    output_file = tmp_path / "output"
    environment_file = tmp_path / "environment"
    custom_path = tmp_path / "custom-cache"
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setenv("GITHUB_ENV", str(environment_file))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv(input_name, str(custom_path))

    assert cache_paths.run() == 0

    environment = environment_file.read_text(encoding="utf-8")
    assert f"{environment_name}<<" in environment
    assert str(custom_path) in environment
    assert custom_path.is_dir()
