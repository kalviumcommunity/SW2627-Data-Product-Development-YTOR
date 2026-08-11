from pathlib import Path

from src.data_cleaning import ROOT_DIR, clean_datasets
from src.intake_validation import generate_validation_report


def test_clean_datasets_creates_cleaned_csvs(tmp_path):
    output_dir = tmp_path / "cleaned"
    cleaned = clean_datasets(raw_data_dir=ROOT_DIR / "raw data", output_dir=output_dir)

    assert "customers" in cleaned
    assert (output_dir / "customers_cleaned.csv").exists()
    assert (output_dir / "orders_enriched_cleaned.csv").exists()

    customers = cleaned["customers"]
    assert "city" in customers.columns
    assert customers["city"].notna().all()
    assert customers.shape[0] > 0


def test_intake_validation_report_for_raw_customer_csv(tmp_path):
    filepath = ROOT_DIR / "raw data" / "olist_customers_dataset.csv"
    expected_columns = [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ]
    report_path = tmp_path / "validation_report.json"
    report = generate_validation_report(
        filepath,
        expected_columns,
        output_path=report_path,
        expected_encoding="utf-8",
        allowed_formats=["csv"],
    )

    assert report["status"] == "success"
    assert report["checks"]["file_exists"] == "File exists and has content"
    assert report["checks"]["format"] == "Format valid: csv"
    assert report_path.exists()
    assert report["statistics"]["rows"] > 0
