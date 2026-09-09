"""Tests for CLI auto-generation of proof tokens (mmcalc.cli generate).

When a .mmcalc file's theorem has no proof tokens yet (or only a `?`
placeholder), `mmcalc generate` must derive the proof from the
calculational steps (via the engine) and produce a .mm file that verifies
with both the reference metamath tool and metamath-knife.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_NEEDS_MM = (
    shutil.which("metamath") is not None
    and shutil.which("metamath-knife") is not None
    and Path("set.mm").is_file()
)

_DFCLEQ_CALC_NO_TOKENS = """$[ set.mm $]
$$
mydfcleq $p |- ( A = B <-> A. x ( x e. A <-> x e. B ) ) $= ? $.

A = B
<-> { by (dfcleq) }
A. x ( x e. A <-> x e. B )
.
"""


@pytest.mark.skipif(not _NEEDS_MM, reason="needs metamath, knife, and set.mm")
def test_generate_autogenerates_proof_and_verifies(tmp_path: Path):
    from mmcalc.cli import main

    calc = tmp_path / "mydfcleq.mmcalc"
    calc.write_text(_DFCLEQ_CALC_NO_TOKENS, encoding="utf-8")

    rc = main(["generate", str(calc)])
    assert rc == 0

    out = calc.with_suffix(".mm")
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "vx cA cB dfcleq" in body
    assert "  $d x A $." in body
    assert "  $d x B $." in body

    result = subprocess.run(
        ['metamath', f'read "{out.resolve()}"', "verify proof *", "exit", "No"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All proofs in the database were verified" in result.stdout
