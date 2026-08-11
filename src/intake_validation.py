from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import chardet
import pandas as pd

SUPPORTED_FORMATS = {"csv", "json", "xlsx", "xls", "parquet"}


def validate_file_exists(filepath: Path | str) -> tuple[bool, str]:
    filepath = Path(filepath)
    if not filepath.exists():
        return False, f"File not found: {filepath}"
    if filepath.stat().st_size == 0:
        return False, "File is empty"
    return True, "File exists and has content"


def validate_file_format(filepath: Path | str, allowed: Iterable[str] | None = None) -> tuple[bool, str]:
    allowed = set(allowed or SUPPORTED_FORMATS)
    extension = Path(filepath).suffix.lower().lstrip(".")
    if extension not in allowed:
        return False, f"Unsupported file format: {extension or 'unknown'}"
    return True, f"Format valid: {extension}"


def detect_encoding(filepath: Path | str) -> tuple[str, str]:
    filepath = Path(filepath)
    with open(filepath, "rb") as f:
        raw_bytes = f.read(10000)

    result = chardet.detect(raw_bytes)
    encoding = result.get("encoding") or "unknown"
    confidence = result.get("confidence", 0.0)
    return encoding, f"Detected encoding: {encoding} ({confidence:.0%})"


def _normalize_encoding_name(encoding: str | None) -> str:
    if not encoding:
        return "unknown"
    normalized = encoding.strip().lower().replace("_", "-")
    if normalized in {"utf8", "utf-8-sig"}:
        return "utf-8"
    return normalized


def validate_schema(df: pd.DataFrame, expected_cols: Iterable[str]) -> tuple[bool, str]:
    expected = set(expected_cols)
    actual = set(df.columns)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"Missing columns: {missing}")
        if extra:
            parts.append(f"Extra columns: {extra}")
        return False, " | ".join(parts)
    return True, "Schema valid"


def capture_stats(filepath: Path | str, df: pd.DataFrame) -> dict:
    filepath = Path(filepath)
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "file_size_mb": round(filepath.stat().st_size / (1024 * 1024), 3),
    }


def _load_dataframe(filepath: Path | str, file_format: str, encoding: str | None = None) -> pd.DataFrame:
    filepath = Path(filepath)
    file_format = file_format.lower()
    if file_format == "csv":
        encoding_name = encoding or "utf-8-sig"
        if encoding_name.lower() in {"utf-8", "utf8", "ascii", "unknown"}:
            encoding_name = "utf-8-sig"
        return pd.read_csv(filepath, encoding=encoding_name)
    if file_format == "json":
        return pd.read_json(filepath)
    if file_format in {"xlsx", "xls"}:
        return pd.read_excel(filepath)
    if file_format == "parquet":
        return pd.read_parquet(filepath)
    raise ValueError(f"Unsupported file format for loading: {file_format}")


def _save_report(report: dict, output_path: Path | str | None) -> None:
    if output_path is None:
        return
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)


def generate_validation_report(
    filepath: Path | str,
    expected_cols: Iterable[str],
    output_path: Path | str | None = None,
    expected_encoding: str = "utf-8",
    allowed_formats: Iterable[str] | None = None,
) -> dict:
    filepath = Path(filepath)
    report = {
        "timestamp": datetime.now().isoformat(),
        "filepath": str(filepath),
        "status": "failed",
        "checks": {},
    }

    exists_ok, exists_msg = validate_file_exists(filepath)
    report["checks"]["file_exists"] = exists_msg
    if not exists_ok:
        _save_report(report, output_path)
        return report

    format_ok, format_msg = validate_file_format(filepath, allowed_formats)
    report["checks"]["format"] = format_msg
    if not format_ok:
        _save_report(report, output_path)
        return report

    encoding, encoding_msg = detect_encoding(filepath)
    report["checks"]["encoding"] = encoding_msg
    normalized_encoding = _normalize_encoding_name(encoding)
    normalized_expected = _normalize_encoding_name(expected_encoding)
    if expected_encoding and normalized_encoding not in {normalized_expected, "ascii", "unknown"}:
        report["checks"]["encoding"] = (
            f"Detected {encoding} but expected {expected_encoding} ({encoding_msg.split(':',1)[1].strip()})"
        )
        _save_report(report, output_path)
        return report

    try:
        df = _load_dataframe(filepath, filepath.suffix.lower().lstrip("."), encoding=encoding if encoding != "unknown" else None)
    except Exception as exc:
        report["checks"]["load"] = f"Data loading failed: {exc}"
        _save_report(report, output_path)
        return report

    schema_ok, schema_msg = validate_schema(df, expected_cols)
    report["checks"]["schema"] = schema_msg
    if not schema_ok:
        _save_report(report, output_path)
        return report

    report["status"] = "success"
    report["statistics"] = capture_stats(filepath, df)
    _save_report(report, output_path)
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate dataset intake before any transformation.")
    parser.add_argument("filepath", help="Path to the input file to validate.")
    parser.add_argument("--expected-columns", nargs="+", required=True, help="List of expected columns for validation.")
    parser.add_argument(
        "--output",
        default="intake_validation_report.json",
        help="Optional output path for the validation report.",
    )
    parser.add_argument(
        "--expected-encoding",
        default="utf-8",
        help="Expected file encoding used for validation.",
    )
    args = parser.parse_args()

    report = generate_validation_report(
        Path(args.filepath),
        args.expected_columns,
        output_path=args.output,
        expected_encoding=args.expected_encoding,
    )
    if report["status"] != "success":
        raise SystemExit(1)
