from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from src.db import query_to_df, get_connection, DEFAULT_DB_PATH
from src.trust_model import compute_seller_trust_score

def get_seller_summary_metrics(db_path: str = DEFAULT_DB_PATH, days_window: int = 90) -> pd.DataFrame:
    """
    Retrieves and aggregates seller operational metrics over a given sliding window,
    then calculates trust scores and risk tiers using Pandas & NumPy.
    """
    # Find dataset max date to anchor sliding window
    ref_df = query_to_df("SELECT MAX(date(order_purchase_timestamp)) as max_d FROM orders_enriched", db_path=db_path)
    ref_date = ref_df["max_d"].iloc[0] if not ref_df.empty and ref_df["max_d"].iloc[0] else None

    where_clause = ""
    if days_window and days_window > 0 and ref_date:
        where_clause = f"WHERE date(order_purchase_timestamp) >= date('{ref_date}', '-{days_window} days')"

    orders_df = query_to_df(
        f"""
        SELECT 
            order_id, 
            seller_id, 
            COALESCE(seller_city, 'Marketplace') as seller_city,
            COALESCE(seller_state, 'BR') as seller_state,
            COALESCE(product_category_name_english, 'General') as category,
            order_purchase_timestamp as order_date,
            CASE 
                WHEN delivery_delay_days > 0 THEN 'Delayed' 
                WHEN order_status = 'canceled' THEN 'Cancelled_By_Seller' 
                ELSE 'Delivered' 
            END as shipping_status
        FROM orders_enriched
        {where_clause}
        """, db_path=db_path
    )

    if orders_df.empty:
        orders_df = query_to_df(
            """
            SELECT 
                order_id, seller_id, 
                COALESCE(seller_city, 'Marketplace') as seller_city,
                COALESCE(seller_state, 'BR') as seller_state,
                COALESCE(product_category_name_english, 'General') as category,
                order_purchase_timestamp as order_date,
                CASE WHEN delivery_delay_days > 0 THEN 'Delayed' WHEN order_status = 'canceled' THEN 'Cancelled_By_Seller' ELSE 'Delivered' END as shipping_status
            FROM orders_enriched
            WHERE seller_id IS NOT NULL
            """, db_path=db_path
        )
    
    if orders_df.empty:
        return pd.DataFrame(columns=[
            "seller_id", "seller_name", "seller_city", "seller_state", "category", "total_orders", "late_orders",
            "cancelled_orders", "misleading_returns", "total_returns", "avg_support_days",
            "total_reviews", "negative_reviews", "avg_sentiment", "fake_reviews",
            "trust_score", "risk_tier", "misleading_return_pct", "late_dispatch_pct",
            "cancellation_pct", "neg_sentiment_pct", "penalty_misleading",
            "penalty_late", "penalty_cancel", "penalty_sentiment", "penalty_support"
        ])

    orders_df["seller_name"] = "Seller #" + orders_df["seller_id"].astype(str).str[:8].str.upper() + " (" + orders_df["seller_city"].astype(str).str.title() + ")"

    where_ret = f"WHERE date(return_date) >= date('{ref_date}', '-{days_window} days')" if days_window and days_window > 0 and ref_date else ""
    returns_df = query_to_df(
        f"""
        SELECT return_id, order_id, seller_id, return_reason, support_resolution_time_days
        FROM returns
        {where_ret}
        """, db_path=db_path
    )
    
    where_rev = f"WHERE date(r.review_creation_date) >= date('{ref_date}', '-{days_window} days')" if days_window and days_window > 0 and ref_date else ""
    reviews_df = query_to_df(
        f"""
        SELECT 
            r.review_id, r.order_id, oe.seller_id, 
            r.review_score as rating, 
            (r.review_score - 3) / 2.0 as sentiment_score,
            CASE WHEN r.review_score >= 4 THEN 'Positive' WHEN r.review_score <= 2 THEN 'Negative' ELSE 'Neutral' END as sentiment_label,
            0 as trust_flag_fake_review
        FROM reviews r
        JOIN orders_enriched oe ON r.order_id = oe.order_id
        {where_rev}
        """, db_path=db_path
    )
    
    # Group orders by seller
    order_counts = orders_df.groupby(["seller_id", "seller_name", "seller_city", "seller_state", "category"]).agg(
        total_orders=("order_id", "count"),
        late_orders=("shipping_status", lambda x: (x == "Delayed").sum()),
        cancelled_orders=("shipping_status", lambda x: (x == "Cancelled_By_Seller").sum()),
    ).reset_index()
    
    # Filter misleading / defective returns
    misleading_reasons = ["Misleading Description", "Defective Product", "Wrong Item Sent"]
    returns_df["is_misleading"] = returns_df["return_reason"].isin(misleading_reasons)
    
    return_agg = returns_df.groupby("seller_id").agg(
        misleading_returns=("is_misleading", "sum"),
        total_returns=("return_id", "count"),
        avg_support_days=("support_resolution_time_days", "mean")
    ).reset_index() if not returns_df.empty else pd.DataFrame(columns=["seller_id", "misleading_returns", "total_returns", "avg_support_days"])
    
    # Aggregate reviews
    reviews_df["is_negative"] = reviews_df["sentiment_label"] == "Negative"
    review_agg = reviews_df.groupby("seller_id").agg(
        total_reviews=("review_id", "count"),
        negative_reviews=("is_negative", "sum"),
        avg_sentiment=("sentiment_score", "mean"),
        fake_reviews=("trust_flag_fake_review", "sum")
    ).reset_index() if not reviews_df.empty else pd.DataFrame(columns=["seller_id", "total_reviews", "negative_reviews", "avg_sentiment", "fake_reviews"])
    
    # Merge aggregations
    merged = pd.merge(order_counts, return_agg, on="seller_id", how="left").fillna(0)
    merged = pd.merge(merged, review_agg, on="seller_id", how="left").fillna(0)
    
    # Apply Trust Index Calculation
    trust_scores = []
    risk_tiers = []
    misleading_rates = []
    late_rates = []
    cancel_rates = []
    neg_sent_rates = []
    p_misleading = []
    p_late = []
    p_cancel = []
    p_sentiment = []
    p_support = []

    for _, row in merged.iterrows():
        res = compute_seller_trust_score(
            total_orders=int(row["total_orders"]),
            misleading_returns=int(row["misleading_returns"]),
            late_orders=int(row["late_orders"]),
            cancelled_orders=int(row["cancelled_orders"]),
            total_reviews=int(row["total_reviews"]),
            negative_reviews=int(row["negative_reviews"]),
            avg_support_days=float(row["avg_support_days"]),
            fake_review_flags=int(row["fake_reviews"])
        )
        trust_scores.append(res["trust_score"])
        risk_tiers.append(res["risk_tier"])
        misleading_rates.append(res["misleading_return_rate"])
        late_rates.append(res["late_dispatch_rate"])
        cancel_rates.append(res["cancellation_rate"])
        neg_sent_rates.append(res["neg_sentiment_rate"])
        
        pen = res["penalties"]
        p_misleading.append(pen["misleading"])
        p_late.append(pen["late"])
        p_cancel.append(pen["cancellation"])
        p_sentiment.append(pen["sentiment"])
        p_support.append(pen["support"])

    merged["trust_score"] = trust_scores
    merged["risk_tier"] = risk_tiers
    merged["misleading_return_pct"] = misleading_rates
    merged["late_dispatch_pct"] = late_rates
    merged["cancellation_pct"] = cancel_rates
    merged["neg_sentiment_pct"] = neg_sent_rates
    
    merged["penalty_misleading"] = p_misleading
    merged["penalty_late"] = p_late
    merged["penalty_cancel"] = p_cancel
    merged["penalty_sentiment"] = p_sentiment
    merged["penalty_support"] = p_support
    
    # Sort by lowest trust score first (most at-risk)
    merged = merged.sort_values(by="trust_score", ascending=True).reset_index(drop=True)
    return merged

