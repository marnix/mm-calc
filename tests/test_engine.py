"""Tests for the proof engine (mmcalc.engine).

Slice 1: derive the proof of a theorem whose calc is a single relational
step, where the relation is stated by applying one rule.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from mmcalc.parser import parse_file

_NEEDS_MM = shutil.which("metamath") is not None and Path("set.mm").is_file()
_NEEDS_REFERENCE_TOOL = shutil.which("metamath") is not None

_FIXTURES = Path(__file__).parent / "fixtures"
_MINICHAIN_DB = _FIXTURES / "minichain.mm"
_MINICHAIN_SETTINGS = _FIXTURES / "minichain.settings"

_CHAIN_CALC = """$[ minichain.mm $]
$$
echain $p |- ( x e. A <-> x e. C ) $= ? $.

x e. A
<-> { by (r1) } (bitri)
x e. B
<-> { by (r2) }
x e. C
.
"""

_DFCLEQ_CALC = """$[ set.mm $]
$$
mydfcleq $p |- ( A = B <-> A. x ( x e. A <-> x e. B ) ) $= ? $.

A = B
<-> { by (dfcleq) }
A. x ( x e. A <-> x e. B )
.
"""


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_derive_single_relation_step():
    from mmcalc.engine import derive_calc_proof

    pf = parse_file(_DFCLEQ_CALC)
    assert len(pf.calculations) == 1
    tokens, disjoint = derive_calc_proof(Path("set.mm"), pf.calculations[0], pf.theorem_statement)
    assert tokens == ["vx", "cA", "cB", "dfcleq"]
    assert sorted(disjoint) == ["x A", "x B"]


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath and set.mm")
def test_derive_calc_generated_mm_verifies(tmp_path: Path):
    from mmcalc.engine import derive_calc_proof
    from mmcalc.generator import generate_mm

    pf = parse_file(_DFCLEQ_CALC)
    tokens, disjoint = derive_calc_proof(Path("set.mm"), pf.calculations[0], pf.theorem_statement)
    pf.proof_tokens = " ".join(tokens)
    pf.disjoint = list(dict.fromkeys(list(pf.disjoint) + disjoint))

    out = tmp_path / "mydfcleq.mm"
    out.write_text(generate_mm(pf, None), encoding="utf-8")

    db = str(out.resolve())
    result = subprocess.run(
        ["metamath", f'read "{db}"', "verify proof *", "exit", "No"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All proofs in the database were verified" in result.stdout


@pytest.mark.skipif(not _NEEDS_REFERENCE_TOOL, reason="needs metamath")
def test_derive_two_step_chain():
    from mmcalc.config import parse_settings
    from mmcalc.engine import derive_calc_proof

    settings = parse_settings(_MINICHAIN_SETTINGS)
    pf = parse_file(_CHAIN_CALC)
    assert len(pf.calculations) == 1
    tokens, disjoint = derive_calc_proof(
        _MINICHAIN_DB, pf.calculations[0], pf.theorem_statement, settings=settings
    )
    assert tokens == [
        "vx",
        "cA",
        "wcel",
        "vx",
        "cB",
        "wcel",
        "vx",
        "cC",
        "wcel",
        "vx",
        "cA",
        "cB",
        "r1",
        "vx",
        "cB",
        "cC",
        "r2",
        "bitri",
    ]
    assert disjoint == []


@pytest.mark.skipif(not _NEEDS_REFERENCE_TOOL, reason="needs metamath")
def test_two_step_chain_generated_mm_verifies(tmp_path: Path):
    import shutil

    from mmcalc.config import parse_settings
    from mmcalc.engine import derive_calc_proof
    from mmcalc.generator import generate_mm

    settings = parse_settings(_MINICHAIN_SETTINGS)
    pf = parse_file(_CHAIN_CALC)
    tokens, disjoint = derive_calc_proof(
        _MINICHAIN_DB, pf.calculations[0], pf.theorem_statement, settings=settings
    )
    pf.proof_tokens = " ".join(tokens)
    pf.disjoint = list(dict.fromkeys(list(pf.disjoint) + disjoint))

    shutil.copy(_MINICHAIN_DB, tmp_path / "minichain.mm")
    out = tmp_path / "echain.mm"
    out.write_text(generate_mm(pf, None), encoding="utf-8")

    db = str(out.resolve())
    result = subprocess.run(
        ["metamath", f'read "{db}"', "verify proof *", "exit", "No"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All proofs in the database were verified" in result.stdout
