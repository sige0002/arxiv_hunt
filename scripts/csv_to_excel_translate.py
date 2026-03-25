#!/usr/bin/env python3
"""CLI tool for converting arXiv CSV results to Excel with TRANSLATE formulas.

Usage examples:
    python -m arxiv_hunt.scripts.csv_to_excel_translate
    python -m arxiv_hunt.scripts.csv_to_excel_translate --input data/csv/results.csv
    python -m arxiv_hunt.scripts.csv_to_excel_translate --input data/csv/results.csv --output out.xlsx
    python -m arxiv_hunt.scripts.csv_to_excel_translate --source-lang en --target-lang de
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from arxiv_hunt.config import CSV_OUTPUT_DIR, RESULTS_CSV_FILENAME
from arxiv_hunt.excel_converter import convert_csv_to_excel

logger = logging.getLogger(__name__)

# Default input CSV path
_DEFAULT_CSV_PATH = CSV_OUTPUT_DIR / RESULTS_CSV_FILENAME


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="csv_to_excel_translate",
        description=(
            "Convert an arXiv papers CSV file to an Excel workbook "
            "with TRANSLATE formulas for abstract translation."
        ),
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_DEFAULT_CSV_PATH,
        dest="input_path",
        help=f"Input CSV file path (default: {_DEFAULT_CSV_PATH}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        dest="output_path",
        help="Output Excel file path (auto-generated if not specified).",
    )
    parser.add_argument(
        "--source-lang",
        default="en",
        help='Source language code for TRANSLATE formula (default: "en").',
    )
    parser.add_argument(
        "--target-lang",
        default="ja",
        help='Target language code for TRANSLATE formula (default: "ja").',
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the csv_to_excel_translate CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("csv_to_excel_translate starting")
    logger.debug(
        "Parameters: input=%s, output=%s, source_lang=%s, target_lang=%s",
        args.input_path,
        args.output_path,
        args.source_lang,
        args.target_lang,
    )

    # Validate input file exists
    if not args.input_path.exists():
        logger.error("Input CSV file not found: %s", args.input_path)
        sys.exit(1)

    if not args.input_path.is_file():
        logger.error("Input path is not a file: %s", args.input_path)
        sys.exit(1)

    # Convert CSV to Excel
    try:
        output_path = convert_csv_to_excel(
            csv_path=args.input_path,
            output_path=args.output_path,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
        )
    except Exception:
        logger.exception("Failed to convert CSV to Excel.")
        sys.exit(1)

    print(f"Excel file created: {output_path}")
    print(f"  Source language: {args.source_lang}")
    print(f"  Target language: {args.target_lang}")
    print(f"  TRANSLATE formulas embedded for abstract translation.")


if __name__ == "__main__":
    main()
