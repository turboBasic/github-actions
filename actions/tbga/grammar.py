import re

from . import ERROR, annotate, emit, read_text

# A type is a bare word: letters and digits, starting with a letter. Nothing else is admitted, because
# the alternation below is substituted into a regex — an entry carrying `|`, `(` or `.` would be pattern
# rather than data, and would widen or break the grammar rather than fail.
BARE_WORD = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*$")

# The grammar both checks judge against, and the only place it is written. `TYPES_HERE` is replaced by
# the validated alternation.
TEMPLATE = """[tool.commitizen]
name = "cz_customize"

[tool.commitizen.customize]
schema_pattern = '(?s)(TYPES_HERE)(\\(\\S+\\))?!?: ([^\\n\\r]+)((\\n\\n.*)|(\\s*))?$'
"""

PLACEHOLDER = "TYPES_HERE"


def compile_grammar(types: str) -> str | None:
    # Returns the rendered config, or None where the list is unusable. Every entry is checked before any
    # substitution happens, so a rejected list never reaches the template at all.
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
    # The list as a reader should see it in a failure, so neither judging step has to render it again.
    emit(config=destination, types=", ".join(listed))
    return 0
