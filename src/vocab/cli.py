"""Command line entry point; later sections add subcommands here."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from collections.abc import Sequence

from vocab.llm.roles import ROLES, Role


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level parser and register known subcommands."""
    parser = argparse.ArgumentParser(prog="vocab", description="vocab-coach commands")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    setup = sub.add_parser(
        "setup-nlp",
        help="Download the spaCy English model and the NLTK WordNet corpus",
    )
    setup.set_defaults(func=_cmd_setup_nlp)

    llm = sub.add_parser("llm", help="LLM utilities")
    llm_sub = llm.add_subparsers(dest="llm_command", metavar="<llm-command>")
    ping = llm_sub.add_parser("ping", help="Send a tiny request to a role's model")
    ping.add_argument("role", choices=ROLES)
    ping.set_defaults(func=_cmd_llm_ping)
    llm.set_defaults(func=_cmd_llm_help)

    lexicon = sub.add_parser("lexicon", help="Lexicon drafts (import via API)")
    lexicon_sub = lexicon.add_subparsers(dest="lexicon_command", metavar="<lexicon-command>")
    draft = lexicon_sub.add_parser(
        "draft",
        help="Draft groups via group_gen, or --kind confusable/idiom",
    )
    draft.add_argument("lemma", nargs="?", default=None, help="Head lemma (precision drafts)")
    draft.add_argument(
        "--kind",
        choices=("confusable", "idiom"),
        default=None,
        help="Draft a confusable or idiom set instead of a precision group",
    )
    draft.add_argument(
        "--words",
        default=None,
        help="Comma-separated words for --kind confusable",
    )
    draft.add_argument(
        "--lemma",
        dest="lemma_flag",
        default=None,
        help="Head lemma for --kind idiom",
    )
    draft.set_defaults(func=_cmd_lexicon_draft)
    lexicon.set_defaults(func=_cmd_lexicon_help)

    eval_parser = sub.add_parser("eval", help="Quality evals")
    eval_sub = eval_parser.add_subparsers(dest="eval_command", metavar="<eval-command>")
    editor_eval = eval_sub.add_parser("editor", help="Run the editor gold eval")
    editor_eval.add_argument("--model", default=None, help="Override LLM_EDITOR_MODEL")
    editor_eval.add_argument(
        "--prompt-version",
        type=int,
        default=None,
        dest="prompt_version",
        help="Override LLM_EDITOR_PROMPT_VERSION",
    )
    editor_eval.set_defaults(func=_cmd_eval_editor)
    disputes = eval_sub.add_parser(
        "drill-disputes",
        help="Export drill_disputed events since the last export file",
    )
    disputes.set_defaults(func=_cmd_eval_drill_disputes)
    eval_parser.set_defaults(func=_cmd_eval_help)

    srs = sub.add_parser("srs", help="Spaced-repetition utilities")
    srs_sub = srs.add_subparsers(dest="srs_command", metavar="<srs-command>")
    rebuild = srs_sub.add_parser("rebuild", help="Replay card_reviewed into srs_cards")
    rebuild.add_argument("--user", required=True, dest="user_id", help="Internal users.id")
    rebuild.set_defaults(func=_cmd_srs_rebuild)
    srs.set_defaults(func=_cmd_srs_help)

    db = sub.add_parser("db", help="Database utilities")
    db_sub = db.add_subparsers(dest="db_command", metavar="<db-command>")
    copy = db_sub.add_parser("copy-sqlite", help="Copy SQLite rows into Postgres")
    copy.add_argument("--sqlite", required=True, help="Source SQLAlchemy URL")
    copy.add_argument("--postgres", required=True, help="Target SQLAlchemy URL")
    copy.set_defaults(func=_cmd_db_copy_sqlite)
    db.set_defaults(func=_cmd_db_help)

    return parser


