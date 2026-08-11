from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "raw data"
OUTPUT_DIR = ROOT_DIR / "data" / "cleaned"


def _clean_text(series: pd.Series, fill_value: str = "Unknown") -> pd.Series:
    cleaned = series.astype("string").str.strip()
    cleaned = cleaned.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaN": pd.NA})
    return cleaned.fillna(fill_value).astype(str)


def _clean_numeric(series: pd.Series, fill_value: float | None = None) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if fill_value is None:
        numeric = numeric.fillna(numeric.median())
    else:
        numeric = numeric.fillna(fill_value)
    return numeric.astype(float)


def _parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def clean_datasets(raw_data_dir: Path | str = RAW_DATA_DIR, output_dir: Path | str = OUTPUT_DIR) -> Dict[str, pd.DataFrame]:
    """Load and clean the raw Olist-style CSV files from the raw data folder."""
    raw_data_dir = Path(raw_data_dir)
    output_dir = Path(output_dir)
    _ensure_output_dir(output_dir)

    customers = pd.read_csv(raw_data_dir / "olist_customers_dataset.csv")
    geolocation = pd.read_csv(raw_data_dir / "olist_geolocation_dataset.csv")
    order_items = pd.read_csv(raw_data_dir / "olist_order_items_dataset.csv")
    order_payments = pd.read_csv(raw_data_dir / "olist_order_payments_dataset.csv")
    reviews = pd.read_csv(raw_data_dir / "olist_order_reviews_dataset.csv")
    orders = pd.read_csv(raw_data_dir / "olist_orders_dataset.csv")
    products = pd.read_csv(raw_data_dir / "olist_products_dataset.csv")
    sellers = pd.read_csv(raw_data_dir / "olist_sellers_dataset.csv")
    category_translation = pd.read_csv(raw_data_dir / "product_category_name_translation.csv")

    # Customer and seller geography
    customers["customer_id"] = customers["customer_id"].astype(str).str.strip()
    customers["customer_unique_id"] = customers["customer_unique_id"].astype(str).str.strip()
    customers = customers.rename(columns={
        "customer_city": "city",
        "customer_state": "state",
        "customer_zip_code_prefix": "zip_code_prefix",
    })
    customers["city"] = _clean_text(customers["city"], fill_value="Unknown")
    customers["state"] = _clean_text(customers["state"], fill_value="Unknown")
    customers["zip_code_prefix"] = _clean_numeric(customers["zip_code_prefix"], fill_value=0).astype(int)

    geolocation = geolocation.copy()
    geolocation["geolocation_city"] = _clean_text(geolocation["geolocation_city"], fill_value="Unknown")
    geolocation["geolocation_state"] = _clean_text(geolocation["geolocation_state"], fill_value="Unknown")
    geolocation["geolocation_zip_code_prefix"] = _clean_numeric(geolocation["geolocation_zip_code_prefix"], fill_value=0).astype(int)

    # Order items and payments
    order_items["order_id"] = order_items["order_id"].astype(str).str.strip()
    order_items["product_id"] = order_items["product_id"].astype(str).str.strip()
    order_items["seller_id"] = order_items["seller_id"].astype(str).str.strip()
    order_items["shipping_limit_date"] = _parse_dates(order_items["shipping_limit_date"])
    order_items["price"] = _clean_numeric(order_items["price"], fill_value=0)
    order_items["freight_value"] = _clean_numeric(order_items["freight_value"], fill_value=0)

    order_payments["order_id"] = order_payments["order_id"].astype(str).str.strip()
    order_payments["payment_type"] = _clean_text(order_payments["payment_type"], fill_value="Unknown")
    order_payments["payment_installments"] = _clean_numeric(order_payments["payment_installments"], fill_value=0).astype(int)
    order_payments["payment_value"] = _clean_numeric(order_payments["payment_value"], fill_value=0)

    # Reviews
    reviews["review_id"] = reviews["review_id"].astype(str).str.strip()
    reviews["order_id"] = reviews["order_id"].astype(str).str.strip()
    reviews["review_creation_date"] = _parse_dates(reviews["review_creation_date"])
    reviews["review_answer_timestamp"] = _parse_dates(reviews["review_answer_timestamp"])
    reviews["review_comment_title"] = reviews["review_comment_title"].fillna("No title provided")
    reviews["review_comment_message"] = reviews["review_comment_message"].fillna("No comment provided")
    reviews["review_comment_title"] = _clean_text(reviews["review_comment_title"], fill_value="No title provided")
    reviews["review_comment_message"] = _clean_text(reviews["review_comment_message"], fill_value="No comment provided")
    reviews["review_score"] = _clean_numeric(reviews["review_score"], fill_value=0).astype(int)

    # Orders
    orders["order_id"] = orders["order_id"].astype(str).str.strip()
    orders["customer_id"] = orders["customer_id"].astype(str).str.strip()
    orders["order_status"] = _clean_text(orders["order_status"], fill_value="Unknown")
    for col in ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]:
        orders[col] = _parse_dates(orders[col])
    orders["is_delivered"] = orders["order_delivered_customer_date"].notna()
    orders["delivery_delay_days"] = (orders["order_delivered_customer_date"] - orders["order_estimated_delivery_date"]).dt.days

    # Products and translation
    products["product_id"] = products["product_id"].astype(str).str.strip()
    products["product_category_name"] = _clean_text(products["product_category_name"], fill_value="Unknown")
    products["product_name_lenght"] = _clean_numeric(products["product_name_lenght"], fill_value=0)
    products["product_description_lenght"] = _clean_numeric(products["product_description_lenght"], fill_value=0)
    products["product_photos_qty"] = _clean_numeric(products["product_photos_qty"], fill_value=0)
    products["product_weight_g"] = _clean_numeric(products["product_weight_g"], fill_value=0)
    products["product_length_cm"] = _clean_numeric(products["product_length_cm"], fill_value=0)
    products["product_height_cm"] = _clean_numeric(products["product_height_cm"], fill_value=0)
    products["product_width_cm"] = _clean_numeric(products["product_width_cm"], fill_value=0)

    category_translation["product_category_name"] = _clean_text(category_translation["product_category_name"], fill_value="Unknown")
    category_translation["product_category_name_english"] = _clean_text(category_translation["product_category_name_english"], fill_value="Unknown")
    products = products.merge(category_translation, on="product_category_name", how="left")
    products["product_category_name_english"] = products["product_category_name_english"].fillna("Untranslated")

    sellers["seller_id"] = sellers["seller_id"].astype(str).str.strip()
    sellers["seller_city"] = _clean_text(sellers["seller_city"], fill_value="Unknown")
    sellers["seller_state"] = _clean_text(sellers["seller_state"], fill_value="Unknown")
    sellers["seller_zip_code_prefix"] = _clean_numeric(sellers["seller_zip_code_prefix"], fill_value=0).astype(int)

    cleaned = {
        "customers": customers,
        "geolocation": geolocation,
        "order_items": order_items,
        "order_payments": order_payments,
        "reviews": reviews,
        "orders": orders,
        "products": products,
        "sellers": sellers,
        "category_translation": category_translation,
    }

    for name, frame in cleaned.items():
        frame.to_csv(output_dir / f"{name}_cleaned.csv", index=False)

    # Create an enriched order-level view to support downstream analysis.
    enriched_orders = orders.merge(customers[["customer_id", "customer_unique_id", "city", "state"]], on="customer_id", how="left")
    enriched_orders = enriched_orders.merge(order_items, on="order_id", how="left")
    enriched_orders = enriched_orders.merge(order_payments, on="order_id", how="left")
    enriched_orders = enriched_orders.merge(products[["product_id", "product_category_name", "product_category_name_english", "product_weight_g"]], on="product_id", how="left")
    enriched_orders = enriched_orders.merge(sellers[["seller_id", "seller_city", "seller_state"]], on="seller_id", how="left")
    enriched_orders = enriched_orders.merge(reviews[["order_id", "review_score", "review_comment_title", "review_comment_message"]].drop_duplicates(subset=["order_id"]), on="order_id", how="left")
    enriched_orders.to_csv(output_dir / "orders_enriched_cleaned.csv", index=False)

    return cleaned


if __name__ == "__main__":
    clean_datasets()
    print(f"Cleaned datasets saved to {OUTPUT_DIR}")
