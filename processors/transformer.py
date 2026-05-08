"""Transformer Engine - Chainable transforms for data processing."""

import re
import multiprocessing
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from functools import partial


class Transformer:
    BUILT_IN_TRANSFORMS = {
        "strip": lambda x: str(x).strip() if x is not None else x,
        "lowercase": lambda x: str(x).lower() if x is not None else x,
        "uppercase": lambda x: str(x).upper() if x is not None else x,
        "title_case": lambda x: str(x).title() if x is not None else x,
        "remove_special_chars": lambda x: re.sub(r"[^a-zA-Z0-9\s]", "", str(x)) if x is not None else x,
        "parse_date": lambda x: _parse_date(x),
        "to_integer": lambda x: int(float(x)) if x is not None else None,
        "to_float": lambda x: float(x) if x is not None else None,
        "to_string": lambda x: str(x) if x is not None else x,
        "remove_whitespace": lambda x: re.sub(r"\s+", " ", str(x)).strip() if x is not None else x,
        "remove_digits": lambda x: re.sub(r"\d", "", str(x)) if x is not None else x,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._custom_transforms = {}
        self._filter_fn = None
        self._chain = []

    def register_transform(self, name: str, func: Callable) -> None:
        self._custom_transforms[name] = func

    def strip(self, field: str) -> "Transformer":
        self._chain.append(("strip", field))
        return self

    def lowercase(self, field: str) -> "Transformer":
        self._chain.append(("lowercase", field))
        return self

    def uppercase(self, field: str) -> "Transformer":
        self._chain.append(("uppercase", field))
        return self

    def title_case(self, field: str) -> "Transformer":
        self._chain.append(("title_case", field))
        return self

    def remove_special_chars(self, field: str) -> "Transformer":
        self._chain.append(("remove_special_chars", field))
        return self

    def normalize_phone(self, field: str) -> "Transformer":
        self._chain.append(("normalize_phone", field))
        return self

    def enrich(self, field: str, value: Any) -> "Transformer":
        self._chain.append(("enrich", field, value))
        return self

    def filter(self, predicate: Callable[[Dict], bool]) -> "Transformer":
        self._filter_fn = predicate
        return self

    def apply_transforms(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        result = record.copy()

        for step in self._chain:
            if step[0] == "enrich":
                _, field, value = step
                if callable(value):
                    result[field] = value(result)
                else:
                    result[field] = value
            else:
                transform_name = step[1] if len(step) > 1 else step[0]
                field = step[1] if len(step) > 1 else None

                if field and field in result:
                    transform_fn = self._get_transform(transform_name)
                    if transform_fn:
                        result[field] = transform_fn(result[field])

        if self._filter_fn and not self._filter_fn(result):
            return None

        return result

    def transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.apply_transforms(record)

    def _get_transform(self, name: str) -> Optional[Callable]:
        if name in self._custom_transforms:
            return self._custom_transforms[name]
        if name in self.BUILT_IN_TRANSFORMS:
            return self.BUILT_IN_TRANSFORMS[name]
        if name == "normalize_phone":
            return self._normalize_phone
        return None

    def _normalize_phone(self, value: Any) -> str:
        digits = re.sub(r"\D", "", str(value))
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == "1":
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return str(value)

    def from_config(self, transform_names: List[str]) -> "Transformer":
        for name in transform_names:
            if name in self.BUILT_IN_TRANSFORMS:
                self._chain.append((name, None))
            elif hasattr(self, name):
                self._chain.append((name, None))
        return self


def _parse_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    value_str = str(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(value_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value_str


class TransformPipeline:
    def __init__(self, transforms: List[Callable], parallel: bool = False, workers: Optional[int] = None):
        self.transforms = transforms
        self.parallel = parallel
        self.workers = workers or multiprocessing.cpu_count()

    def process(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.parallel:
            return self._process_parallel(records)
        return self._process_sequential(records)

    def _process_sequential(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for record in records:
            processed = record
            for transform in self.transforms:
                if processed is None:
                    break
                processed = transform(processed)
            if processed is not None:
                result.append(processed)
        return result

    def _process_parallel(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        with multiprocessing.Pool(processes=self.workers) as pool:
            result = pool.map(self._apply_all_transforms, records)
        return [r for r in result if r is not None]

    def _apply_all_transforms(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        processed = record
        for transform in self.transforms:
            if processed is None:
                break
            processed = transform(processed)
        return processed