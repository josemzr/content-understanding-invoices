from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from azure.core.exceptions import AzureError

from invoice_demo.azure_services import AzureDocumentServices
from invoice_demo.config import Settings
from invoice_demo.evaluation import evaluate_report
from invoice_demo.templates import ROUTER_ANALYZER_ID


def _existing_file(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File does not exist: {path}")
    return path


def _write_json(payload: Any, output: Path | None) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if output is None:
        print(serialized)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{serialized}\n", encoding="utf-8")
    print(f"Wrote {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invoice-demo",
        description="Compare Azure Content Understanding and Document Intelligence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser(
        "setup", help="Create invoice, delivery-note and router analyzers."
    )
    setup.add_argument("--replace", action="store_true", help="Replace analyzers if they exist.")

    inspect_parser = subparsers.add_parser("inspect", help="Show models supported by an analyzer.")
    inspect_parser.add_argument("analyzer_id", nargs="?", default=ROUTER_ANALYZER_ID)

    analyze = subparsers.add_parser("analyze", help="Analyze one local PDF or image.")
    analyze.add_argument("document", type=_existing_file)
    analyze.add_argument("--provider", choices=("cu", "di"), default="cu")
    analyze.add_argument("--analyzer-id", default=ROUTER_ANALYZER_ID)
    analyze.add_argument("--di-model-id", default="prebuilt-invoice")
    analyze.add_argument("--output", type=Path)

    compare = subparsers.add_parser("compare", help="Run both services and score against truth.")
    compare.add_argument("document", type=_existing_file)
    compare.add_argument("ground_truth", type=_existing_file)
    compare.add_argument("--analyzer-id", default=ROUTER_ANALYZER_ID)
    compare.add_argument("--di-model-id", default="prebuilt-invoice")
    compare.add_argument("--output", type=Path)
    return parser


def run(args: argparse.Namespace, services: AzureDocumentServices) -> int:
    if args.command == "setup":
        _write_json(services.setup_analyzers(replace=args.replace), None)
        return 0

    if args.command == "inspect":
        _write_json(services.inspect_analyzer(args.analyzer_id), None)
        return 0

    if args.command == "analyze":
        if args.provider == "cu":
            report = services.analyze_content_understanding(args.document, args.analyzer_id)
        else:
            report = services.analyze_document_intelligence(args.document, args.di_model_id)
        _write_json(report.to_dict(), args.output)
        return 0

    if args.command == "compare":
        ground_truth = json.loads(args.ground_truth.read_text(encoding="utf-8"))
        cu_report = services.analyze_content_understanding(args.document, args.analyzer_id)
        di_report = services.analyze_document_intelligence(args.document, args.di_model_id)
        payload = {
            "content_understanding": {
                "report": cu_report.to_dict(),
                "evaluation": evaluate_report(cu_report, ground_truth),
            },
            "document_intelligence": {
                "report": di_report.to_dict(),
                "evaluation": evaluate_report(di_report, ground_truth),
            },
        }
        _write_json(payload, args.output)
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    services = AzureDocumentServices(Settings.from_environment())
    try:
        raise SystemExit(run(args, services))
    except (AzureError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    finally:
        services.close()
