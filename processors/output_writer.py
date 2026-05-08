"""Output Writer - CSV, JSON, SQLite, API output support."""

import csv
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class OutputWriter:
    def __init__(self, output_path: Union[str, Path], output_format: str = "auto"):
        self.output_path = Path(output_path)
        self.output_format = output_format
        self._conn = None

    def write(self, records: List[Dict[str, Any]], mode: str = "write") -> None:
        if self.output_format == "auto":
            self.output_format = self._detect_format()

        if self.output_format == "csv":
            self._write_csv(records)
        elif self.output_format == "json":
            self._write_json(records)
        elif self.output_format == "ndjson":
            self._write_ndjson(records)
        elif self.output_format == "sqlite":
            self._write_sqlite(records, mode)
        elif self.output_format == "api":
            raise NotImplementedError("API output requires endpoint configuration")

    def _detect_format(self) -> str:
        ext = self.output_path.suffix.lower().lstrip(".")
        if ext in ("csv",):
            return "csv"
        elif ext in ("ndjson", "jsonl"):
            return "ndjson"
        elif ext == "json":
            return "json"
        elif ext in ("db", "sqlite", "sqlite3"):
            return "sqlite"
        return "json"

    def _write_csv(self, records: List[Dict[str, Any]], append: bool = False) -> None:
        if not records:
            return

        mode = "a" if append else "w"
        with open(self.output_path, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            if not append:
                writer.writeheader()
            writer.writerows(records)

    def _write_json(self, records: List[Dict[str, Any]], pretty: bool = True) -> None:
        with open(self.output_path, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(records, f, indent=2, ensure_ascii=False)
            else:
                json.dump(records, f, ensure_ascii=False)

    def _write_ndjson(self, records: List[Dict[str, Any]]) -> None:
        with open(self.output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _write_sqlite(self, records: List[Dict[str, Any]], mode: str = "replace") -> None:
        if not records:
            return

        self._conn = sqlite3.connect(str(self.output_path))
        cursor = self._conn.cursor()

        if mode == "replace":
            cursor.execute("DROP TABLE IF EXISTS records")

        columns = list(records[0].keys())
        column_defs = ", ".join([f'"{col}" TEXT' for col in columns])
        cursor.execute(f"CREATE TABLE IF NOT EXISTS records ({column_defs})")

        placeholders = ", ".join(["?" for _ in columns])
        for record in records:
            values = [str(record.get(col, "")) for col in columns]
            cursor.execute(f"INSERT INTO records VALUES ({placeholders})", values)

        self._conn.commit()
        self._conn.close()

    def write_api(self, records: List[Dict[str, Any]], endpoint: str, retry: int = 3) -> dict:
        import requests
        last_error = None

        for attempt in range(retry):
            try:
                response = requests.post(endpoint, json=records, timeout=30)
                response.raise_for_status()
                return {"success": True, "status_code": response.status_code}
            except Exception as e:
                last_error = str(e)
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)

        return {"success": False, "error": last_error}

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


class CSVWriter:
    def __init__(self, path: Union[str, Path], delimiter: str = ",", quoting: str = "minimal"):
        self.path = Path(path)
        self.delimiter = delimiter
        self.quoting = quoting
        self._file = None
        self._writer = None

    def open(self, append: bool = False) -> None:
        mode = "a" if append else "w"
        self._file = open(self.path, mode, encoding="utf-8", newline="")
        self._writer = None

    def write_header(self, fields: List[str]) -> None:
        if self._file:
            writer = csv.DictWriter(self._file, fieldnames=fields, delimiter=self.delimiter)
            writer.writeheader()
            self._writer = writer

    def write_row(self, record: Dict[str, Any]) -> None:
        if self._file is None:
            return
        if self._writer is None:
            writer = csv.DictWriter(self._file, fieldnames=record.keys(), delimiter=self.delimiter)
            self._writer = writer
            writer.writeheader()
        self._writer.writerow(record)

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None


class JSONWriter:
    def __init__(self, path: Union[str, Path], pretty: bool = True):
        self.path = Path(path)
        self.pretty = pretty
        self._file = None

    def open(self) -> None:
        self._file = open(self.path, "w", encoding="utf-8")

    def write(self, data: Any) -> None:
        if self._file:
            if self.pretty:
                json.dump(data, self._file, indent=2, ensure_ascii=False)
            else:
                json.dump(data, self._file, ensure_ascii=False)

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None