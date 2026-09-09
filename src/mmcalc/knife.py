"""Wrapper around metamath-knife for Metamath parsing and verification."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Statement:
    """A parsed Metamath statement."""

    label: str
    type_code: str
    statement_type: str  # "f", "e", "a", "p", "c"
    tokens: list[str] = field(default_factory=list)


@dataclass
class Database:
    """Parsed Metamath database information from metamath-knife."""

    path: Path
    statements: list[Statement] = field(default_factory=list)
    outline: str = ""


def run_knife(
    args: list[str], mm_path: Path, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run metamath-knife with given arguments on a .mm file."""
    cmd = ["metamath-knife", *args, str(mm_path)]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
    )


def verify(mm_path: Path) -> subprocess.CompletedProcess[str]:
    """Verify a Metamath database."""
    return run_knife(["--verify"], mm_path)


def dump_statements(mm_path: Path) -> list[str]:
    """List all statement labels in a database."""
    result = run_knife(["--list-statements"], mm_path)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def dump_outline(mm_path: Path) -> str:
    """Get the outline (structure) of a database."""
    result = run_knife(["--outline"], mm_path)
    return result.stdout


def parse_all(mm_path: Path) -> subprocess.CompletedProcess[str]:
    """Parse all statements according to the database grammar."""
    return run_knife(["--parse-stmt"], mm_path)


def dump_grammar(mm_path: Path) -> str:
    """Dump the grammar of a database."""
    result = run_knife(["--dump-grammar"], mm_path)
    return result.stdout


def dump_formula(mm_path: Path) -> str:
    """Dump all formulas in the database."""
    result = run_knife(["--dump-formula"], mm_path)
    return result.stdout


def export_proof(mm_path: Path, label: str) -> str:
    """Export a proof for a given label."""
    result = run_knife(["--export", label], mm_path)
    return result.stdout


def _mm_tool() -> str:
    """The reference Metamath binary (INTERACTIVE_METAMATH env or `metamath`)."""
    return os.environ.get("MM_TOOL", "metamath")


def show_normal_proof(mm_path: Path, label: str) -> str:
    """Return a theorem's proof in uncompressed (normal) form.

    Uses the reference Metamath program's `show proof <label> /normal`
    command, which emits the label sequence as it appears in an
    uncompressed proof (each assertion pops its own mandatory
    hypotheses).  The returned string is the whitespace-joined labels.
    """
    db = str(mm_path.resolve())
    result = subprocess.run(
        [_mm_tool(), f'read "{db}"', f"show proof {label} /normal", "exit"],
        capture_output=True,
        text=True,
        check=False,
    )
    marker = "Clip out the proof below this line to put it in the source file:"
    if result.returncode != 0 or marker not in result.stdout:
        raise RuntimeError(result.stdout or result.stderr)
    body = result.stdout.split(marker, 1)[1].split("\n----", 1)[0]
    return " ".join(body.split()).rstrip("$.").strip()


def show_statement(mm_path: Path, label: str) -> str:
    """Show a statement with its hypotheses, as the reference tool renders it."""
    db = str(mm_path.resolve())
    result = subprocess.run(
        [_mm_tool(), f'read "{db}"', f"show statement {label}", "exit"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or label not in result.stdout:
        raise RuntimeError(result.stdout or result.stderr)
    return result.stdout
