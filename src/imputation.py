from __future__ import annotations

from typing import Dict, Any, Iterable
from pathlib import Path
from datetime import datetime
import json

import pandas as pd


def analyze_missing_before(df: pd.DataFrame) -> Dict[str, Any]:
    n = len(df)
    summary = {}
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = round((null_count / n) * 100, 2) if n else 0.0
        summary[col] = {"null_count": null_count, "null_pct": null_pct}
    return {"rows": n, "columns": len(df.columns), "per_column": summary}


def apply_imputation(df: pd.DataFrame, spec: Dict[str, Dict[str, Any]], output_path: Path | str | None = None) -> Dict[str, Any]:
    """Apply imputation strategies described in `spec`.

    spec example:
      {
        'amount': {'strategy': 'median', 'reason': 'median preserves distribution'},
        'segment': {'strategy': 'mode', 'reason': 'most common segment'},
        'price': {'strategy': 'ffill', 'reason': 'time-series forward fill'},
        'customer_id': {'strategy': 'drop', 'reason': 'identifier required to join'},
        'notes': {'strategy': 'fill_value', 'value': 'MISSING', 'reason': 'placeholder for analyst'}
      }

    Returns a report describing before/after null counts and decisions made.
    """
    df = df.copy()
    report: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "before": analyze_missing_before(df),
        "decisions": {},
    }

    # Apply drops first to avoid filling rows that will be removed
    for col, conf in spec.items():
        strat = conf.get("strategy")
        if strat == "drop":
            before_rows = len(df)
            df = df.dropna(subset=[col])
            dropped = before_rows - len(df)
            report["decisions"][col] = {"strategy": "drop", "dropped_rows": int(dropped), "reason": conf.get("reason")}

    # Now apply other strategies
    for col, conf in spec.items():
        strat = conf.get("strategy")
        if strat == "drop":
            continue
        if col not in df.columns:
            report["decisions"][col] = {"strategy": strat, "status": "skipped_missing_column", "reason": conf.get("reason")}
            continue

        if strat == "median":
            if pd.api.types.is_numeric_dtype(df[col]):
                fill = df[col].median()
                df[col] = df[col].fillna(fill)
                report["decisions"][col] = {"strategy": "median", "filled_with": float(fill), "reason": conf.get("reason")}
            else:
                report["decisions"][col] = {"strategy": "median", "status": "skipped_not_numeric", "reason": conf.get("reason")}

        elif strat == "mode":
            mode_series = df[col].mode(dropna=True)
            if not mode_series.empty:
                fill = mode_series.iloc[0]
                df[col] = df[col].fillna(fill)
                report["decisions"][col] = {"strategy": "mode", "filled_with": fill, "reason": conf.get("reason")}
            else:
                report["decisions"][col] = {"strategy": "mode", "status": "no_mode_found", "reason": conf.get("reason")}

        elif strat == "ffill":
            df[col] = df[col].ffill()
            report["decisions"][col] = {"strategy": "ffill", "reason": conf.get("reason")}

        elif strat == "fill_value":
            val = conf.get("value")
            df[col] = df[col].fillna(val)
            report["decisions"][col] = {"strategy": "fill_value", "filled_with": val, "reason": conf.get("reason")}

        elif strat == "none":
            report["decisions"][col] = {"strategy": "none", "reason": conf.get("reason")}

        else:
            report["decisions"][col] = {"strategy": strat, "status": "unsupported", "reason": conf.get("reason")}

    report["after"] = analyze_missing_before(df)
    report["delta"] = {
        col: {"before": report["before"]["per_column"].get(col, {}), "after": report["after"]["per_column"].get(col, {})}
        for col in set(list(report["before"]["per_column"].keys()) + list(report["after"]["per_column"].keys()))
    }

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

    return {"df": df, "report": report}


if __name__ == "__main__":
    print("imputation module ready")
