"""CLI Entry Point for Data Processing Automation Framework."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from processors import FileLoader, Validator, Transformer, TransformPipeline, OutputWriter
from utils import ErrorHandler, SummaryReport, setup_logging


def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_pipeline(args: argparse.Namespace) -> int:
    config = load_config(args.config) if args.config else {}

    if args.input:
        config["input"] = {"path": args.input}
    if args.output:
        config["output"] = {"path": args.output, "format": args.format or "auto"}

    input_config = config.get("input", {})
    output_config = config.get("output", {})
    schema_config = config.get("schema", {})
    transform_names = config.get("transforms", [])
    error_mode = config.get("error_mode", "skip" if not args.fail_halt else "halt")
    log_level = config.get("logging", {}).get("level", args.log_level or "INFO")
    log_path = config.get("logging", {}).get("path", args.log_file)

    error_handler = setup_logging(log_level, log_path, error_mode)
    summary = SummaryReport()
    summary.start()

    loader = FileLoader()
    validator = Validator(schema_config, fail_mode=error_mode) if schema_config.get("fields") else None
    transformer = Transformer(config)

    input_path = input_config.get("path")
    if not input_path:
        error_handler.log_error({"row": 0, "field": "input", "reason": "No input path specified"})
        return 1

    file_format = input_config.get("format", "auto")

    try:
        records = []
        row_num = 0

        for record in loader.load(input_path, file_format):
            row_num += 1
            record_copy = dict(record)

            if validator:
                valid, errors = validator.validate(record_copy, row_num)
                if not valid:
                    for err in errors:
                        error_handler.log_error(err)
                        summary.record_failure(err)
                    if error_mode == "halt":
                        break
                    continue

            for transform_name in transform_names:
                transform_fn = transformer._get_transform(transform_name)
                if transform_fn and transform_name in record_copy:
                    try:
                        record_copy[transform_name] = transform_fn(record_copy[transform_name])
                    except Exception as e:
                        error_handler.log_error({
                            "row": row_num,
                            "field": transform_name,
                            "reason": str(e)
                        })

            transformed = transformer.apply_transforms(record_copy)
            if transformed:
                records.append(transformed)
                summary.record_success()
            else:
                summary.record_success()

        output_path = output_config.get("path")
        if output_path:
            output_format = output_config.get("format", "auto")
            writer = OutputWriter(output_path, output_format)
            writer.write(records)

        summary.finish()
        summary.print_summary()

    except Exception as e:
        error_handler.log_error({"row": 0, "field": "pipeline", "reason": str(e)})
        return 1

    return 0


def validate_command(args: argparse.Namespace) -> int:
    if not args.input:
        print("Error: --input is required for validate command")
        return 1

    schema_path = args.schema
    if not schema_path:
        print("Error: --schema is required for validate command")
        return 1

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    loader = FileLoader()
    validator = Validator(schema)

    error_handler = setup_logging(args.log_level or "INFO", args.log_file, "skip")
    summary = SummaryReport()
    summary.start()

    row_num = 0
    for record in loader.load(args.input):
        row_num += 1
        valid, errors = validator.validate(record, row_num)
        if not valid:
            for err in errors:
                error_handler.log_error(err)
                summary.record_failure(err)

    summary.finish()
    summary.print_summary()

    return 0


def batch_command(args: argparse.Namespace) -> int:
    config = load_config(args.config) if args.config else {}
    input_dir = Path(args.input_dir)

    if not input_dir.exists():
        print(f"Error: Directory not found: {input_dir}")
        return 1

    files = list(input_dir.glob("*.csv")) + list(input_dir.glob("*.json")) + list(input_dir.glob("*.txt"))
    if not files:
        print(f"No processable files found in {input_dir}")
        return 1

    print(f"Found {len(files)} files to process")

    results = []
    for file_path in files:
        print(f"\nProcessing: {file_path.name}")
        args.input = str(file_path)
        ret = run_pipeline_with_config(args, config)
        results.append((file_path.name, ret))

    print("\n" + "=" * 50)
    print("BATCH SUMMARY")
    print("=" * 50)
    for name, ret in results:
        status = "OK" if ret == 0 else "FAILED"
        print(f"  {name}: {status}")

    return 0


def run_pipeline_with_config(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    return run_pipeline(args)


def report_command(args: argparse.Namespace) -> int:
    if not args.log:
        print("Error: --log is required for report command")
        return 1

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"Error: Log file not found: {log_path}")
        return 1

    errors = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    errors.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    print(f"\nTotal errors in log: {len(errors)}")
    if errors:
        print("\nFirst 10 errors:")
        for err in errors[:10]:
            print(f"  Row {err.get('row', '?')}: {err.get('field', '?')} - {err.get('reason', 'Unknown')}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Data Processing Automation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Run full pipeline")
    run_parser.add_argument("-i", "--input", help="Input file path")
    run_parser.add_argument("-o", "--output", help="Output file path")
    run_parser.add_argument("-c", "--config", help="Config JSON file")
    run_parser.add_argument("-f", "--format", help="Output format (csv|json|sqlite)")
    run_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    run_parser.add_argument("--log-file", help="Log file path")
    run_parser.add_argument("--fail-halt", action="store_true", help="Halt on first error")
    run_parser.add_argument("--dry-run", action="store_true", help="Validate only, no output")
    run_parser.add_argument("--parallel", action="store_true", help="Enable multiprocessing")

    validate_parser = subparsers.add_parser("validate", help="Validate without transform")
    validate_parser.add_argument("-i", "--input", required=True, help="Input file path")
    validate_parser.add_argument("-s", "--schema", required=True, help="Schema JSON file")
    validate_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    validate_parser.add_argument("--log-file", help="Log file path")

    batch_parser = subparsers.add_parser("batch", help="Process all files in directory")
    batch_parser.add_argument("-i", "--input-dir", required=True, help="Input directory path")
    batch_parser.add_argument("-c", "--config", help="Config JSON file")
    batch_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")

    report_parser = subparsers.add_parser("report", help="Generate summary from error log")
    report_parser.add_argument("--log", required=True, help="Log file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "run":
        return run_pipeline(args)
    elif args.command == "validate":
        return validate_command(args)
    elif args.command == "batch":
        return batch_command(args)
    elif args.command == "report":
        return report_command(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())