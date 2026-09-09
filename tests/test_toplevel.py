"""Tests for TOPLEVEL-based expression parsing (mmcalc.toplevel)."""

import shutil

import pytest

from mmcalc.config import parse_settings

SETTINGS = parse_settings(__import__("pathlib").Path("examples/ac9s.settings"))

_NEEDS_MM = shutil.which("metamath") is not None and __import__(
    "pathlib"
).Path("set.mm").is_file()


def parse(expression: str) -> list[str]:
    from mmcalc.toplevel import parse_tree_rpn

    return parse_tree_rpn(__import__("pathlib").Path("set.mm"), expression, SETTINGS)


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_theorem_statement():
    rpn = parse("|- ( A. x e. A B =/= (/) <-> X_ x e. A B =/= (/) )")
    assert rpn[-1] == "TOP.turnstile"
    assert "wral" in rpn
    assert "cixp" in rpn
    assert "wb" in rpn


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_wff():
    rpn = parse("A. x e. A B =/= (/)")
    assert rpn[-1] == "TOP.wff"
    assert "wral" in rpn


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_class():
    rpn = parse("X_ x e. A B")
    assert rpn[-1] == "TOP.class"
    assert "cixp" in rpn


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_unparseable_raises():
    from mmcalc.toplevel import parse_tree_rpn

    with pytest.raises(ValueError):
        parse_tree_rpn(
            __import__("pathlib").Path("set.mm"), "a b c d e f", SETTINGS
        )


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_cli_parse_expr():
    from mmcalc.cli import main

    rc = main(
        [
            "parse-expr",
            "|- ( A. x e. A B =/= (/) <-> X_ x e. A B =/= (/) )",
            "--database",
            "set.mm",
            "--settings",
            "examples/ac9s.settings",
        ]
    )
    assert rc == 0