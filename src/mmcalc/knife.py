"""Wrapper around metamath-knife for Metamath parsing and verification."""

from __future__ import annotations

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
