"""File Loader - Auto-detect format, validate structure, stream-large-files."""

import csv
import json
import os
from pathlib import Path
from typing import Any, Generator, Iterator, Union


class FileLoader:
    SUPPORTED_FORMATS = {"csv", "json", "txt", "ndjson"}

    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self._format = None
        self._path = None

    def detect_format(self, path: Union[str, Path]) -> str:
        path = Path(path)
        ext = path.suffix.lower().lstrip(".")

        if ext in ("csv", "tsv"):
            return "csv"
        elif ext in ("ndjson", "jsonl"):
            return "ndjson"
        elif ext == "json":
            return "json"
        elif ext == "txt":
            return self._sniff_text_format(path)
        return "csv"

    def _sniff_text_format(self, path: Path) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                first_line = f.readline()
                if first_line.strip().startswith("["):
                    return "json"
                if "\t" in first_line and "," not in first_line:
                    return "csv"
                try:
                    json.loads(first_line)
                    return "ndjson"
                except json.JSONDecodeError:
                    pass
        except (UnicodeDecodeError, IOError):
            pass
        return "txt"

    def validate_file(self, path: Union[str, Path]) -> None:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"File is not readable: {path}")
        if path.stat().st_size == 0:
            raise ValueError(f"File is empty: {path}")

    def load(self, path: Union[str, Path], file_format: str = "auto") -> Iterator[dict]:
        path = Path(path)
        self._path = path

        if file_format == "auto":
            self._format = self.detect_format(path)
        else:
            self._format = file_format

        self.validate_file(path)

        if self._format == "csv":
            yield from self._load_csv(path)
        elif self._format == "ndjson":
            yield from self._load_ndjson(path)
        elif self._format == "json":
            yield from self._load_json(path)
        else:
            yield from self._load_txt(path)

    def _load_csv(self, path: Path) -> Generator[dict, None, None]:
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                sample = f.read(8192)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    reader = csv.DictReader(f, dialect=dialect)
                except csv.Error:
                    f.seek(0)
                    reader = csv.DictReader(f)
                for row in reader:
                    yield dict(row)
        except csv.Error:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield dict(row)

    def _load_json(self, path: Path) -> Generator[dict, None, None]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item
        elif isinstance(data, dict):
            yield data

    def _load_ndjson(self, path: Path) -> Generator[dict, None, None]:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    def _load_txt(self, path: Path) -> Generator[dict, None, None]:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                yield {"line": i, "content": line.rstrip("\n")}