"""Parser for the mmcalc calculational proof file format.

The format allows writing structured derivations that expand to Metamath proofs.

See the design document for full specification:
https://groups.google.com/g/metamath/c/aNki7h6G50A/m/-hsjesajGAAJ
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO


@dataclass
class Step:
    """A single step in a calculational proof."""

    expression: str
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
    context: list[str] = field(default_factory=list)


@dataclass
class ProofFile:
    """A complete calculational proof file."""

    context_label: str = ""
    context_line: str = ""  # $==>
    calculations: list[Calculation] = field(default_factory=list)
    preamble: list[str] = field(default_factory=list)  # raw preamble lines


_RE_RULE_REF = re.compile(r"\((-?\d+):(\w+)\)|\((\w+)\)")
_RE_JUSTIFICATION = re.compile(r"\{\s*by\s+(.+?)\s*\}")


def _parse_justification(text: str) -> Justification | None:
    """Parse a justification like '{ by (bitri) using (bicomi) } (-1:impbii)'."""
    m = _RE_JUSTIFICATION.search(text)
    if not m:
        return None

    inner = m.group(1)
    just = Justification()

    for ref_match in _RE_RULE_REF.finditer(inner):
        if ref_match.group(1) is not None:
            just.index = int(ref_match.group(1))
            just.rule_refs.append(ref_match.group(2))
        else:
            just.rule_refs.append(ref_match.group(3))

    if "using" in inner:
        parts = inner.split("using")
        rules_part = parts[0]
        using_part = parts[1] if len(parts) > 1 else ""
        just.rule_refs = [r.strip() for r in re.findall(r"\((\w+)\)", rules_part)]
        just.using_refs = [r.strip() for r in re.findall(r"\((\w+)\)", using_part)]

    # Also look for indexed rule references outside the { by ... } block
    after = text[m.end():]
    for ref_match in _RE_RULE_REF.finditer(after):
        if ref_match.group(1) is not None:
            just.index = int(ref_match.group(1))
            just.rule_refs.append(ref_match.group(2))

    return just


def _parse_step_line(line: str) -> Step | None:
    """Parse a single step line, extracting expression and justification."""
    line = line.strip()
    if not line:
        return None

    justification = _parse_justification(line)
    step_text = _RE_JUSTIFICATION.sub("", line).strip()

    # Strip indexed rule references like (-1:impbii) that appear after justification
    step_text = re.sub(r"\s*\(-?\d+:\w+\)\s*$", "", step_text).strip()

    # Strip trailing relational operators like <-> or <-
    step_text = re.sub(r"\s*<->\s*$", "", step_text).strip()
    step_text = re.sub(r"\s*<-\s*$", "", step_text).strip()
    step_text = re.sub(r"\s*=\s*$", "", step_text).strip()

    if not step_text:
        return None

    return Step(expression=step_text, justification=justification)


def parse_calculation(text: str) -> Calculation:
    """Parse a calculation block from the proof text."""
    calc = Calculation()
    for line in text.splitlines():
        step = _parse_step_line(line)
        if step:
            calc.steps.append(step)
    return calc


def _extract_context_and_calcs(text: str) -> tuple[str, str, list[str]]:
    """Split text into context label, context line, and calculation segments.

    The format uses:
    - *...* lines as context/comment lines
    - $==> separating context from proof steps
    - . separating proof steps
    """
    context_label = ""
    context_line = ""
    segments: list[str] = []

    # Find $==> to split context from calculations
    parts = text.split("$==>", 1)
    if len(parts) < 2:
        # No $==> found, treat entire text as context
        for line in parts[0].splitlines():
            m = re.search(r"\*\s*\((\w+\.\d+)\)\s*\|-\s*(.+)", line)
            if m:
                context_label = m.group(1)
                context_line = m.group(2).strip()
        return context_label, context_line, []

    preamble_text = parts[0]
    calc_text = parts[1]

    # Extract context label from preamble
    for line in preamble_text.splitlines():
        m = re.search(r"\*\s*\((\w+\.\d+)\)\s*\|-\s*(.+)", line)
        if m:
            context_label = m.group(1)
            context_line = m.group(2).strip()

    # Split calculation text on '.' terminators
    segments = [seg.strip() for seg in calc_text.split(".") if seg.strip()]

    return context_label, context_line, segments


def parse_file(source: str | Path) -> ProofFile:
    """Parse an mmcalc proof file."""
    text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source

    pf = ProofFile()
    pf.context_label, pf.context_line, segments = _extract_context_and_calcs(text)

    for segment in segments:
        calc = parse_calculation(segment)
        if calc.steps:
            pf.calculations.append(calc)

    return pf


def write_file(pf: ProofFile, dest: TextIO) -> None:
    """Write a ProofFile back to text format."""
    for line in pf.preamble:
        dest.write(line + "\n")

    dest.write("$==>\n")
    for calc in pf.calculations:
        for _i, step in enumerate(calc.steps):
            line = f"    {step.expression}"
            if step.justification:
                just = step.justification
                refs = " ".join(f"({r})" for r in just.rule_refs)
                using = ""
                if just.using_refs:
                    using = " using " + " ".join(f"({r})" for r in just.using_refs)
                line += f"    {{ by {refs}{using} }}"
            dest.write(line + "\n")
        dest.write("    .\n")
