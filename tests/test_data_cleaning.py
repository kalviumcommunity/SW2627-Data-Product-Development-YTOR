from pathlib import Path

from src.data_cleaning import ROOT_DIR, clean_datasets


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
