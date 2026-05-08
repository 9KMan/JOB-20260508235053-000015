"""Data Validator - Config-driven schema validation."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class Validator:
    FIELD_TYPES = {"string", "integer", "float", "email", "date", "enum", "boolean"}

    def __init__(self, schema: Dict[str, Any], fail_mode: str = "skip"):
        self.schema = schema
        self.fail_mode = fail_mode
        self._errors = []

    def validate(self, record: Dict[str, Any], row_num: int = 0) -> tuple[bool, List[Dict[str, Any]]]:
        errors = []
        fields = self.schema.get("fields", [])

        for field_def in fields:
            field_name = field_def.get("name")
            field_type = field_def.get("type", "string")
            required = field_def.get("required", False)
            enum_values = field_def.get("enum_values", [])
            custom_msg = field_def.get("error_message", f"Invalid value for '{field_name}'")

            value = record.get(field_name)

            if value is None or value == "":
                if required:
                    errors.append({
                        "row": row_num,
                        "field": field_name,
                        "reason": f"Required field is missing or empty (got: {repr(value)})"
                    })
                continue

            if field_type == "string":
                if not isinstance(value, str):
                    errors.append({"row": row_num, "field": field_name, "reason": custom_msg})

            elif field_type == "integer":
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append({"row": row_num, "field": field_name, "reason": custom_msg})

            elif field_type == "float":
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append({"row": row_num, "field": field_name, "reason": custom_msg})

            elif field_type == "email":
                if not self._is_valid_email(str(value)):
                    errors.append({"row": row_num, "field": field_name, "reason": "Invalid email format"})

            elif field_type == "date":
                if not self._is_valid_date(str(value)):
                    errors.append({"row": row_num, "field": field_name, "reason": "Invalid date format (expected YYYY-MM-DD)"})

            elif field_type == "enum":
                if str(value) not in enum_values:
                    errors.append({"row": row_num, "field": field_name, "reason": f"Value must be one of {enum_values}"})

            elif field_type == "boolean":
                if str(value).lower() not in ("true", "false", "1", "0", "yes", "no"):
                    errors.append({"row": row_num, "field": field_name, "reason": custom_msg})

        return (len(errors) == 0, errors)

    def _is_valid_email(self, email: str) -> bool:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def _is_valid_date(self, date_str: str) -> bool:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def get_errors(self) -> List[Dict[str, Any]]:
        return self._errors

    def add_error(self, error: Dict[str, Any]) -> None:
        self._errors.append(error)

    def clear_errors(self) -> None:
        self._errors = []