"""CLI entry point for mmcalc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mmcalc import __version__
from mmcalc.parser import parse_file


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify that a .mm file passes metamath-knife verification."""
    from mmcalc.knife import verify

    try:
        result = verify(Path(args.database))
        print(result.stdout, end="")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_parse(args: argparse.Namespace) -> int:
    """Parse an mmcalc proof file and display its structure."""
    try:
        pf = parse_file(Path(args.file))
        print(f"Context: {pf.context_label}")
        print(f"Context line: {pf.context_line}")
        print(f"Calculations: {len(pf.calculations)}")
        for i, calc in enumerate(pf.calculations):
            print(f"\n  Calculation {i + 1}:")
            for j, step in enumerate(calc.steps):
                just_str = ""
                if step.justification:
                    refs = ", ".join(step.justification.rule_refs)
                    just_str = f" (by {refs})"
                print(f"    {j}: {step.expression}{just_str}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_statements(args: argparse.Namespace) -> int:
    """List statements in a Metamath database."""
    from mmcalc.knife import dump_statements

    try:
        labels = dump_statements(Path(args.database))
        for label in labels:
            print(label)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_outline(args: argparse.Namespace) -> int:
    """Show the outline of a Metamath database."""
    from mmcalc.knife import dump_outline

    try:
        outline = dump_outline(Path(args.database))
        print(outline, end="")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="mmcalc",
        description="Calculational proofs for Metamath",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command")

    # verify subcommand
    p_verify = sub.add_parser("verify", help="Verify a Metamath database")
    p_verify.add_argument("database", help="Path to .mm file")

    # parse subcommand
    p_parse = sub.add_parser("parse", help="Parse an mmcalc proof file")
    p_parse.add_argument("file", help="Path to .mcalc file")

    # statements subcommand
    p_stmts = sub.add_parser("statements", help="List statements in a database")
    p_stmts.add_argument("database", help="Path to .mm file")

    # outline subcommand
    p_outline = sub.add_parser("outline", help="Show database outline")
    p_outline.add_argument("database", help="Path to .mm file")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "verify": cmd_verify,
        "parse": cmd_parse,
        "statements": cmd_statements,
        "outline": cmd_outline,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
