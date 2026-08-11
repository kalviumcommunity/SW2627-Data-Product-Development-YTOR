from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple, Any

import json
import pandas as pd


def ingest_csv(
    filepath: Path | str,
    delimiter: str = ",",
    encoding: str = "utf-8",
    dtype: dict | None = None,
    parse_dates: Iterable[str] | None = None,
    usecols: Iterable[str] | None = None,
) -> Tuple[pd.DataFrame, dict]:
    """Load a CSV with explicit parameters and return dataframe + metadata.

    Always specify `delimiter` and `encoding` explicitly so callers are
    clear about what was used. This function raises informative errors on
    Unicode problems so the operator can try alternatives.
    """
    path = Path(filepath)
    try:
        df = pd.read_csv(
            path,
            sep=delimiter,
            encoding=encoding,
            dtype=dtype,
            parse_dates=list(parse_dates) if parse_dates is not None else None,
            usecols=list(usecols) if usecols is not None else None,
        )
    except UnicodeDecodeError as exc:
        raise UnicodeError(
            f"Failed to decode {path} with encoding={encoding}. Try 'latin-1' or 'cp1252'. Original: {exc}"
        )

    meta = {"rows": len(df), "columns": len(df.columns), "encoding": encoding}
    return df, meta


def ingest_csv_with_fallback(
    filepath: Path | str,
    delimiter: str = ",",
    encodings: Iterable[str] | None = None,
    **kwargs: Any,
) -> Tuple[pd.DataFrame, dict]:
    """Attempt multiple encodings until the CSV loads successfully.

    Returns dataframe and metadata including `encoding_used`.
    """
    path = Path(filepath)
    tried = []
    encodings = list(encodings or ["utf-8", "latin-1", "iso-8859-1", "cp1252"])
    for enc in encodings:
        try:
            df, meta = ingest_csv(path, delimiter=delimiter, encoding=enc, **kwargs)
            meta["encoding_used"] = enc
            return df, meta
        except (UnicodeDecodeError, UnicodeError):
            tried.append(enc)
            continue

    raise ValueError(f"Could not read CSV {path} with tried encodings: {tried}")


def ingest_json(filepath: Path | str, is_nested: bool = False) -> Tuple[pd.DataFrame, dict]:
    """Load JSON. If `is_nested` is True, flatten nested structures using json_normalize.

    The function accepts both JSON-lines and standard JSON arrays.
    """
    path = Path(filepath)
    # Try pandas fast path first
    try:
        df = pd.read_json(path)
    except ValueError:
        # Try loading via json module (handles newlines / mixed structures)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            payload = json.load(f)
        df = pd.json_normalize(payload) if is_nested else pd.DataFrame(payload)

    if is_nested:
        try:
            df = pd.json_normalize(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            # If normalization fails, leave df as-is
            pass

    meta = {"rows": len(df), "columns": len(df.columns), "format": "json", "nested_flattened": bool(is_nested)}
    return df, meta


def ingest_excel(filepath: Path | str, sheet_name: str | int = 0, engine: str | None = None) -> Tuple[pd.DataFrame, dict]:
    """Load an Excel sheet explicitly by `sheet_name` (name or zero-based index).

    Keep engine explicit when callers want to control reader backend.
    """
    path = Path(filepath)
    df = pd.read_excel(path, sheet_name=sheet_name, engine=engine)
    meta = {"rows": len(df), "columns": len(df.columns), "sheet_name": sheet_name}
    return df, meta


def document_ingestion(df: pd.DataFrame, source: str | Path | None = None, sample_rows: int = 3) -> dict:
    """Return a structured ingestion report (also prints a brief summary).

    The returned dict is easy to persist as JSON for audit trails.
    """
    report = {
        "source": str(source) if source is not None else None,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "sample": df.head(sample_rows).to_dict(orient="records"),
    }
    print("INGESTION REPORT:", report["source"])
    print(f"Rows: {report['rows']}, Columns: {report['columns']}")
    print(report["dtypes"]) 
    print("Sample:")
    print(df.head(sample_rows))
    return report
