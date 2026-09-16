import re

from . import ERROR, annotate, emit, read_text

# The alternation is substituted into a regex, so an entry must be data and not pattern.
BARE_WORD = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*$")

# The grammar both checks judge against, written once.
TEMPLATE = """[tool.commitizen]
name = "cz_customize"

[tool.commitizen.customize]
schema_pattern = '(?s)(TYPES_HERE)(\\(\\S+\\))?!?: ([^\\n\\r]+)((\\n\\n.*)|(\\s*))?$'
"""

PLACEHOLDER = "TYPES_HERE"


def compile_grammar(types: str) -> str | None:
    # Every entry is validated before any substitution, so a rejected list never reaches the template.
    wanted = [line.strip() for line in types.splitlines() if line.strip()]
    if not wanted or any(not BARE_WORD.match(entry) for entry in wanted):
        return None
    return TEMPLATE.replace(PLACEHOLDER, "|".join(wanted))


def run() -> int:
    types = read_text("TYPES")
    rendered = compile_grammar(types)
    if rendered is None:
        annotate(
            ERROR,
            f"conventional-commits read the types input as [{types}] and will not compile it. Every "
            "type is a bare word — letters and digits, starting with a letter — one per line. A "
            "comma-separated or quoted list looks accepted and matches nothing. Fix the types input at "
            "the call site",
        )
        return 1
    destination = read_text("CONFIG_PATH")
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    listed = [line.strip() for line in types.splitlines() if line.strip()]
    # Rendered here so neither judging step renders it again.
    emit(config=destination, types=", ".join(listed))
    return 0
