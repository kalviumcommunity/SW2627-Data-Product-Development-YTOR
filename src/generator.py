import random
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from src.db import get_connection, init_db, DEFAULT_DB_PATH

CATEGORIES = ["Electronics", "Fashion", "Home & Kitchen", "Beauty & Care", "Sports & Outdoors", "Automotive"]

SELLER_PERSONAS = [
    {"name": "Pristine Merchant", "type": "TOP_SELLER", "count": 15},
    {"name": "Spec Deceiver", "type": "MISLEADING_SPECS", "count": 8},
    {"name": "Lagging Logistics", "type": "CHRONIC_LATE", "count": 8},
    {"name": "Stockout Refractory", "type": "HIGH_CANCELLATIONS", "count": 6},
    {"name": "Review Gamer", "type": "REVIEW_MANIPULATOR", "count": 4},
    {"name": "Standard Shop", "type": "AVERAGE", "count": 12},
]

RETURN_REASONS = [
    "Misleading Description",
    "Defective Product",
    "Late Delivery",
    "Wrong Item Sent",
    "Buyer Remorse",
]

REVIEW_TEMPLATES = {
    "Positive": [
        "Excellent product! Arrived on time and exactly as described.",
        "Very happy with this purchase. High quality and quick shipping.",
        "Superb seller, highly recommended!",
        "Item works perfectly, robust packaging.",
    ],
    "Neutral": [
        "Decent product for the price. Shipping took a little longer than expected.",
        "Okay product, matches description but quality is average.",
        "Item works fine, packaging was a bit damaged.",
    ],
    "Negative": [
        "Completely misleading description! Looks cheap and broke on day 1.",
        "Delivered 10 days late! Seller never responded to my messages.",
        "Order was cancelled without notice after waiting a week!",
        "Item sent was totally different from what was shown in the listing photos.",
        "Defective item, seller refused to process refund without dispute.",
    ],
}

