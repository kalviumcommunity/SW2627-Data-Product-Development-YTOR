-- YTOR  Database Schema

CREATE TABLE IF NOT EXISTS sellers (
    seller_id TEXT PRIMARY KEY,
    seller_name TEXT NOT NULL,
    category TEXT NOT NULL,
    join_date TEXT NOT NULL,
    fulfillment_type TEXT NOT NULL DEFAULT 'Merchant'
);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    seller_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY(seller_id) REFERENCES sellers(seller_id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    seller_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    promised_delivery_date TEXT NOT NULL,
    actual_delivery_date TEXT,
    shipping_status TEXT NOT NULL,
    cancellation_reason TEXT,
    FOREIGN KEY(seller_id) REFERENCES sellers(seller_id),
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS returns (
    return_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    seller_id TEXT NOT NULL,
    return_date TEXT NOT NULL,
    return_reason TEXT NOT NULL,
    resolution TEXT NOT NULL,
    support_resolution_time_days INTEGER DEFAULT 0,
    FOREIGN KEY(order_id) REFERENCES orders(order_id),
    FOREIGN KEY(seller_id) REFERENCES sellers(seller_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    seller_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    review_date TEXT NOT NULL,
    rating INTEGER NOT NULL,
    review_text TEXT,
    sentiment_score REAL NOT NULL,
    sentiment_label TEXT NOT NULL,
    trust_flag_fake_review INTEGER DEFAULT 0,
    FOREIGN KEY(order_id) REFERENCES orders(order_id),
    FOREIGN KEY(seller_id) REFERENCES sellers(seller_id),
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS seller_trust_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    trust_score REAL NOT NULL,
    risk_tier TEXT NOT NULL,
    misleading_return_rate REAL NOT NULL,
    late_dispatch_rate REAL NOT NULL,
    cancellation_rate REAL NOT NULL,
    sentiment_moving_avg REAL NOT NULL,
    FOREIGN KEY(seller_id) REFERENCES sellers(seller_id)
);

-- Index creation for optimized querying
CREATE INDEX IF NOT EXISTS idx_orders_seller_date ON orders(seller_id, order_date);
CREATE INDEX IF NOT EXISTS idx_returns_seller ON returns(seller_id, return_reason);
CREATE INDEX IF NOT EXISTS idx_reviews_seller_date ON reviews(seller_id, review_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_seller_date ON seller_trust_snapshots(seller_id, snapshot_date);
