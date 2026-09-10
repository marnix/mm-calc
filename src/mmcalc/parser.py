"""Parser for the mmcalc calculational proof file format.

An `.mmcalc` file contains:

- Settings lines: `$[ database $]`
- Comment lines: `$( ... $)` or `* ...`
- Metamath declarations: `$d`, `$e`, `$p` (the machine-verifiable theorem)
- A calculational proof (structured derivation) with justification hints

See design.md for the full specification.

Original idea: https://groups.google.com/g/metamath/c/aNki7h6G50A/m/-hsjesajGAAJ
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Step:
    """A single step in a calculational proof."""

    expression: str  # opaque Metamath token text
    justification: Justification | None = None


@dataclass
class Justification:
    """A justification for a proof step."""

    rule_refs: list[str] = field(default_factory=list)
    using_refs: list[str] = field(default_factory=list)
    index: int | None = None  # For numbered references like (-1:impbii)


@dataclass
class Calculation:
    """A calculational proof chain."""

    steps: list[Step] = field(default_factory=list)
    label: str = ""


@dataclass
class ProofFile:
    """A complete calculational proof file."""

    settings: list[str] = field(default_factory=list)  # $[ db $] includes
    disjoint: list[str] = field(default_factory=list)  # $d constraints
    hypotheses: list[tuple[str, str]] = field(default_factory=list)  # (label, stmt)
    theorem_label: str = ""
    theorem_statement: str = ""
    proof_tokens: str = ""  # optional explicit $= tokens
    calculations: list[Calculation] = field(default_factory=list)
    preamble: list[str] = field(default_factory=list)  # raw comment lines


_RE_RULE_REF = re.compile(r"\((-?\d+):([\w.]+)\)|\(([\w.]+)\)")
_RE_JUSTIFICATION = re.compile(r"\{\s*by\s+(.+?)\}")
_RE_INCLUDE = re.compile(r"\$\[\s*(.+?)\s*\$\]")
_RE_DISJOINT = re.compile(r"^\$d\s+(.*?)\s*\.\s*$")
_RE_HYPOTHESIS = re.compile(r"([\w.]+)\s*\$e\s+(.*?)\s*\.?\s*$")
_RE_THEOREM = re.compile(
    r"([\w.]+)\s*\$p\s+(.*?)\s*\$=\s*(.*?)\s*\.\s*$", re.DOTALL
)


def _parse_justification(text: str) -> Justification | None:
    """Parse a justification like '{ by (bitri) using (bicomi) } (-1:impbii)'."""
    m = _RE_JUSTIFICATION.search(text)
    if not m:
        return None

    inner = m.group(1)
    just = Justification()

    if "using" in inner:
        parts = inner.split("using")
        rules_part, using_part = parts[0], parts[1]
        just.rule_refs = [
            r for r in re.findall(r"\(([\w.]+)\)", rules_part)
        ]
        just.using_refs = [
            r for r in re.findall(r"\(([\w.]+)\)", using_part)
        ]
    else:
        for ref_match in _RE_RULE_REF.finditer(inner):
            if ref_match.group(1) is not None:
                just.index = int(ref_match.group(1))
                just.rule_refs.append(ref_match.group(2))
            else:
                just.rule_refs.append(ref_match.group(3))

    # Also look for indexed rule references outside the { by ... } block
    after = text[m.end():]
    for ref_match in _RE_RULE_REF.finditer(after):
        if ref_match.group(1) is not None:
            just.index = int(ref_match.group(1))
            just.rule_refs.append(ref_match.group(2))

    return just


def _parse_step_line(line: str) -> Step | None:
    """Parse a single step line, extracting expression and justification.

    The expression is kept as opaque Metamath token text; nothing here
    interprets any particular Metamath symbol (no `|-`, `<->`, parens, ...).
    The structure of expressions is recovered only through TOPLEVEL parsing.
    """
    line = line.strip()
    if not line:
        return None

    justification = _parse_justification(line)
    step_text = _RE_JUSTIFICATION.sub("", line).strip()

    # Strip an indexed rule reference like (1:impbii) after the justification
    step_text = re.sub(r"\(\s*-?\d+\s*:\s*[\w.]+\s*\)\s*$", "", step_text).strip()

    if not step_text or step_text == "$...":
        return None

    return Step(expression=step_text, justification=justification)


def parse_calculation(text: str) -> Calculation:
    """Parse a calculation block from the proof text."""
    calc = Calculation()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "." or not stripped:
            continue
        step = _parse_step_line(stripped)
        if step:
            calc.steps.append(step)
    return calc


def parse_file(source: str | Path) -> ProofFile:
    """Parse an mmcalc proof file."""
    text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
    pf = ProofFile()
    lines = text.splitlines()

    in_calc = False
    in_comment = False
    in_proof = False  # collecting $p proof tokens
    calc_lines: list[str] = []
    proof_buf: list[str] = []

    def handle_comment(stripped: str) -> bool:
        """Handle multiline $( ... $) comments; returns True if handled."""
        nonlocal in_comment
        if in_comment:
            if "$)" in stripped:
                in_comment = False
            pf.preamble.append(stripped)
            return True
        if stripped.startswith("$("):
            in_comment = True
            if "$)" in stripped:
                in_comment = False
            pf.preamble.append(stripped)
            return True
        return False

    for raw in lines:
        stripped = raw.strip()

        if not stripped:
            if in_proof:
                proof_buf.append("")
            elif in_calc:
                calc_lines.append("")
            continue

        # Multi-line comment handling
        if handle_comment(stripped):
            continue

        # If we're collecting proof tokens, look for $. terminator
        if in_proof:
            if stripped == "$." or stripped.endswith("$."):
                # Extract any trailing tokens on this line before $.
                tok_line = stripped[: stripped.rfind("$.")].strip()
                if tok_line:
                    proof_buf.append(tok_line)
                pf.proof_tokens = " ".join(proof_buf).strip()
                in_proof = False
            else:
                proof_buf.append(stripped)
            continue

        # Settings line
        m = _RE_INCLUDE.match(stripped)
        if m:
            pf.settings.append(m.group(1))
            continue

        # Single-line "*" comments
        if stripped.startswith("*"):
            pf.preamble.append(stripped)
            continue

        # Disjoint constraints (possibly several on one line)
        if stripped.startswith("$d ") or stripped.startswith("$d\t"):
            for m_d in re.finditer(r"\$d\s+([^\$]+?)\s*\$", stripped):
                pf.disjoint.append(m_d.group(1).strip())
            continue

        # Hypothesis
        m = _RE_HYPOTHESIS.match(stripped)
        if m and not in_calc:
            label = m.group(1).strip()
            stmt = m.group(2).strip().rstrip("$. ")
            if stmt:
                pf.hypotheses.append((label, stmt))
                continue

        # Theorem $p statement (possibly multi-line with $= proof tokens)
        m = re.match(r"([\w.]+)\s*\$p\s+(.*?)\s*\$=", stripped)
        if m and not in_calc:
            pf.theorem_label = m.group(1)
            pf.theorem_statement = m.group(2).strip()
            # Check if proof tokens + $. are on the same line
            after_eq = stripped[m.end():]
            if "$." in after_eq:
                # single-line: "ac9s $p |- ... $= tokens $."
                pf.proof_tokens = after_eq[: after_eq.rfind("$.")].strip()
            elif after_eq.strip():
                # "$= tokens\n" (tokens start here, $. later)
                in_proof = True
                proof_buf = [after_eq.strip()]
            else:
                # "$=\n" (tokens on next line)
                in_proof = True
                proof_buf = []
            continue

        # Block delimiters
        if stripped in ("$", "$}", "${", "$$"):
            continue

        # "." terminates a calculation; "$." book-ends are handled above
        if stripped == "." and in_calc:
            calc = parse_calculation("\n".join(calc_lines))
            if calc.steps:
                pf.calculations.append(calc)
            calc_lines = []
            in_calc = False
            continue

        # Otherwise, a step line: either starting or continuing a calculation
        in_calc = True
        calc_lines.append(raw)

    # Trailing calculation without terminator
    if calc_lines and any(s.strip() and s.strip() != "." for s in calc_lines):
        calc = parse_calculation("\n".join(calc_lines))
        if calc.steps:
            pf.calculations.append(calc)

    return pf
