from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import json
import pandas as pd


def profile_nulls_and_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    n = len(df)
    nulls = {}
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = round((null_count / n) * 100, 2) if n else 0.0
        nulls[col] = {"null_count": null_count, "null_pct": null_pct}

    exact_duplicates = int(df.duplicated().sum())
    dup_pct = round((exact_duplicates / n) * 100, 2) if n else 0.0
    return {"per_column": nulls, "exact_duplicates": exact_duplicates, "duplicate_pct": dup_pct}


def profile_numerical(df: pd.DataFrame) -> Dict[str, Any]:
    stats = {}
    numeric = df.select_dtypes(include=["number"]).columns
    for col in numeric:
        series = df[col]
        stats[col] = {
            "count": int(series.count()),
            "missing": int(series.isnull().sum()),
            "min": None if series.dropna().empty else float(series.min()),
            "max": None if series.dropna().empty else float(series.max()),
            "mean": None if series.dropna().empty else float(round(series.mean(), 4)),
            "median": None if series.dropna().empty else float(series.median()),
            "std": None if series.dropna().empty else float(round(series.std(), 4)),
            "negative_count": int((series < 0).sum()) if not series.dropna().empty else 0,
        }
    return stats


def profile_categorical(df: pd.DataFrame, top_n: int = 5) -> Dict[str, Any]:
    cats = {}
    for col in df.select_dtypes(include=["object", "string", "category"]).columns:
        vc = df[col].value_counts(dropna=False)
        total = len(df)
        top = []
        for val, cnt in vc.head(top_n).items():
            pct = round((cnt / total) * 100, 2) if total else 0.0
            top.append({"value": None if pd.isna(val) else val, "count": int(cnt), "pct": pct})
        cats[col] = {"distinct": int(vc.size), "top": top}
    return cats


def identify_issues(df: pd.DataFrame, null_threshold: float = 30.0, dup_threshold: float = 5.0) -> Dict[str, Any]:
    issues = []
    n = len(df)
    null_profile = profile_nulls_and_duplicates(df)["per_column"]
    for col, metrics in null_profile.items():
        if metrics["null_pct"] >= null_threshold:
            issues.append({"column": col, "type": "High nulls", "value": f"{metrics['null_pct']}%"})

    dup_pct = profile_nulls_and_duplicates(df)["duplicate_pct"]
    if dup_pct >= dup_threshold:
        issues.append({"type": "High duplicates", "value": f"{dup_pct}%"})

    # numeric anomalies: negative values
    numeric = df.select_dtypes(include=["number"]).columns
    for col in numeric:
        neg = int((df[col] < 0).sum())
        if neg > 0:
            pct = round((neg / n) * 100, 2) if n else 0.0
            issues.append({"column": col, "type": "Negative values", "value": f"{neg} ({pct}%)"})

    return {"issues": issues}


def generate_profile_report(df: pd.DataFrame, name: str | None = None, output_path: Path | str | None = None, thresholds: Dict[str, float] | None = None) -> Dict[str, Any]:
    thresholds = thresholds or {"null_threshold": 30.0, "dup_threshold": 5.0}
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "name": name,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "nulls_and_duplicates": profile_nulls_and_duplicates(df),
        "numerical": profile_numerical(df),
        "categorical": profile_categorical(df),
        "issues": identify_issues(df, null_threshold=thresholds.get("null_threshold", 30.0), dup_threshold=thresholds.get("dup_threshold", 5.0)),
    }

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

    return report


if __name__ == "__main__":
    print("profiling module ready")
