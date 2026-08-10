# SW2627-Data-Product-Development-YTOR


YTOR is an operational dashboard designed to identify seller behaviors in an e-commerce marketplace that consistently reduce customer trust over time. It correlates seller fulfillment metrics (misleading item returns, late dispatches, post-sale order cancellations) with customer review sentiment decay to calculate a dynamic **Seller Trust Index (0-100)** and trigger automated operational enforcement actions.

---

## 🛠️ Tech Stack & Architecture

- **Language**: Python 3.11+
- **Data Manipulation**: Pandas, NumPy
- **Database & Querying Layer**: SQL / SQLite
- **Interactive Dashboard**: Streamlit, Plotly
- **Styling**: Modern dark theme glassmorphism CSS
- **CI/CD Pipeline**: GitHub Actions (Data seeding & `pytest` automated validation)

---

## 📊 Features & Core Concepts

### 1. Seller Trust Index (0-100)
The Trust Score evaluates sellers dynamically over configurable sliding windows (30/60/90/180 days):
- **Misleading Return Penalty**: Deducts points for returns categorized under *Misleading Description* or *Defective Product*.
- **Late Dispatch Penalty**: Penalizes high delay ratios against promised delivery dates.
- **Cancellation Penalty**: Severe penalties for post-payment seller cancellations due to stockouts.
- **Sentiment Decay Penalty**: Monitors drops in moving-average review sentiment scores.
- **Support Latency Factor**: Penalizes long dispute resolution lead times.

### 2. Risk Tiers
- **Critical Risk ($T < 50$)**: Immediate visibility restriction and catalog audit required.
- **Moderate Risk ($50 \le T < 70$)**: Formal operational warning issued with mandatory support SLA.
- **Watchlist ($70 \le T < 85$)**: Fulfillment audit and review sentinel monitoring.
- **Low Risk / Healthy ($T \ge 85$)**: High trust score, eligible for Top Seller badge.

### 3. Interactive Streamlit Dashboard
- **Executive Trust Overview**: Marketplace-wide KPI cards, risk tier donut chart, and primary trust penalty drivers.
- **Behavior & Sentiment Deep-Dive**: Scatter plot of Misleading Returns vs. Negative Review Sentiment, correlation matrix heatmap, and individual seller historical trajectories.
- **Operations Action Center**: Recommended enforcement actions table with CSV export.
- **SQLite Data Explorer**: Raw database table views and custom SQL query workbench.

---

## 🚀 Quickstart Guide

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/ytor.git
cd YTOR
pip install -r requirements.txt
```

### 2. Seed SQLite Database
```bash
python -m src.generator
```

### 3. Launch Streamlit Dashboard
```bash
streamlit run app.py
```

### 4. Run Pytest Suite
```bash
python -m pytest tests/
```

---

## 📁 Repository Structure

```
YTOR/
├── .github/
│   └── workflows/
│       └── pipeline.yml         # GitHub Actions workflow for CI/CD
├── data/
│   ├── schema.sql               # SQLite schema definition
│   └── ytor.db                  # Generated SQLite database
├── src/
│   ├── __init__.py
│   ├── db.py                    # SQLite connection & query helper module
│   ├── generator.py             # Realistic marketplace data generator
│   ├── trust_model.py           # Trust Index math & risk tier algorithms
│   └── analytics.py             # Pandas/NumPy analytics & aggregations
├── tests/
│   ├── test_db.py               # Unit tests for database & schema
│   └── test_analytics.py        # Unit tests for trust engine & metrics
├── .streamlit/
│   └── config.toml              # Streamlit layout & color theme config
├── app.py                       # Main Streamlit web application
├── styles.css                   # Custom CSS styling
├── requirements.txt             # Dependency requirements
└── README.md                    # Project documentation
```
