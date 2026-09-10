"""Proof engine: build Metamath proof trees from calculational steps.

Slice 1: a calc with a single relational step whose relation is stated by
applying exactly one rule.  The engine looks up the rule's statement with
the reference tool, verifies that the theorem statement is a verbatim
instance of the rule's conclusion, and emits the proof: the rule's
mandatory hypotheses (in RPN order, as the reference tool lists them)
followed by the rule label, together with the rule's mandatory disjoint
variable pairs so the generated theorem block can declare them.

Slice 2: a calc with two relational steps (`expr0 <-> expr1 <-> expr2`)
joined by one transitivity rule such as ``bitri``.  The join rule's
mandatory hypotheses, in RPN order, are its ``$f`` well-formedness hyps
(one per calc expression) followed by its ``$e`` step hyps (one per
relational step).  The engine emits a well-formedness cell for each
expression (the TOPLEVEL parse of `typecode expr`, minus the trailing
TOP.* wrapper), then one proof per relational step (that step's rule's
mandatory hypotheses followed by the rule label), then the join rule.

As in slice 1, the engine never interprets any Metamath *mathematical*
token (no `|-`, `<->`, parens, ...).  Variable substitution is handled
at the token level: the join rule's ``$f`` hypothesis variables are
replaced by the calc expressions (in calc order) in the join rule's
conclusion and `$e` hypotheses, and the results must match the theorem
statement and the step rules' conclusions verbatim.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from mmcalc.config import Settings
from mmcalc.knife import _mm_tool
from mmcalc.parser import Calculation
from mmcalc.toplevel import parse_tree_rpn


@dataclass
class RuleInfo:
    """Metadata for a statement used as a proof rule."""

    label: str
    conclusion: list[str] = field(default_factory=list)  # token text
    mandatory_hyps: list[str] = field(default_factory=list)  # labels, RPN order
    f_hyps: list[tuple[str, str, str]] = field(default_factory=list)  # (label, type, var)
    e_hyps: list[tuple[str, list[str]]] = field(default_factory=list)  # (label, stmt tokens)
    disjoint: list[tuple[str, str]] = field(default_factory=list)  # variable pairs
    has_e_hyp: bool = False


_RE_STMT = re.compile(r"^\s*\d+\s+(\S+)\s*\$[ap]\s+(.*?)\s*(?:\$=|\$\.)", re.DOTALL | re.MULTILINE)
_RE_MAND_HYPS = re.compile(
    r"Its mandatory hypotheses in RPN order are:\s*"
    r"(.*?)(?:\nIts optional|\nIts mandatory|\nThe statement|\s*\Z)",
    re.DOTALL,
)
_RE_HYPLINE = re.compile(r"^[ \t]*(\S+)[ \t]+\$(f|e)[ \t]+(.*?)[ \t]*\$\.", re.MULTILINE)
_RE_DISJOINT = re.compile(r"<(\w+),(\w+)>")


def rule_info(db_path: Path, label: str, tool: str | None = None) -> RuleInfo:
    """Look up a rule's statement metadata via the reference tool.

    Parses the output of `show statement <label> /full`, which lists the
    statement's mandatory hypotheses in RPN order and its mandatory
    disjoint-variable pairs.  Works for both ``$a`` axioms and ``$p``
    theorems.
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
    if result.returncode != 0 or f"{label} $" not in stdout:
        raise RuntimeError(stdout or result.stderr)

    info = RuleInfo(label=label)
    m = _RE_STMT.search(stdout)
    if m:
        info.conclusion = m.group(2).split()

    # Mandatory hypotheses (RPN order): $f hyps carry a typecode, $e carry a
    # full statement.  Both are needed by the chaining slice.
    m_h = _RE_MAND_HYPS.search(stdout)
    if m_h:
        for hyp in _RE_HYPLINE.finditer(m_h.group(1)):
            hyp_label, kind, rest = hyp.group(1), hyp.group(2), hyp.group(3)
            info.mandatory_hyps.append(hyp_label)
            if kind == "f":
                parts = rest.split()
                if len(parts) == 2:
                    info.f_hyps.append((hyp_label, parts[0], parts[1]))
            else:
                info.e_hyps.append((hyp_label, rest.split()))
    info.has_e_hyp = bool(info.e_hyps)

    # Mandatory disjoint variable pairs (only the "mandatory" line)
    m_dj = re.search(
        r"Its mandatory disjoint variable pairs are:\s+(.*(?:\n\s+[^\n]*)*)",
        stdout,
    )
    if m_dj:
        info.disjoint = [(a, b) for a, b in _RE_DISJOINT.findall(m_dj.group(1))]

    return info


def _substitute(tokens: list[str], mapping: dict[str, list[str]]) -> list[str]:
    """Replace Metamath variable tokens by expression token sequences."""
    out: list[str] = []
    for tok in tokens:
        if tok in mapping:
            out.extend(mapping[tok])
        else:
            out.append(tok)
    return out


def _wff_cell(
    db_path: Path, typecode: str, expr: str, settings: Settings, tool: str | None
) -> list[str]:
    """Well-formedness proof of `typecode expr`: TOPLEVEL parse minus TOP.*."""
    rpn = parse_tree_rpn(db_path, f"{typecode} {expr}", settings, tool=tool)
    if not rpn:
        raise ValueError(f"cannot parse well-formedness of: {typecode} {expr}")
    return rpn[:-1]  # drop the trailing TOP.* wrapper step


