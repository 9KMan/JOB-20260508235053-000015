"""Error Handler + Logging - Structured logging with error tracking."""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class ErrorHandler:
    def __init__(
        self,
        log_level: str = "INFO",
        log_path: Optional[Union[str, Path]] = None,
        fail_mode: str = "skip"
    ):
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_path = Path(log_path) if log_path else None
        self.fail_mode = fail_mode
        self.errors = []
        self._setup_logger()

    def _setup_logger(self) -> None:
        self.logger = logging.getLogger("data_processor")
        self.logger.setLevel(self.log_level)

        if self.logger.handlers:
            self.logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        if self.log_path:
            file_handler = logging.FileHandler(str(self.log_path), encoding="utf-8")
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log_error(self, error: Dict[str, Any]) -> None:
        self.errors.append(error)
        self.logger.error(f"Row {error.get('row', '?')}: {error.get('field', '?')} - {error.get('reason', 'Unknown error')}")

    def log_warning(self, message: str) -> None:
        self.logger.warning(message)

    def log_info(self, message: str) -> None:
        self.logger.info(message)

    def log_debug(self, message: str) -> None:
        self.logger.debug(message)

    def should_continue(self) -> bool:
        if self.fail_mode == "halt":
            return False
        return True

    def get_errors(self) -> List[Dict[str, Any]]:
        return self.errors

    def clear_errors(self) -> None:
        self.errors = []


class SummaryReport:
    def __init__(self):
        self.processed = 0
        self.succeeded = 0
        self.failed = 0
        self.start_time = None
        self.end_time = None
        self.errors = []

    def start(self) -> None:
        self.start_time = time.time()

    def finish(self) -> None:
        self.end_time = time.time()

    def record_success(self) -> None:
        self.succeeded += 1
        self.processed += 1

    def record_failure(self, error: Dict[str, Any]) -> None:
        self.failed += 1
        self.processed += 1
        self.errors.append(error)

    def get_duration(self) -> float:
        if self.start_time and self.end_time:
            return round(self.end_time - self.start_time, 2)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "duration_seconds": self.get_duration(),
            "errors": self.errors[:100]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def print_summary(self) -> None:
        duration = self.get_duration()
        print("\n" + "=" * 50)
        print("PROCESSING SUMMARY")
        print("=" * 50)
        print(f"Total processed: {self.processed}")
        print(f"Succeeded:       {self.succeeded}")
        print(f"Failed:          {self.failed}")
        print(f"Duration:        {duration}s")
        if self.errors:
            print("\nFirst 5 errors:")
            for err in self.errors[:5]:
                print(f"  Row {err.get('row', '?')}: {err.get('field', '?')} - {err.get('reason', 'Unknown')}")
        print("=" * 50)


class ErrorLogWriter:
    def __init__(self, log_path: Union[str, Path]):
        self.log_path = Path(log_path)
        self._file = None

    def open(self) -> None:
        self._file = open(self.log_path, "a", encoding="utf-8")

    def write_error(self, error: Dict[str, Any]) -> None:
        if self._file:
            self._file.write(json.dumps(error, ensure_ascii=False) + "\n")

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    fail_mode: str = "skip"
) -> ErrorHandler:
    return ErrorHandler(
        log_level=level,
        log_path=log_file,
        fail_mode=fail_mode
    )