def compute_historical_trust_trend(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Computes monthly seller trust scores over past dates to visualize trust decay trends.
    """
    query = """
    SELECT seller_id, strftime('%Y-%m', order_purchase_timestamp) as month,
           COUNT(order_id) as total_orders,
           SUM(CASE WHEN delivery_delay_days > 0 THEN 1 ELSE 0 END) as late_orders,
           SUM(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) as cancelled_orders
    FROM orders_enriched
    WHERE seller_id IS NOT NULL
    GROUP BY seller_id, month
    ORDER BY month ASC
    """
    df_orders = query_to_df(query, db_path=db_path)
    
    query_ret = """
    SELECT seller_id, strftime('%Y-%m', return_date) as month,
           SUM(CASE WHEN return_reason IN ('Misleading Description', 'Defective Product') THEN 1 ELSE 0 END) as misleading_returns,
           AVG(support_resolution_time_days) as avg_support_days
    FROM returns
    GROUP BY seller_id, month
    """
    df_returns = query_to_df(query_ret, db_path=db_path)
    
    query_rev = """
    SELECT oe.seller_id, strftime('%Y-%m', r.review_creation_date) as month,
           COUNT(r.review_id) as total_reviews,
           SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) as negative_reviews,
           AVG((r.review_score - 3) / 2.0) as avg_sentiment
    FROM reviews r
    JOIN orders_enriched oe ON r.order_id = oe.order_id
    GROUP BY oe.seller_id, month
    """
    df_reviews = query_to_df(query_rev, db_path=db_path)
    
    merged = pd.merge(df_orders, df_returns, on=["seller_id", "month"], how="left").fillna(0)
    merged = pd.merge(merged, df_reviews, on=["seller_id", "month"], how="left").fillna(0)
    
    scores = []
    tiers = []
    for _, r in merged.iterrows():
        res = compute_seller_trust_score(
            total_orders=int(r["total_orders"]),
            misleading_returns=int(r["misleading_returns"]),
            late_orders=int(r["late_orders"]),
            cancelled_orders=int(r["cancelled_orders"]),
            total_reviews=int(r["total_reviews"]),
            negative_reviews=int(r["negative_reviews"]),
            avg_support_days=float(r["avg_support_days"])
        )
        scores.append(res["trust_score"])
        tiers.append(res["risk_tier"])
        
    merged["trust_score"] = scores
    merged["risk_tier"] = tiers
    return merged

def get_behavior_correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Computes correlation matrix between operational behaviors and trust score reduction."""
    cols = ["trust_score", "misleading_return_pct", "late_dispatch_pct", "cancellation_pct", "neg_sentiment_pct", "avg_support_days"]
    existing_cols = [c for c in cols if c in df.columns]
    if len(existing_cols) < 2:
        return pd.DataFrame()
    return df[existing_cols].corr()

