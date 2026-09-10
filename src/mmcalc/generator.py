"""Generator: produces valid .mm files from calculational proofs."""

from __future__ import annotations

from mmcalc.config import Settings
from mmcalc.parser import ProofFile


def _wrap_proof(tokens: str, width: int = 78) -> list[str]:
    """Wrap whitespace-separated proof tokens to a given line width."""
    words = tokens.split()
    lines: list[str] = []
    line = ""
    for word in words:
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def generate_mm(pf: ProofFile, settings: Settings | None = None) -> str:
    """Generate the text of a .mm file from a parsed calculational proof.

    The generated file includes the databases from settings (or the file's
    own `$[ ... $]` lines), declares disjoint variables and hypotheses, and
    states the theorem with its proof tokens.

    If the theorem has no proof tokens yet, a `?` placeholder is emitted
    (the file will then not verify).
    """
    out: list[str] = []

    includes = list(pf.settings)
    if settings is not None:
        includes = list(settings.database_includes) + includes

    for db in includes:
        out.append(f"$[ {db} $]")

    if not (pf.disjoint or pf.hypotheses or pf.theorem_label):
        out.append("")
        return "\n".join(out)

    out.append("")
    out.append("${")

    for d in pf.disjoint:
        out.append(f"  $d {d} $.")

    for label, stmt in pf.hypotheses:
        label_part = f"{label} " if label else ""
        out.append(f"  {label_part}$e {stmt} $.")

    if pf.theorem_label:
        stmt = pf.theorem_statement
        proof = pf.proof_tokens.strip()
        out.append(f"  {pf.theorem_label} $p {stmt} $=")
        if proof:
            out.extend(f"    {line}" for line in _wrap_proof(proof))
            out.append("    $. ")
        else:
            out.append("    ? $. ")

    out.append("$}")
    return "\n".join(out)
