"""Tests for TOPLEVEL-based expression parsing (mmcalc.toplevel).

A top-level expression is a *statement*, i.e. a typecode prefix followed by
a formula: `|- x e. A`, `wff ...`, `class ...`, `setvar x`.  Its parse tree
is the (essentially unique) proof of `TOPLEVEL <statement>`: the TOP.* axiom
for that typecode is the last step, and the formula's grammar tree is proved
underneath (e.g. `wff x e. A` from `class x` via `cv`, `class A`, `wcel`).
"""

import shutil
from pathlib import Path

import pytest

from mmcalc.config import parse_settings

SETTINGS = parse_settings(Path("examples/ac9s.settings"))

_NEEDS_MM = shutil.which("metamath") is not None and Path("set.mm").is_file()


def parse(expression: str) -> list[str]:
    from mmcalc.toplevel import parse_tree_rpn

    return parse_tree_rpn(Path("set.mm"), expression, SETTINGS)


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_theorem_statement():
    rpn = parse("|- ( A. x e. A B =/= (/) <-> X_ x e. A B =/= (/) )")
    assert rpn[-1] == "TOP.turnstile"
    assert "wral" in rpn
    assert "cixp" in rpn
    assert "wb" in rpn


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_wff_statement():
    rpn = parse("wff A. x e. A B =/= (/)")
    assert rpn[-1] == "TOP.wff"
    assert "wral" in rpn


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_class_statement():
    rpn = parse("class X_ x e. A B")
    assert rpn[-1] == "TOP.class"
    assert "cixp" in rpn


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_setvar_statement():
    rpn = parse("setvar x")
    assert rpn[-1] == "TOP.set"
    assert rpn[0] == "vx"


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_membership_statement():
    assert parse("|- x e. A") == ["vx", "cv", "cA", "wcel", "TOP.turnstile"]


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_parse_unparseable_raises():
    from mmcalc.toplevel import parse_tree_rpn

    with pytest.raises(ValueError):
        parse_tree_rpn(Path("set.mm"), "a b c d e f", SETTINGS)


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