def _cmd_setup_nlp(_args: argparse.Namespace) -> int:
    """Fetch en_core_web_sm and WordNet so the analyzer can run offline."""
    print("Downloading spaCy model en_core_web_sm...")
    result = subprocess.run(
        [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
        check=False,
    )
    if result.returncode != 0:
        print("spaCy model download failed.", file=sys.stderr)
        return result.returncode

    print("Downloading NLTK WordNet corpus...")
    try:
        import nltk

        ok = nltk.download("wordnet")
    except OSError as exc:
        print(f"NLTK WordNet download failed: {exc}", file=sys.stderr)
        print(
            "If you are behind a proxy, set NLTK_ALLOW_PROXIED_URLOPEN=1 and retry.",
            file=sys.stderr,
        )
        return 1
    if not ok:
        print("NLTK WordNet download failed.", file=sys.stderr)
        print(
            "If you are behind a proxy, set NLTK_ALLOW_PROXIED_URLOPEN=1 and retry.",
            file=sys.stderr,
        )
        return 1

    print("NLP data ready.")
    return 0


def _cmd_llm_help(args: argparse.Namespace) -> int:
    """Print llm subcommand help when none was chosen."""
    if getattr(args, "llm_command", None) is None:
        print("usage: vocab llm ping <role>", file=sys.stderr)
        return 2
    return 0


def _cmd_llm_ping(args: argparse.Namespace) -> int:
    """Probe the configured model for a role and print reply plus latency."""
    from vocab.llm.client import ping

    role: Role = args.role
    try:
        content, latency_ms = asyncio.run(ping(role))
    except Exception as exc:  # noqa: BLE001  CLI must show any provider failure
        print(f"ping failed: {exc}", file=sys.stderr)
        return 1
    print(content)
    print(f"latency_ms={latency_ms}")
    return 0


def _cli_session():  # noqa: ANN202
    """Open a short-lived DB session for lexicon commands."""
    from sqlalchemy.orm import Session

    from vocab.db import get_engine

    return Session(get_engine())


def _cmd_lexicon_help(args: argparse.Namespace) -> int:
    if getattr(args, "lexicon_command", None) is None:
        print("usage: vocab lexicon draft ...", file=sys.stderr)
        print(
            "Import approved groups via POST /api/lexicon/import "
            "or POST /api/lexicon/import/builtin (admin).",
            file=sys.stderr,
        )
        return 2
    return 0


def _cmd_lexicon_draft(args: argparse.Namespace) -> int:
    from vocab.lexicon.service import draft_lemma, draft_set

    with _cli_session() as session:
        try:
            if args.kind:
                words = (
                    [w.strip() for w in args.words.split(",") if w.strip()] if args.words else None
                )
                lemma = args.lemma_flag or args.lemma
                groups = asyncio.run(draft_set(session, args.kind, words=words, lemma=lemma))
            else:
                if not args.lemma:
                    print("usage: vocab lexicon draft <lemma>", file=sys.stderr)
                    return 2
                groups = asyncio.run(draft_lemma(session, args.lemma))
        except Exception as exc:  # noqa: BLE001  surface provider/config errors
            print(f"draft failed: {exc}", file=sys.stderr)
            return 1
    for group in groups:
        head = group.head_lemma or "-"
        print(f"draft {group.id} kind={group.kind} ({head}) options={len(group.options)}")
    return 0


def _cmd_eval_help(args: argparse.Namespace) -> int:
    if getattr(args, "eval_command", None) is None:
        print(
            "usage: vocab eval {editor,drill-disputes} ...",
            file=sys.stderr,
        )
        return 2
    return 0


def _cmd_eval_drill_disputes(_args: argparse.Namespace) -> int:
    from vocab.drills.service import export_drill_disputes

    with _cli_session() as session:
        path = export_drill_disputes(session)
    print(path)
    return 0


def _cmd_eval_editor(args: argparse.Namespace) -> int:
    from vocab.editor.eval_runner import run_eval, write_results

    with _cli_session() as session:
        try:
            summary = asyncio.run(
                run_eval(
                    session,
                    model=args.model,
                    prompt_version=args.prompt_version,
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"eval failed: {exc}", file=sys.stderr)
            return 1
    path = write_results(summary)
    print(f"flag_recall={summary['flag_recall']}")
    print(f"false_flag_rate={summary['false_flag_rate']}")
    print(f"option_acceptability={summary['option_acceptability']}")
    print(f"inflation_count={summary['inflation_count']}")
    print(f"schema_failure_rate={summary['schema_failure_rate']}")
    print(f"median_latency_ms={summary['median_latency_ms']}")
    print(path)
    return 0


def _cmd_srs_help(args: argparse.Namespace) -> int:
    if getattr(args, "srs_command", None) is None:
        print("usage: vocab srs rebuild --user <id>", file=sys.stderr)
        return 2
    return 0


def _cmd_srs_rebuild(args: argparse.Namespace) -> int:
    from vocab.practice.srs import rebuild_cards

    with _cli_session() as session:
        rows = rebuild_cards(session, args.user_id)
    print(f"rebuilt cards={len(rows)}")
    return 0


def _cmd_db_help(args: argparse.Namespace) -> int:
    if getattr(args, "db_command", None) is None:
        print("usage: vocab db copy-sqlite --sqlite URL --postgres URL", file=sys.stderr)
        return 2
    return 0


def _cmd_db_copy_sqlite(args: argparse.Namespace) -> int:
    from vocab.db_copy import copy_sqlite_to_postgres, ping_engine

    try:
        ping_engine(args.sqlite)
        ping_engine(args.postgres)
        counts = copy_sqlite_to_postgres(sqlite_url=args.sqlite, postgres_url=args.postgres)
    except Exception as exc:  # noqa: BLE001
        print(f"copy failed: {exc}", file=sys.stderr)
        return 1
    for name, count in sorted(counts.items()):
        print(f"{name}={count}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return int(args.func(args))
