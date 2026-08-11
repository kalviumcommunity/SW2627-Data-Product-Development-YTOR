from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Iterable

import re
import pandas as pd


def _sample_bad_values(series: pd.Series, mask: pd.Series, limit: int = 5):
    return series[mask].dropna().unique().tolist()[:limit]


def enforce_datetime_column(
    df: pd.DataFrame,
    column: str,
    fmt: str,
    errors: str = "raise",
    fail_on_error: bool = False,
) -> Dict[str, Any]:
    """Convert `column` to datetime using explicit `fmt`.

    errors: passed to pandas `to_datetime` as `errors` param ('raise'|'coerce').
    If `fail_on_error` and conversion leaves any NaT values, raises ValueError with samples.
    Returns a report dict describing conversion.
    """
    before_dtype = str(df[column].dtype)
    original = df[column].copy()
    try:
        converted = pd.to_datetime(original, format=fmt, errors=errors)
    except Exception as exc:
        if fail_on_error:
            raise
        return {"status": "failed", "error": str(exc), "before_dtype": before_dtype}

    bad_mask = converted.isna() & original.notna()
    df[column] = converted
    bad_samples = _sample_bad_values(original, bad_mask)
    if bad_samples and fail_on_error:
        raise ValueError(f"Failed to convert values in {column}: {bad_samples}")

    return {
        "status": "success" if not bad_samples else "partial",
        "before_dtype": before_dtype,
        "after_dtype": str(df[column].dtype),
        "converted_count": int(converted.notna().sum()),
        "failed_samples": bad_samples,
    }


def enforce_currency_to_float(
    df: pd.DataFrame,
    column: str,
    currency_symbols: Iterable[str] | None = None,
    thousands_sep: str | None = ",",
    decimal: str = ".",
    fail_on_error: bool = False,
) -> Dict[str, Any]:
    """Strip currency symbols and thousands separators then convert to float.

    Returns a report. If `fail_on_error` and any values cannot be converted, raises ValueError.
    """
    before_dtype = str(df[column].dtype)
    text = df[column].astype(str).fillna("")
    symbols = currency_symbols or ["$", "€", "£", "¥", ","]
    # Build regex to remove currency symbols and grouping separators
    sym_pattern = "|".join(re.escape(s) for s in symbols if s != thousands_sep)
    # Remove currency symbols and whitespace
    cleaned = text.str.replace(rf"({sym_pattern})", "", regex=True)
    if thousands_sep:
        cleaned = cleaned.str.replace(thousands_sep, "")
    if decimal != ".":
        cleaned = cleaned.str.replace(decimal, ".")

    numeric = pd.to_numeric(cleaned.replace("", pd.NA), errors="coerce")
    df[column] = numeric
    failed_mask = numeric.isna() & cleaned.notna()
    failed_samples = _sample_bad_values(cleaned, failed_mask)
    if failed_samples and fail_on_error:
        raise ValueError(f"Failed to parse currency in {column}: {failed_samples}")

    return {
        "status": "success" if not failed_samples else "partial",
        "before_dtype": before_dtype,
        "after_dtype": str(df[column].dtype),
        "converted_count": int(numeric.notna().sum()),
        "failed_samples": failed_samples,
    }


def enforce_int_to_bool(
    df: pd.DataFrame,
    column: str,
    mapping: Dict[Any, bool] | None = None,
    fail_on_error: bool = False,
) -> Dict[str, Any]:
    """Convert integer-like or string values to boolean using `mapping`.

    If mapping is not provided, a default mapping of {0:False,1:True,'0':False,'1':True,'yes':True,'no':False,'true':True,'false':False} is used.
    """
    before_dtype = str(df[column].dtype)
    default_map = {0: False, 1: True, "0": False, "1": True, "yes": True, "no": False, "true": True, "false": False, True: True, False: False}
    mapping = mapping or default_map

    mapped = df[column].map(lambda v: mapping.get(v) if v in mapping else mapping.get(str(v).lower(), pd.NA))
    df[column] = mapped.astype("boolean")
    failed_mask = df[column].isna() & df[column].notna()  # always False because cast
    # Instead find original values that mapped to NA
    original_series = df[column]
    # derive failed samples by checking where mapping returned pd.NA prior to cast
    # We reconstruct mapping result using original values
    recon = df[column].astype(object)
    # find samples where conversion is <NA>
    failed = []
    for val in df[column].index:
        pass
    # Simpler: detect entries that are <NA> after mapping
    failed_mask = df[column].isna()
    failed_samples = []
    if failed_mask.any():
        failed_samples = df.loc[failed_mask].index.tolist()[:5]
    if failed_samples and fail_on_error:
        raise ValueError(f"Failed to convert values to bool in {column}: indices {failed_samples}")

    return {
        "status": "success" if not failed_samples else "partial",
        "before_dtype": before_dtype,
        "after_dtype": str(df[column].dtype),
        "converted_count": int(df[column].notna().sum()),
        "failed_samples": failed_samples,
    }


def enforce_types(df: pd.DataFrame, spec: Dict[str, Dict[str, Any]], fail_on_error: bool = False) -> Dict[str, Any]:
    """Apply a `spec` mapping column -> {type: 'datetime'|'currency'|'bool', ...}.

    Returns a dict of per-column reports.
    """
    reports: Dict[str, Any] = {}
    for col, conf in spec.items():
        typ = conf.get("type")
        if typ == "datetime":
            reports[col] = enforce_datetime_column(df, col, fmt=conf.get("format"), errors=conf.get("errors", "coerce"), fail_on_error=fail_on_error)
        elif typ == "currency":
            reports[col] = enforce_currency_to_float(df, col, currency_symbols=conf.get("symbols"), thousands_sep=conf.get("thousands_sep", ","), decimal=conf.get("decimal", "."), fail_on_error=fail_on_error)
        elif typ == "bool":
            reports[col] = enforce_int_to_bool(df, col, mapping=conf.get("mapping"), fail_on_error=fail_on_error)
        elif typ == "int":
            before = str(df[col].dtype)
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            reports[col] = {"status": "success", "before_dtype": before, "after_dtype": str(df[col].dtype)}
        elif typ == "float":
            before = str(df[col].dtype)
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")
            reports[col] = {"status": "success", "before_dtype": before, "after_dtype": str(df[col].dtype)}
        else:
            reports[col] = {"status": "skipped", "reason": f"unsupported type {typ}"}

    return reports
