"""Proof engine: build Metamath proof trees from calculational steps.

Slice 1: a calc with a single relational step whose relation is stated by
applying exactly one rule.  The engine looks up the rule's statement with
the reference tool, verifies that the theorem statement is a verbatim
instance of the rule's conclusion, and emits the proof: the rule's
mandatory hypotheses (in RPN order, as the reference tool lists them)
followed by the rule label, together with the rule's mandatory disjoint
variable pairs so the generated theorem block can declare them.

The engine never interprets any Metamath *mathematical* token (no `|-`,
`<->`, parens, ...): the theorem statement is compared to the rule's
conclusion as opaque token text, and structure is recovered only via the
reference tool's statement metadata.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from mmcalc.knife import _mm_tool
from mmcalc.parser import Calculation


@dataclass
class RuleInfo:
    """Metadata for a statement used as a proof rule."""

    label: str
    conclusion: list[str] = field(default_factory=list)  # token text
    mandatory_hyps: list[str] = field(default_factory=list)  # labels, RPN order
    disjoint: list[tuple[str, str]] = field(default_factory=list)  # variable pairs
    has_e_hyp: bool = False


_RE_STMT = re.compile(r"^\s*\d+\s+(\S+)\s*\$p\s+(.*?)\s*\$=", re.DOTALL | re.MULTILINE)
_RE_HYP_RPN = re.compile(r"^\s+(\S+)\s+\$f\s+", re.MULTILINE)
_RE_HYP_E = re.compile(r"^\s+(\S+)\s+\$e\s+", re.MULTILINE)
_RE_DISJOINT = re.compile(r"<(\w+),(\w+)>")


def rule_info(db_path: Path, label: str, tool: str | None = None) -> RuleInfo:
    """Look up a rule's statement metadata via the reference tool.

    Parses the output of `show statement <label> /full`, which lists the
    statement's mandatory hypotheses in RPN order and its mandatory
    disjoint-variable pairs.
    """
    db = str(db_path.resolve())
    tool = _mm_tool() if tool is None else tool
    result = subprocess.run(
        [tool, f'read "{db}"', f"show statement {label} /full", "exit"],
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = result.stdout
    if result.returncode != 0 or f"{label} $p" not in stdout:
        raise RuntimeError(stdout or result.stderr)

    info = RuleInfo(label=label)
    m = _RE_STMT.search(stdout)
    if m:
        info.conclusion = m.group(2).split()

    # Mandatory hypotheses (RPN order): all $f hyps (slice 1: no $e hyps)
    e_hyps = _RE_HYP_E.findall(stdout)
    info.has_e_hyp = bool(e_hyps)
    if not e_hyps:
        info.mandatory_hyps = _RE_HYP_RPN.findall(stdout)

    # Mandatory disjoint variable pairs (only the "mandatory" line)
    m_dj = re.search(
        r"Its mandatory disjoint variable pairs are:\s+(.*(?:\n\s+[^\n]*)*)",
        stdout,
    )
    if m_dj:
        info.disjoint = [(a, b) for a, b in _RE_DISJOINT.findall(m_dj.group(1))]

    return info


def derive_calc_proof(
    db_path: Path,
    calc: Calculation,
    theorem_statement: str,
    tool: str | None = None,
) -> tuple[list[str], list[str]]:
    """Derive proof tokens for a single-relation calc.

    Returns ``(tokens, disjoint)`` where ``disjoint`` is a list of
    ``"x y"`` disjoint-variable constraints the generated theorem block
    must declare for the proof to verify.

    Raises UnsupportedError/ValueError if the calc is not of slice-1 shape.
    """
    steps = calc.steps
    if len(steps) != 3:
        raise NotImplementedError(
            "slice 1: exactly one relational step (3 calc lines) supported"
        )
    expr_left, rel_step, expr_right = steps
    if expr_left.justification is not None or expr_right.justification is not None:
        raise NotImplementedError(
            "slice 1: only the relational step may carry a justification"
        )
    if rel_step.justification is None or len(rel_step.justification.rule_refs) != 1:
        raise NotImplementedError(
            "slice 1: exactly one rule in the relation step's hint"
        )
    if rel_step.justification.using_refs:
        raise NotImplementedError("slice 1: 'using' hints not supported")

    rule = rel_step.justification.rule_refs[0]
    info = rule_info(db_path, rule, tool=tool)
    if info.has_e_hyp:
        raise NotImplementedError(f"slice 1: rule {rule} has $e hypotheses")

    theorem_tokens = " ".join(theorem_statement.split())
    conclusion_tokens = " ".join(info.conclusion)
    if theorem_tokens != conclusion_tokens:
        raise ValueError(
            f"theorem statement does not match the conclusion of {rule}:\n"
            f"  theorem:    {theorem_tokens}\n"
            f"  conclusion: {conclusion_tokens}"
        )

    # The calc's two expressions must appear verbatim inside the statement
    for expr in (expr_left.expression, expr_right.expression):
        if " ".join(expr.split()) not in theorem_tokens:
            raise ValueError(f"calc expression not in theorem statement: {expr}")

    tokens = list(info.mandatory_hyps) + [rule]
    disjoint = [f"{a} {b}" for a, b in info.disjoint]
    return tokens, disjoint
