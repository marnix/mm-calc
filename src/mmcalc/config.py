"""Configuration file parser for mmcalc settings files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    """Settings from a .settings file.

    The settings file provides both the database includes (``$[ ... $]``)
    and the TOPLEVEL parsing rules.  To parse the expression ``x y z`` we
    construct the unique proof tree of ``TOPLEVEL x y z``, and that proof
    tree *is* the parse tree.  ``toplevel_lines`` holds everything that is
    not an include, verbatim (e.g. ``$c TOPLEVEL $.`` and the ``TOP.* $a``
    axioms), so the parser never has to know any specific Metamath tokens.
    """

    database_includes: list[str] = field(default_factory=list)
    toplevel_lines: list[str] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)


def parse_settings(path: Path) -> Settings:
    """Parse a settings file containing $[ ... $] includes and other directives."""
    text = path.read_text(encoding="utf-8")
    settings = Settings()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        settings.raw_lines.append(stripped)
        m = re.match(r"\$\[\s*(.+?)\s*\$\]", stripped)
        if m:
            settings.database_includes.append(m.group(1))
        else:
            settings.toplevel_lines.append(stripped)
    return settings