def generate_dataset(db_path: str = DEFAULT_DB_PATH, num_days: int = 180, seed: int = 42) -> None:
    """Generates synthetic dataset simulating marketplace dynamics over time."""
    random.seed(seed)
    np.random.seed(seed)
    
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Clear existing data
    for table in ["seller_trust_snapshots", "reviews", "returns", "orders", "products", "sellers"]:
        cursor.execute(f"DELETE FROM {table}")
        
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_days)
    
    sellers_data = []
    products_data = []
    
    seller_counter = 1
    product_counter = 1
    
    seller_configs = []
    
    for group in SELLER_PERSONAS:
        p_type = group["type"]
        for i in range(group["count"]):
            seller_id = f"SEL-{seller_counter:03d}"
            s_name = f"{group['name']} #{i+1}"
            cat = random.choice(CATEGORIES)
            j_date = (start_date - timedelta(days=random.randint(100, 500))).strftime("%Y-%m-%d")
            f_type = "Fulfillment_By_Amazon" if random.random() > 0.6 else "Merchant_Fulfilled"
            
            sellers_data.append((seller_id, s_name, cat, j_date, f_type))
            seller_configs.append({"seller_id": seller_id, "name": s_name, "category": cat, "type": p_type})
            
            # Generate 3-6 products per seller
            for p in range(random.randint(3, 6)):
                p_id = f"PROD-{product_counter:04d}"
                p_name = f"{cat} Item {product_counter}"
                price = round(random.uniform(15.0, 250.0), 2)
                products_data.append((p_id, seller_id, p_name, cat, price))
                product_counter += 1
                
            seller_counter += 1
            
    cursor.executemany("INSERT INTO sellers VALUES (?, ?, ?, ?, ?)", sellers_data)
    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products_data)
    conn.commit()
    
    # Map products by seller
    products_df = pd.read_sql_query("SELECT product_id, seller_id FROM products", conn)
    seller_products = products_df.groupby("seller_id")["product_id"].apply(list).to_dict()
    
    orders_data = []
    returns_data = []
    reviews_data = []
    
    order_counter = 1
    return_counter = 1
    review_counter = 1
    
    # Generate daily order flow over num_days
    for day_offset in range(num_days):
        current_dt = start_date + timedelta(days=day_offset)
        dt_str = current_dt.strftime("%Y-%m-%d")
        
        for config in seller_configs:
            sid = config["seller_id"]
            stype = config["type"]
            p_ids = seller_products.get(sid, [])
            if not p_ids:
                continue
                
            # Base daily order count
            num_orders = random.randint(3, 10)
            
            for _ in range(num_orders):
                oid = f"ORD-{order_counter:06d}"
                pid = random.choice(p_ids)
                cid = f"CUST-{random.randint(1000, 9999)}"
                
                prom_deliv = current_dt + timedelta(days=random.randint(3, 5))
                
                # Determine outcome based on persona
                shipping_status = "Delivered"
                cancellation_reason = None
                is_late = False
                is_returned = False
                
                if stype == "TOP_SELLER":
                    is_late = random.random() < 0.02
                    is_returned = random.random() < 0.03
                elif stype == "MISLEADING_SPECS":
                    is_late = random.random() < 0.05
                    # Higher returns over time as bad products get sold
                    is_returned = random.random() < (0.18 + (day_offset / num_days) * 0.12)
                elif stype == "CHRONIC_LATE":
                    is_late = random.random() < 0.35
                    is_returned = random.random() < 0.12
                elif stype == "HIGH_CANCELLATIONS":
                    if random.random() < 0.22:
                        shipping_status = "Cancelled_By_Seller"
                        cancellation_reason = "Out_of_Stock"
                    else:
                        is_late = random.random() < 0.08
                        is_returned = random.random() < 0.05
                elif stype == "REVIEW_MANIPULATOR":
                    is_late = random.random() < 0.08
                    is_returned = random.random() < 0.15
                else: # AVERAGE
                    is_late = random.random() < 0.07
                    is_returned = random.random() < 0.06
                    
                if shipping_status != "Cancelled_By_Seller":
                    delay_days = random.randint(3, 8) if is_late else random.randint(0, 1)
                    actual_deliv = prom_deliv + timedelta(days=delay_days)
                    if is_late:
                        shipping_status = "Delayed"
                    act_deliv_str = actual_deliv.strftime("%Y-%m-%d")
                else:
                    act_deliv_str = None
                    
                orders_data.append((
                    oid, sid, pid, cid, dt_str,
                    prom_deliv.strftime("%Y-%m-%d"),
                    act_deliv_str, shipping_status, cancellation_reason
                ))
                
                # Process Returns
                if is_returned and shipping_status != "Cancelled_By_Seller":
                    rid = f"RET-{return_counter:06d}"
                    ret_dt = (current_dt + timedelta(days=random.randint(4, 12))).strftime("%Y-%m-%d")
                    
                    if stype == "MISLEADING_SPECS":
                        reason = random.choice(["Misleading Description", "Defective Product", "Misleading Description"])
                    elif is_late:
                        reason = "Late Delivery"
                    else:
                        reason = random.choice(RETURN_REASONS)
                        
                    res = "Refunded" if random.random() > 0.15 else "Disputed"
                    resolution_days = random.randint(5, 14) if stype in ["MISLEADING_SPECS", "CHRONIC_LATE"] else random.randint(1, 3)
                    
                    returns_data.append((rid, oid, sid, ret_dt, reason, res, resolution_days))
                    return_counter += 1
                    
                # Process Reviews (approx 40% of orders generate a review)
                if random.random() < 0.40:
                    revid = f"REV-{review_counter:06d}"
                    rev_dt = (current_dt + timedelta(days=random.randint(5, 15))).strftime("%Y-%m-%d")
                    
                    fake_flag = 0
                    if stype == "TOP_SELLER":
                        rating = random.choices([5, 4, 3], weights=[0.8, 0.15, 0.05])[0]
                    elif stype == "MISLEADING_SPECS":
                        # Declining ratings over time
                        rating = random.choices([1, 2, 3, 5], weights=[0.5, 0.3, 0.1, 0.1])[0]
                    elif stype == "CHRONIC_LATE":
                        rating = random.choices([1, 2, 3, 4], weights=[0.4, 0.3, 0.2, 0.1])[0]
                    elif stype == "HIGH_CANCELLATIONS":
                        rating = 1 if shipping_status == "Cancelled_By_Seller" else random.choices([1, 2, 4, 5], weights=[0.3, 0.3, 0.2, 0.2])[0]
                    elif stype == "REVIEW_MANIPULATOR":
                        # Mixed fake 5-stars with organic 1-stars
                        if random.random() < 0.5:
                            rating = 5
                            fake_flag = 1
                        else:
                            rating = 1
                    else:
                        rating = random.choices([5, 4, 3, 2, 1], weights=[0.5, 0.25, 0.15, 0.05, 0.05])[0]
                        
                    if rating >= 4:
                        s_label = "Positive"
                        s_score = round(random.uniform(0.5, 0.95), 2)
                    elif rating == 3:
                        s_label = "Neutral"
                        s_score = round(random.uniform(-0.1, 0.2), 2)
                    else:
                        s_label = "Negative"
                        s_score = round(random.uniform(-0.95, -0.4), 2)
                        
                    r_text = random.choice(REVIEW_TEMPLATES[s_label])
                    reviews_data.append((revid, oid, sid, pid, rev_dt, rating, r_text, s_score, s_label, fake_flag))
                    review_counter += 1
                    
                order_counter += 1
                
    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", orders_data)
    cursor.executemany("INSERT INTO returns VALUES (?, ?, ?, ?, ?, ?, ?)", returns_data)
    cursor.executemany("INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", reviews_data)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    generate_dataset()
    print("Marketplace dataset successfully generated!")