def get_marketplace_kpis(db_path: str = DEFAULT_DB_PATH, days_window: int = 90) -> Dict[str, Any]:
    """Calculates the 6 core operational KPIs for the marketplace dashboard overview."""
    df_sellers = query_to_df("SELECT COUNT(DISTINCT seller_id) as count FROM sellers", db_path=db_path)
    total_sellers = int(df_sellers["count"].iloc[0]) if not df_sellers.empty else 0
    
    summary_df = get_seller_summary_metrics(db_path=db_path, days_window=days_window)
    if summary_df.empty:
        return {
            "total_sellers": total_sellers,
            "active_sellers": 0,
            "sellers_trust_score": 0.0,
            "return_rate": 0.0,
            "avg_customer_rating": 0.0,
            "delivery_success_rate": 0.0
        }
        
    active_sellers = int((summary_df["total_orders"] > 0).sum())
    sellers_trust_score = round(float(summary_df["trust_score"].mean()), 1)
    
    # Calculate marketplace return rate
    df_ret = query_to_df("SELECT COUNT(*) as total_ret FROM returns", db_path=db_path)
    df_ord = query_to_df("SELECT COUNT(*) as total_ord FROM orders", db_path=db_path)
    if not df_ret.empty and not df_ord.empty and df_ord["total_ord"].iloc[0] > 0:
        return_rate = round(float(df_ret["total_ret"].iloc[0] / df_ord["total_ord"].iloc[0] * 100), 1)
    else:
        return_rate = 0.0
        
    # Calculate average rating
    df_rev = query_to_df("SELECT AVG(review_score) as avg_rating FROM reviews WHERE review_score IS NOT NULL", db_path=db_path)
    avg_customer_rating = round(float(df_rev["avg_rating"].iloc[0]), 2) if not df_rev.empty and df_rev["avg_rating"].iloc[0] else 4.2
    
    # Calculate delivery success rate
    df_deliv = query_to_df("""
        SELECT 
            COUNT(order_id) as total_orders,
            SUM(CASE WHEN is_delivered = 1 OR order_status = 'delivered' THEN 1 ELSE 0 END) as successful_orders
        FROM orders
    """, db_path=db_path)
    if not df_deliv.empty and df_deliv["total_orders"].iloc[0] > 0:
        delivery_success_rate = round(float(df_deliv["successful_orders"].iloc[0] / df_deliv["total_orders"].iloc[0] * 100), 1)
    else:
        delivery_success_rate = 0.0
        
    return {
        "total_sellers": total_sellers,
        "active_sellers": active_sellers,
        "sellers_trust_score": sellers_trust_score,
        "return_rate": return_rate,
        "avg_customer_rating": avg_customer_rating,
        "delivery_success_rate": delivery_success_rate
    }


