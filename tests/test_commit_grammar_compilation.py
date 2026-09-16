from pathlib import Path

from tbga import grammar

# The default list conventional-commits ships, as its `types` input declares it.
DEFAULT = "\n".join(
    (
        "build",
        "bump",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
    )
)


def test_the_default_list_compiles_into_one_alternation() -> None:
    rendered = grammar.compile_grammar(DEFAULT)
    assert rendered is not None
    assert "(build|bump|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)" in rendered
    assert grammar.PLACEHOLDER not in rendered


def test_an_entry_carrying_a_metacharacter_is_refused_before_any_substitution() -> None:
    # Substituted into a regex, so an unvalidated entry is pattern and not data. `.*` matches every
    # subject; `)` breaks the group and fails every commit. Neither reaches the template.
    for hostile in ("feat\n.*", "feat\nfix)", "feat\na|b", "feat\nfi x", "feat\n$(id)"):
        assert grammar.compile_grammar(hostile) is None, hostile


def test_a_comma_separated_list_is_refused_rather_than_matching_nothing() -> None:
    # The shape a caller reaches for first. Admitted, it is one alternative matching no message, and
    # every commit fails against a check that looks configured.
    assert grammar.compile_grammar("feat, fix, chore") is None


def test_an_empty_list_is_refused() -> None:
    for nothing in ("", "\n", "   \n\t\n"):
        assert grammar.compile_grammar(nothing) is None


def test_blank_lines_and_surrounding_space_are_not_entries() -> None:
    rendered = grammar.compile_grammar("  feat  \n\n\tfix\n")
    assert rendered is not None
    assert "(feat|fix)" in rendered


def test_the_rendered_config_is_what_the_commit_tool_reads(tmp_path: Path) -> None:
    # The tool is handed this as its own config. Invalid TOML fails inside it, naming neither this
    # repository nor the list.
    import tomllib

    rendered = grammar.compile_grammar(DEFAULT)
    assert rendered is not None
    written = tmp_path / "cz.toml"
    written.write_text(rendered, encoding="utf-8")
    with open(written, "rb") as handle:
        table = tomllib.load(handle)
    assert table["tool"]["commitizen"]["name"] == "cz_customize"
    assert "schema_pattern" in table["tool"]["commitizen"]["customize"]
