"""Database-independent expression parsing via a TOPLEVEL token.

To parse the token sequence ``x y z`` we build a small Metamath database:

  - the target database (from settings, e.g. ``$[ set.mm $]``),
  - the TOPLEVEL declarations from settings (``$c TOPLEVEL $.`` and the
    ``TOP.* $a`` axioms), and
  - a synthetic ``$p`` statement ``LABEL $p TOPLEVEL x y z $= ? $.``

Then we let the reference Metamath program find the (essentially unique)
proof of that statement.  Its proof tree, read as a tree of syntax
statements, *is* the parse tree of ``x y z``.

Nothing in this module knows any specific Metamath token (no `(`, `)`,
`|-`, ``<->``, ``class``, ...); all vocabulary comes from the database and
the settings file.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from mmcalc.config import Settings

#: Label of the synthetic $p statement used for parsing.
_PARSE_LABEL = "MMCALCTOP"

#: Where to save the proof: as a sequence of statement labels ("/normal").
_PROOF_STYLE = "normal"


@dataclass
class ParseResult:
    """The parse of an expression, as the proof of `TOPLEVEL <tokens>`."""

    tokens: str
    rpn: list[str] = field(default_factory=list)  # proof labels in RPN order
    ok: bool = False
    error: str = ""


def _mm_tool() -> str:
    return os.environ.get("MM_TOOL", "metamath")


def _toplevel_token(settings: Settings) -> str:
    """The TOPLEVEL constant: the typecode used by the TOP.* axioms."""
    import re

    default = "TOPLEVEL"
    declared: set[str] = set()
    for line in settings.toplevel_lines:
        m = re.match(r"\$c\s+(.+?)\s*\$", line)
        if m:
            declared.update(m.group(1).split())
        m = re.match(r"\S+\s*\$a\s+(\S+)", line)
        if m and m.group(1) in declared:
            return m.group(1)
    return default


def _clip_proof(stdout: str) -> list[str] | None:
    """Extract the label sequence from `show proof <label> /normal` output."""
    marker = "Clip out the proof below this line to put it in the source file:"
    if marker not in stdout:
        return None
    body = stdout.split(marker, 1)[1].split("\n----", 1)[0]
    labels = " ".join(body.split()).rstrip("$.").strip().split()
    if labels == ["?"]:
        return None
    return labels or None


def toplevel_proof(
    db_path: Path,
    tokens: str,
    settings: Settings,
    tool: str | None = None,
) -> ParseResult:
    """Return the proof (parse tree in RPN) of `TOPLEVEL <tokens>`.

    ``db_path`` is the top database (e.g. ``set.mm``).  ``settings``
    supplies the database include and the TOPLEVEL rules.
    """
    result = ParseResult(tokens=tokens)
    db_path = db_path.resolve()
    tool = tool or _mm_tool()

    include = "$[ " + db_path.name + " $]"
    body = [include, ""]
    body.extend(settings.toplevel_lines)
    body.append("")
    toplevel_token = _toplevel_token(settings)
    body.append(f"{_PARSE_LABEL} $p {toplevel_token} {tokens} $= ? $.")

    tap = db_path.parent / f".mmcalc_toplevel_{os.getpid()}.tap.mm"
    try:
        tap.write_text("\n".join(body) + "\n", encoding="utf-8")
        cmds = [
            f'read "{tap}"',
            f"prove {_PARSE_LABEL}",
            "improve all",
            f"save new_proof /{_PROOF_STYLE}",
            f"show proof {_PARSE_LABEL} /{_PROOF_STYLE}",
            "exit",
        ]
        proc = subprocess.run(
            [tool, *cmds],
            capture_output=True,
            text=True,
            check=False,
            cwd=db_path.parent,
            timeout=120,
        )
        if proc.returncode != 0:
            result.error = proc.stdout or proc.stderr
            return result
        labels = _clip_proof(proc.stdout)
        if not labels:
            result.error = f"could not extract parse for: {tokens}"
            return result
        result.rpn = labels
        result.ok = True
        return result
    finally:
        tap.unlink(missing_ok=True)


def parse_tree_rpn(
    db_path: Path,
    tokens: str,
    settings: Settings,
    tool: str | None = None,
) -> list[str]:
    """Parse ``tokens`` and return the RPN label list of its parse tree.

    Raises ValueError if the expression cannot be parsed.
    """
    result = toplevel_proof(db_path, tokens, settings, tool=tool)
    if not result.ok:
        raise ValueError(result.error or f"unparseable: {tokens}")
    return result.rpn
