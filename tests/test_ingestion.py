import json
from pathlib import Path

import pandas as pd

from src.ingestion import (
    ingest_csv_with_fallback,
    ingest_json,
    ingest_excel,
    document_ingestion,
)


def test_ingest_csv_with_fallback_latn1(tmp_path):
    data = "id;name;value\n1;José;100\n2;Ana;200\n"
    fp = tmp_path / "latin1.csv"
    fp.write_bytes(data.encode("latin-1"))

    df, meta = ingest_csv_with_fallback(fp, delimiter=";")
    assert meta["encoding_used"] in {"latin-1", "iso-8859-1", "cp1252", "utf-8"}
    assert df.shape[0] == 2
    assert list(df.columns) == ["id", "name", "value"]


def test_ingest_json_nested(tmp_path):
    payload = [
        {"customer": {"id": 1, "name": "Alice"}, "order": {"amount": 10}},
        {"customer": {"id": 2, "name": "Bob"}, "order": {"amount": 20}},
    ]
    fp = tmp_path / "nested.json"
    fp.write_text(json.dumps(payload), encoding="utf-8")

    df, meta = ingest_json(fp, is_nested=True)
    # Expect flattened columns like 'customer.id' or 'customer.name' depending on normalization
    assert "customer.id" in df.columns or "customer.id" in df.columns
    assert meta["rows"] == 2


def test_ingest_excel_and_document(tmp_path):
    df0 = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    fp = tmp_path / "sheet.xlsx"
    df0.to_excel(fp, index=False, sheet_name="Sales")

    df, meta = ingest_excel(fp, sheet_name="Sales")
    report = document_ingestion(df, source=fp, sample_rows=1)

    assert meta["rows"] == 2
    assert report["rows"] == 2
    assert report["columns"] == 2
