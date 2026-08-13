-- YTOR Database Schema for Cleaned Olist Datasets

-- 1. Category Translation
CREATE TABLE IF NOT EXISTS category_translation (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

-- 2. Customers
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    zip_code_prefix INTEGER,
    city TEXT,
    state TEXT
);

-- 3. Geolocation
CREATE TABLE IF NOT EXISTS geolocation (
    geolocation_zip_code_prefix INTEGER,
    geolocation_lat REAL,
    geolocation_lng REAL,
    geolocation_city TEXT,
    geolocation_state TEXT
);

-- 4. Order Items
CREATE TABLE IF NOT EXISTS order_items (
    order_id TEXT,
    order_item_id INTEGER,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TEXT,
    price REAL,
    freight_value REAL
);

-- 5. Order Payments
CREATE TABLE IF NOT EXISTS order_payments (
    order_id TEXT,
    payment_sequential INTEGER,
    payment_type TEXT,
    payment_installments INTEGER,
    payment_value REAL
);

-- 6. Orders
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TEXT,
    order_approved_at TEXT,
    order_delivered_carrier_date TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT,
    is_delivered INTEGER,
    delivery_delay_days REAL
);

-- 7. Orders Enriched
CREATE TABLE IF NOT EXISTS orders_enriched (
    order_id TEXT,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TEXT,
    order_approved_at TEXT,
    order_delivered_carrier_date TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT,
    is_delivered INTEGER,
    delivery_delay_days REAL,
    customer_unique_id TEXT,
    city TEXT,
    state TEXT,
    order_item_id INTEGER,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TEXT,
    price REAL,
    freight_value REAL,
    payment_sequential INTEGER,
    payment_type TEXT,
    payment_installments INTEGER,
    payment_value REAL,
    product_category_name TEXT,
    product_category_name_english TEXT,
    product_weight_g REAL,
    seller_city TEXT,
    seller_state TEXT,
    review_score INTEGER,
    review_comment_title TEXT,
    review_comment_message TEXT
);

-- 8. Products
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_name_lenght REAL,
    product_description_lenght REAL,
    product_photos_qty REAL,
    product_weight_g REAL,
    product_length_cm REAL,
    product_height_cm REAL,
    product_width_cm REAL,
    product_category_name_english TEXT
);

-- 9. Reviews
CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT,
    order_id TEXT,
    review_score INTEGER,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TEXT,
    review_answer_timestamp TEXT
);

-- 10. Sellers
CREATE TABLE IF NOT EXISTS sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix INTEGER,
    seller_city TEXT,
    seller_state TEXT
);

-- 11. Seller Trust Snapshots
CREATE TABLE IF NOT EXISTS seller_trust_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    trust_score REAL NOT NULL,
    risk_tier TEXT NOT NULL,
    misleading_return_rate REAL NOT NULL,
    late_dispatch_rate REAL NOT NULL,
    cancellation_rate REAL NOT NULL,
    sentiment_moving_avg REAL NOT NULL
);

-- Returns view based on cleaned order items & status
CREATE VIEW IF NOT EXISTS returns AS
SELECT 
    ('RET-' || oe.order_id || '-' || COALESCE(oe.order_item_id, 1)) AS return_id,
    oe.order_id,
    oe.seller_id,
    COALESCE(oe.order_delivered_customer_date, oe.order_purchase_timestamp) AS return_date,
    CASE 
        WHEN oe.order_status = 'canceled' THEN 'Misleading Description'
        WHEN oe.delivery_delay_days > 0 THEN 'Late Delivery'
        WHEN oe.review_score <= 2 THEN 'Defective Product'
        ELSE 'Customer Return'
    END AS return_reason,
    'Refunded' AS resolution,
    CAST(COALESCE(MAX(oe.delivery_delay_days, 0), 0) AS INTEGER) AS support_resolution_time_days
FROM orders_enriched oe
WHERE (oe.order_status = 'canceled' OR oe.delivery_delay_days > 0 OR oe.review_score <= 2)
  AND oe.seller_id IS NOT NULL;

-- Create Indexes for performance
CREATE INDEX IF NOT EXISTS idx_customers_unique ON customers(customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_seller ON order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_order_payments_order ON order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts ON orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_orders_enriched_seller ON orders_enriched(seller_id);
CREATE INDEX IF NOT EXISTS idx_orders_enriched_purchase ON orders_enriched(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_reviews_order ON reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_creation ON reviews(review_creation_date);

