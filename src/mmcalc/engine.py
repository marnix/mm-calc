"""Proof engine: builds Metamath proof trees from calculational steps.

Uses metamath-knife to look up theorem statements and parse expressions,
then constructs proof trees by chaining rule applications.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from mmcalc.knife import dump_formula, dump_grammar, run_knife
from mmcalc.parser import Calculation, Justification, ProofFile, Step


@dataclass
class StatementInfo:
    """Information about a Metamath statement from dump-formula."""

    label: str
    formula_tokens: list[str] = field(default_factory=list)
    num_vars: int = 0


@dataclass
class ProofNode:
    """A node in a Metamath proof tree."""

    label: str
    children: list[ProofNode] = field(default_factory=list)
    is_hypothesis: bool = False


class ProofEngine:
    """Builds Metamath proof trees using metamath-knife for lookups."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._formula_cache: dict[str, StatementInfo] = {}
        self._grammar_dump: str | None = None

    def _load_formulas(self) -> None:
        """Load formula dump from metamath-knife."""
        if self._formula_cache:
            return
        result = dump_formula(self.database_path)
        for line in result.splitlines():
            line = line.strip()
            if not line or line.startswith("Formula") or line.startswith("0 "):
                continue
            m = re.match(r"(\S+):\s*(.*)", line)
            if m:
                label = m.group(1)
                tokens_str = m.group(2).strip()
                tokens = tokens_str.split() if tokens_str else []
                self._formula_cache[label] = StatementInfo(
                    label=label, formula_tokens=tokens
                )

    def get_statement_info(self, label: str) -> StatementInfo | None:
        """Get formula info for a statement label."""
        self._load_formulas()
        return self._formula_cache.get(label)

    def list_statements(self) -> list[str]:
        """List all statement labels in the database."""
        result = run_knife(["--list-statements"], self.database_path)
        labels = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("-") or line.startswith("0 "):
                continue
            parts = line.split()
            if parts:
                labels.append(parts[0])
        return labels

    def get_hypotheses(self, label: str) -> list[str]:
        """Get hypothesis labels for a theorem."""
        result = run_knife(["--list-statements"], self.database_path)
        lines = result.stdout.splitlines()
        found = False
        hyps: list[str] = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("0 "):
                if found:
                    break
                continue
            if line.startswith("-"):
                if found:
                    break
                continue
            if found:
                parts = line.split()
                if parts:
                    hyps.append(parts[0])
                continue
            parts = line.split()
            if parts and parts[0] == label:
                found = True
                # Check if previous lines were hypotheses
                # Actually, the format groups hypotheses with their conclusion
        return hyps

    def export_proof(self, label: str, dest: Path) -> str:
        """Export an existing proof to .mmp format."""
        run_knife(["--export", label], self.database_path)
        mmp_path = self.database_path.parent / f"{label}.mmp"
        if mmp_path.exists():
            content = mmp_path.read_text(encoding="utf-8")
            return content
        return ""

    def build_proof_tree(
        self, pf: ProofFile, settings_db: str
    ) -> ProofNode | None:
        """Build a proof tree from a parsed calculational proof file.

        This is a simplified version that constructs the proof structure.
        Full proof generation requires expression unification which is
        the core hard problem.
        """
        # For now, return a placeholder indicating the proof structure
        # This will be expanded as we implement the proof search
        return None


def generate_proof_tokens(
    engine: ProofEngine,
    calc: Calculation,
    theorem_label: str,
) -> str:
    """Generate Metamath proof tokens for a calculational proof.

    For the initial version, this outputs a proof stub that can be
    completed manually. Full auto-generation requires expression
    unification against the grammar.
    """
    # Collect all referenced labels from justifications
    labels_used: list[str] = []
    for step in calc.steps:
        if step.justification:
            for ref in step.justification.rule_refs:
                if ref not in labels_used:
                    labels_used.append(ref)
            for ref in step.justification.using_refs:
                if ref not in labels_used:
                    labels_used.append(ref)

    # Look up formulas for each referenced label
    formulas: dict[str, StatementInfo] = {}
    for label in labels_used:
        info = engine.get_statement_info(label)
        if info:
            formulas[label] = info

    # Build a placeholder proof token list
    # In a full implementation, this would perform unification
    token_parts = [f"({label})" for label in labels_used if label in formulas]
    return "".join(token_parts)
