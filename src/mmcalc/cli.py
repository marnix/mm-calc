"""CLI entry point for mmcalc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mmcalc import __version__
from mmcalc.config import parse_settings
from mmcalc.generator import generate_mm
from mmcalc.parser import ProofFile, parse_file


def _autogenerate_tokens(
    pf: ProofFile,
    db_path: Path,
    tool: str | None = None,
) -> None:
    """Fill in theorem proof tokens from the calc steps, if absent.

    If the theorem has no proof tokens (or only a `?` placeholder),
    derive them from the first calculation via the proof engine and
    merge any required disjoint-variable constraints.
    """
    if pf.proof_tokens.strip() not in ("", "?") or not pf.calculations:
        return
    from mmcalc.engine import derive_calc_proof

    calc = pf.calculations[0]
    tokens, disjoint = derive_calc_proof(
        db_path, calc, pf.theorem_statement, tool=tool
    )
    pf.proof_tokens = " ".join(tokens)
    pf.disjoint = list(dict.fromkeys(list(pf.disjoint) + disjoint))


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate a .mm file from an .mmcalc file and verify it."""
    from mmcalc.knife import _mm_tool, run_knife

    mmcalc_path = Path(args.file)
    try:
        pf = parse_file(mmcalc_path)
    except Exception as e:
        print(f"Error parsing {mmcalc_path}: {e}", file=sys.stderr)
        return 1

    settings = None
    if args.settings:
        try:
            settings = parse_settings(Path(args.settings))
        except Exception as e:
            print(f"Error parsing settings {args.settings}: {e}", file=sys.stderr)
            return 1

    try:
        includes = (settings.database_includes if settings else []) + list(pf.settings)
        db_path = Path(includes[0]) if includes else Path("set.mm")
        _autogenerate_tokens(pf, db_path, tool=_mm_tool())
    except Exception as e:
        print(f"Error deriving proof tokens: {e}", file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else mmcalc_path.with_suffix(".mm")
    out_str = generate_mm(pf, settings)
    out_path.write_text(out_str, encoding="utf-8")
    print(f"Wrote {out_path}")

    if not args.no_verify:
        try:
            result = run_knife(["--verify"], out_path)
            print(result.stdout, end="")
            if result.returncode != 0:
                print(f"Verification FAILED for {out_path}", file=sys.stderr)
                return 1
            print(f"Verification passed for {out_path}")
            return 0
        except Exception as e:
            print(f"Error running metamath-knife: {e}", file=sys.stderr)
            return 1
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify that a .mm file passes metamath-knife verification."""
    from mmcalc.knife import verify

    try:
        result = verify(Path(args.database))
        print(result.stdout, end="")
        return 0 if result.returncode == 0 else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_parse(args: argparse.Namespace) -> int:
    """Parse an mmcalc proof file and display its structure."""
    try:
        pf = parse_file(Path(args.file))
        print(f"Settings: {pf.settings}")
        print(f"Theorem: {pf.theorem_label}: {pf.theorem_statement}")
        print(f"Hypotheses: {pf.hypotheses}")
        print(f"Disjoint: {pf.disjoint}")
        print(f"Has proof tokens: {bool(pf.proof_tokens)}")
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


def cmd_export(args: argparse.Namespace) -> int:
    """Export a proof from a database to .mmp format."""
    from mmcalc.knife import run_knife

    try:
        result = run_knife(["--export", args.label], Path(args.database))
        mmp = Path(f"{args.label}.mmp")
        print(f"Exported to {mmp}")
        return 0 if result.returncode == 0 else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_proof(args: argparse.Namespace) -> int:
    """Print a theorem's proof as an uncompressed label sequence."""
    from mmcalc.knife import show_normal_proof

    try:
        print(show_normal_proof(Path(args.database), args.label))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_statement(args: argparse.Namespace) -> int:
    """Show a statement (with its mandatory hypotheses)."""
    from mmcalc.knife import show_statement

    try:
        print(show_statement(Path(args.database), args.label), end="")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_parse_expr(args: argparse.Namespace) -> int:
    """Parse a Metamath expression via TOPLEVEL, printing its parse tree RPN."""
    from mmcalc.config import parse_settings
    from mmcalc.toplevel import parse_tree_rpn

    try:
        settings = parse_settings(Path(args.settings))
        db = Path(args.database)
        rpn = parse_tree_rpn(db, args.expression, settings)
        print(" ".join(rpn))
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

    # generate subcommand
    p_gen = sub.add_parser(
        "generate", help="Generate a .mm file from an .mmcalc file (and verify it)"
    )
    p_gen.add_argument("file", help="Path to .mmcalc file")
    p_gen.add_argument("-s", "--settings", help="Path to .settings file")
    p_gen.add_argument("-o", "--output", help="Output .mm path (default: <file>.mm)")
    p_gen.add_argument(
        "--no-verify", action="store_true", help="Skip metamath-knife verification"
    )

    # verify subcommand
    p_verify = sub.add_parser("verify", help="Verify a Metamath database")
    p_verify.add_argument("database", help="Path to .mm file")

    # parse subcommand
    p_parse = sub.add_parser("parse", help="Parse an mmcalc proof file")
    p_parse.add_argument("file", help="Path to .mmcalc file")

    # statements subcommand
    p_stmts = sub.add_parser("statements", help="List statements in a database")
    p_stmts.add_argument("database", help="Path to .mm file")

    # outline subcommand
    p_outline = sub.add_parser("outline", help="Show database outline")
    p_outline.add_argument("database", help="Path to .mm file")

    # export subcommand
    p_export = sub.add_parser("export", help="Export a proof to .mmp format")
    p_export.add_argument("label", help="Statement label")
    p_export.add_argument("database", help="Path to .mm file")

    # proof subcommand: print uncompressed label sequence via reference tool
    p_proof = sub.add_parser(
        "proof", help="Show a theorem's proof as uncompressed labels (via reference tool)"
    )
    p_proof.add_argument("label", help="Statement label")
    p_proof.add_argument("database", help="Path to .mm file")

    # statement subcommand: show a statement with its hypotheses
    p_statement = sub.add_parser(
        "statement", help="Show a statement (with its mandatory hypotheses)"
    )
    p_statement.add_argument("label", help="Statement label")
    p_statement.add_argument("database", help="Path to .mm file")

    # parse-expr subcommand: database-independent expression parsing
    p_px = sub.add_parser(
        "parse-expr",
        help="Parse a Metamath expression via TOPLEVEL and print its parse tree RPN",
    )
    p_px.add_argument("expression", help="Expression token sequence to parse")
    p_px.add_argument(
        "--database", required=True, help="Path to the database (e.g. set.mm)"
    )
    p_px.add_argument("--settings", required=True, help="Path to the .settings file")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "generate": cmd_generate,
        "verify": cmd_verify,
        "parse": cmd_parse,
        "statements": cmd_statements,
        "outline": cmd_outline,
        "export": cmd_export,
        "proof": cmd_proof,
        "statement": cmd_statement,
        "parse-expr": cmd_parse_expr,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