def _check_instance(
    pattern_tokens: list[str], mapping: dict[str, list[str]], target: list[str], what: str
) -> None:
    """Require that substituting the mapping into pattern gives target verbatim."""
    got = " ".join(_substitute(pattern_tokens, mapping))
    want = " ".join(target)
    if got != want:
        raise ValueError(
            f"{what} does not match its expected instance:\n  expected: {want}\n  actual:   {got}"
        )


def _derive_chain(
    db_path: Path,
    calc: Calculation,
    theorem_statement: str,
    tool: str | None,
    settings: Settings | None,
) -> tuple[list[str], list[str]]:
    """Slice 2: two-step chain via one join rule (e.g. bitri)."""
    steps = calc.steps
    if len(steps) != 5:
        raise NotImplementedError("slice 2: exactly two relational steps (5 calc lines) supported")
    for i in (0, 2, 4):
        if steps[i].justification is not None:
            raise NotImplementedError("slice 2: only relational steps carry justifications")
    exprs: list[str] = [steps[i].expression for i in (0, 2, 4)]
    rel_steps = [steps[1], steps[3]]

    step_rules: list[str] = []
    join_refs: list[tuple[int | None, str]] = []
    for rel in rel_steps:
        just = rel.justification
        if just is None or len(just.rule_refs) != 1:
            raise NotImplementedError("slice 2: exactly one rule per relational step")
        if just.using_refs:
            raise NotImplementedError("slice 2: 'using' hints not supported")
        step_rules.append(just.rule_refs[0])
        join_refs.extend(just.join_refs)
    if len(join_refs) != 1:
        raise NotImplementedError("slice 2: exactly one join rule expected")
    if join_refs[0][0] is not None:
        raise NotImplementedError("slice 2: indexed joins not supported")
    join_label = join_refs[0][1]

    join = rule_info(db_path, join_label, tool=tool)
    step_infos = [rule_info(db_path, r, tool=tool) for r in step_rules]

    for info in step_infos:
        if info.has_e_hyp:
            raise NotImplementedError(f"slice 2: step rule {info.label} has $e hypotheses")

    if len(join.f_hyps) != len(exprs):
        raise ValueError(
            f"join rule {join_label} needs {len(exprs)} $f hyps, has {len(join.f_hyps)}"
        )
    if len(join.e_hyps) != len(step_rules):
        raise ValueError(
            f"join rule {join_label} needs {len(step_rules)} $e hyps, has {len(join.e_hyps)}"
        )

    # Substitute the join rule's $f variables by the calc expressions, in order.
    mapping: dict[str, list[str]] = {}
    for (_lab, _typ, var), expr in zip(join.f_hyps, exprs, strict=True):
        mapping[var] = expr.split()

    _check_instance(join.conclusion, mapping, theorem_statement.split(), "theorem statement")
    for (_e_lab, e_stmt), info in zip(join.e_hyps, step_infos, strict=True):
        _check_instance(e_stmt, mapping, info.conclusion, f"step {info.label}")

    if settings is None:
        raise NotImplementedError("slice 2: settings required for expression parsing")

    # Emit one well-formedness cell per $f hyp, then one step proof per $e
    # hyp, all in the join rule's mandatory-hyp RPN order, then the join rule.
    f_by_label = {
        lab: (typ, expr) for (lab, typ, _var), expr in zip(join.f_hyps, exprs, strict=True)
    }
    e_by_label = {lab: info for (lab, _stmt), info in zip(join.e_hyps, step_infos, strict=True)}
    tokens: list[str] = []
    for hyp_label in join.mandatory_hyps:
        if hyp_label in f_by_label:
            typ, expr = f_by_label[hyp_label]
            tokens.extend(_wff_cell(db_path, typ, expr, settings, tool))
        else:
            info = e_by_label[hyp_label]
            tokens.extend(info.mandatory_hyps + [info.label])
    tokens.append(join_label)

    disjoint = list(join.disjoint)
    for info in step_infos:
        disjoint.extend(info.disjoint)
    return tokens, [f"{a} {b}" for a, b in disjoint]


def derive_calc_proof(
    db_path: Path,
    calc: Calculation,
    theorem_statement: str,
    tool: str | None = None,
    settings: Settings | None = None,
) -> tuple[list[str], list[str]]:
    """Derive proof tokens for a calc.

    Returns ``(tokens, disjoint)`` where ``disjoint`` is a list of
    ``"x y"`` disjoint-variable constraints the generated theorem block
    must declare for the proof to verify.

    Slice 1 handles a single relational step; slice 2 handles a two-step
    chain joined by a transitivity rule.  Raises UnsupportedError/ValueError
    if the calc has another shape.
    """
    if len(calc.steps) == 5:
        return _derive_chain(db_path, calc, theorem_statement, tool, settings)

    steps = calc.steps
    if len(steps) != 3:
        raise NotImplementedError("slice 1: exactly one relational step (3 calc lines) supported")
    expr_left, rel_step, expr_right = steps
    if expr_left.justification is not None or expr_right.justification is not None:
        raise NotImplementedError("slice 1: only the relational step may carry a justification")
    if rel_step.justification is None or len(rel_step.justification.rule_refs) != 1:
        raise NotImplementedError("slice 1: exactly one rule in the relation step's hint")
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
