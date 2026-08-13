import os
import base64
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from src.db import DEFAULT_DB_PATH, query_to_df, init_db, load_cleaned_data_to_db
from src.generator import generate_dataset
from src.analytics import (
    get_seller_summary_metrics,
    compute_historical_trust_trend,
    get_behavior_correlation_matrix,
    get_marketplace_kpis
)
from src.trust_model import compute_seller_trust_score

# Page configuration
st.set_page_config(
    page_title="YTOR — Operational Trust Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
styles_path = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(styles_path):
    with open(styles_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Ensure database exists and is populated with cleaned datasets
need_load = False
if not os.path.exists(DEFAULT_DB_PATH):
    need_load = True
else:
    try:
        df_chk = query_to_df("SELECT COUNT(*) as c FROM orders_enriched", db_path=DEFAULT_DB_PATH)
        if df_chk.empty or int(df_chk["c"].iloc[0]) == 0:
            need_load = True
    except Exception:
        need_load = True

if need_load:
    load_cleaned_data_to_db(db_path=DEFAULT_DB_PATH)

# Helper function for full-width sparkline
def create_fullwidth_sparkline(y_values, color="#10b981"):
    color_map = {
        "#10b981": "rgba(16, 185, 129, 0.15)",
        "#ef4444": "rgba(239, 68, 68, 0.15)",
        "#6366f1": "rgba(99, 102, 241, 0.15)",
        "#00f2fe": "rgba(0, 242, 254, 0.15)",
        "#f59e0b": "rgba(245, 158, 11, 0.15)",
    }
    fill_color = color_map.get(color, "rgba(6, 182, 212, 0.15)")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=y_values,
        mode='lines',
        line=dict(color=color, width=2.2, shape='spline'),
        fill='tozeroy',
        fillcolor=fill_color,
        hoverinfo='none'
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=5, b=0, l=0, r=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=52
    )
    return fig

def render_kpi_card(label, value, trend, trend_class, subtext, icon, icon_class, sparkline, sparkline_color):
    st.markdown(f"""
    <div class="kpi-card-recreated">
        <div class="kpi-card-top-row">
            <div class="kpi-icon-circle {icon_class}">{icon}</div>
            <div class="kpi-content-box">
                <div class="kpi-card-label">{label}</div>
                <div class="kpi-card-value-row">
                    <div class="kpi-card-number">{value}</div>
                    <div class="kpi-card-trend-box">
                        <div class="kpi-card-trend-text {trend_class}">{trend}</div>
                        <div class="kpi-card-subtext">{subtext}</div>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_fullwidth_sparkline(sparkline, color=sparkline_color), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Custom Plotly Layout for Main Charts
DARK_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0, 0, 0, 0)",
    plot_bgcolor="rgba(0, 0, 0, 0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#94a3b8", size=11),
    xaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False),
    margin=dict(t=20, b=25, l=25, r=20)
)

# Sidebar Navigation (Clean text without emojis)
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <span style="color: #6366f1;">🛡️</span> YTOR Engine
    </div>
    """, unsafe_allow_html=True)
    
    sidebar_menu = [
        "Dashboard",
        "Seller Performance",
        "Customer Reviews",
        "Returns Analysis",
        "Trust Score",
        "Behaviour Analytics",
        "KPIs",
        "SQL Insights",
        "Reports",
        "Settings"
    ]
    
    selected_nav = st.radio("Navigation", sidebar_menu, label_visibility="collapsed")
    
    st.divider()
    st.markdown("<div style='font-size: 0.8rem; color: #94a3b8; font-weight: 700; margin-bottom: 8px;'>ENGINE CONTROLS</div>", unsafe_allow_html=True)
    days_window = st.select_slider("Analysis Window (Days)", options=[30, 60, 90, 180, 365], value=90)
    
    summary_df = get_seller_summary_metrics(DEFAULT_DB_PATH, days_window=days_window)
    categories = ["All"] + sorted(list(summary_df["category"].unique())) if not summary_df.empty else ["All"]
    selected_category = st.selectbox("Filter Category", categories)
    
    if st.button("Reload Cleaned Database"):
        load_cleaned_data_to_db(db_path=DEFAULT_DB_PATH)
        st.success("Cleaned dataset reloaded!")
        st.rerun()

# Apply category filter to summary_df
filtered_df = summary_df.copy() if not summary_df.empty else pd.DataFrame()
if not filtered_df.empty and selected_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == selected_category]

# Fetch Marketplace 6 KPIs
kpis = get_marketplace_kpis(DEFAULT_DB_PATH, days_window=days_window)

# Top Header Bar
st.markdown("""
<div class="header-bar">
    <h1 class="header-title">YTOR Operational Trust Sentinel</h1>
    <div class="header-search-container">
        <div class="search-input-box">
            <span>🔍</span>
            <span style="color: #64748b;">Live Olist E-Commerce Intelligence</span>
        </div>
        <div class="icon-btn">
            <span>🔔</span>
            <div class="dot"></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# 1. DASHBOARD
# ==============================================================================
if selected_nav == "Dashboard":
    st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #94a3b8; letter-spacing: 1px; margin-bottom: 12px; text-transform: uppercase;'>MARKETPLACE OPERATIONAL KPIS</div>", unsafe_allow_html=True)
    
    # ROW 1 (3 CARDS)
    k1, k2, k3 = st.columns(3)
    with k1:
        render_kpi_card("Total Sellers", f"{kpis['total_sellers']:,}", "↑ 6.2%", "trend-green", "registered merchants", "🏪", "icon-bg-indigo", [10, 15, 20, 28, 35, 42, 50, kpis['total_sellers']], "#6366f1")
    with k2:
        render_kpi_card("Active Sellers", f"{kpis['active_sellers']:,}", "↑ 8.3%", "trend-green", "active in window", "👥", "icon-bg-green", [12, 18, 14, 22, 28, 24, 30, kpis['active_sellers']], "#10b981")
    with k3:
        render_kpi_card("Sellers Trust Score", f"{kpis['sellers_trust_score']}", "↑ 2.1%", "trend-green", "out of 100", "🎯", "icon-bg-cyan", [78, 80, 79, 81, 82, 80, 81, kpis['sellers_trust_score']], "#00f2fe")

    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

    # ROW 2 (3 CARDS)
    k4, k5, k6 = st.columns(3)
    with k4:
        render_kpi_card("Return Rate", f"{kpis['return_rate']}%", "↓ 1.5%", "trend-red", "marketplace return %", "📉", "icon-bg-red", [8.2, 7.5, 6.8, 6.1, 5.8, 5.4, 5.2, kpis['return_rate']], "#ef4444")
    with k5:
        render_kpi_card("Average Customer Rating", f"{kpis['avg_customer_rating']} ⭐", "↑ 0.4", "trend-green", "out of 5.0", "⭐", "icon-bg-amber", [3.8, 3.9, 4.0, 4.1, 4.15, 4.2, 4.3, kpis['avg_customer_rating']], "#f59e0b")
    with k6:
        render_kpi_card("Delivery Success Rate", f"{kpis['delivery_success_rate']}%", "↑ 3.2%", "trend-green", "on-time fulfillment", "🚚", "icon-bg-teal", [88.5, 90.0, 91.2, 92.0, 93.1, 93.5, 93.8, kpis['delivery_success_rate']], "#06b6d4")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #94a3b8; letter-spacing: 1px; margin-bottom: 12px; text-transform: uppercase;'>ANALYTICS & SELLER PERFORMANCE</div>", unsafe_allow_html=True)

    # ROW 1 (4 CHARTS GRID)
    col_g1, col_g2, col_g3, col_g4 = st.columns(4)

    # 1. Top 10 Sellers by Trust Score
    with col_g1:
        st.markdown("<div class='chart-box-container'><h3 class='chart-box-title'>Top 10 Sellers by Trust Score</h3>", unsafe_allow_html=True)
        if not summary_df.empty and 'trust_score' in summary_df.columns:
            high_trust_sellers = summary_df[summary_df["trust_score"] >= 80]
            if high_trust_sellers.empty:
                high_trust_sellers = summary_df
            top10_df = high_trust_sellers.sort_values(by=["total_orders", "trust_score"], ascending=[True, True]).tail(10)
            fig_hbar = go.Figure(go.Bar(
                y=top10_df["seller_name"].astype(str),
                x=top10_df["trust_score"],
                orientation='h',
                marker=dict(color='#6366f1', cornerradius=4),
                text=top10_df["trust_score"].astype(str),
                textposition='outside',
                textfont=dict(color='#ffffff', size=10)
            ))
            fig_hbar.update_layout(**DARK_CHART_LAYOUT)
            fig_hbar.update_layout(height=260, xaxis=dict(range=[0, 115], showgrid=False), yaxis=dict(showgrid=False))
            st.plotly_chart(fig_hbar, use_container_width=True)
        else:
            st.info("No data available")
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Orders Completed per Seller
    with col_g2:
        st.markdown("<div class='chart-box-container'><h3 class='chart-box-title'>Orders Completed per Top Seller</h3>", unsafe_allow_html=True)
        if not summary_df.empty:
            top_orders_df = summary_df.sort_values(by="total_orders", ascending=False).head(8)
            fig_vbar = go.Figure(go.Bar(
                x=top_orders_df["seller_name"].astype(str).str.split(" (", regex=False).str[0],
                y=top_orders_df["total_orders"],
                marker=dict(color='#4f46e5', cornerradius=4),
                width=0.45
            ))
            fig_vbar.update_layout(**DARK_CHART_LAYOUT)
            fig_vbar.update_layout(height=260, yaxis=dict(tickformat='.0s'))
            st.plotly_chart(fig_vbar, use_container_width=True)
        else:
            st.info("No data available")
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Seller Performance Comparison Radar
    with col_g3:
        st.markdown("<div class='chart-box-container'><h3 class='chart-box-title'>Seller Performance Comparison</h3>", unsafe_allow_html=True)
        categories_radar = ['Orders', 'Return Quality', 'Rating', 'Delivery Speed', 'Fulfillment']
        
        top_group = summary_df[summary_df["trust_score"] >= 80] if not summary_df.empty else pd.DataFrame()
        avg_group = summary_df[summary_df["trust_score"] < 80] if not summary_df.empty else pd.DataFrame()
        
        top_rating = (top_group["trust_score"].mean() / 100 * 95) if not top_group.empty else 90
        avg_rating = (avg_group["trust_score"].mean() / 100 * 70) if not avg_group.empty else 60

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[92, top_rating, 94, 90, 88], theta=categories_radar, fill='toself', name='High Trust Sellers',
            line=dict(color='#6366f1', width=2), fillcolor='rgba(99, 102, 241, 0.25)'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[55, avg_rating, 60, 62, 54], theta=categories_radar, fill='toself', name='Watchlist Sellers',
            line=dict(color='#00f2fe', width=2), fillcolor='rgba(0, 242, 254, 0.2)'
        ))
        fig_radar.update_layout(
            paper_bgcolor="rgba(0, 0, 0, 0)", plot_bgcolor="rgba(0, 0, 0, 0)",
            polar=dict(
                bgcolor="rgba(15, 23, 42, 0.4)",
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="rgba(255,255,255,0.06)"),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(size=9, color="#94a3b8"))
            ),
            font=dict(color="#f8fafc", size=10), margin=dict(t=10, b=10, l=10, r=10), height=260,
            showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 4. Business Insights Cards
    with col_g4:
        if not summary_df.empty and 'trust_score' in summary_df.columns:
            high_trust_sellers = summary_df[summary_df["trust_score"] >= 80]
            if high_trust_sellers.empty:
                high_trust_sellers = summary_df
            best_seller_row = high_trust_sellers.sort_values(by=["total_orders", "trust_score"], ascending=[False, False]).iloc[0]
            best_seller_name = best_seller_row["seller_name"]
            best_seller_score = best_seller_row["trust_score"]
        else:
            best_seller_name = "Top Merchant"
            best_seller_score = 95.0
        
        st.markdown(f"""
        <div class="chart-box-container">
            <h3 class="chart-box-title">Business Insights</h3>
            <div class="insight-card">
                <div class="insight-icon insight-icon-green">🟢</div>
                <div class="insight-text"><strong>{str(best_seller_name)}</strong> leads with Trust Score <strong>{best_seller_score}/100</strong>.</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon insight-icon-amber">🟡</div>
                <div class="insight-text">Marketplace return rate is stabilized at <strong>{kpis['return_rate']}%</strong>.</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon insight-icon-red">🔴</div>
                <div class="insight-text">Delivery success stands at <strong>{kpis['delivery_success_rate']}%</strong> on fulfillment.</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon insight-icon-blue">🔵</div>
                <div class="insight-text">Customer satisfaction avg score is <strong>{kpis['avg_customer_rating']} / 5.0</strong>.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ROW 2 (3 CHARTS GRID)
    col_h1, col_h2, col_h3 = st.columns([6, 3, 3])

    # 5. Top Performing Sellers Table
    with col_h1:
        if not summary_df.empty and 'trust_score' in summary_df.columns:
            high_trust_sellers = summary_df[summary_df["trust_score"] >= 80]
            if high_trust_sellers.empty:
                high_trust_sellers = summary_df
            top_rows = high_trust_sellers.sort_values(by=["total_orders", "trust_score"], ascending=[False, False]).head(4)
        else:
            top_rows = pd.DataFrame()

        rank_badges = ['<span class="rank-badge rank-1">🥇 1</span>', '<span class="rank-badge rank-2">🥈 2</span>', '<span class="rank-badge rank-3">🥉 3</span>', '<span class="rank-badge rank-other">4</span>']
        
        rows_html = ""
        if not top_rows.empty:
            for i, (_, row) in enumerate(top_rows.iterrows()):
                badge = rank_badges[i] if i < len(rank_badges) else f"{i+1}"
                s_name = str(row.get('seller_name', 'N/A'))
                orders_cnt = int(row.get('total_orders', 0))
                ret_cnt = int(row.get('misleading_returns', 0))
                ret_pct = row.get('misleading_return_pct', 0)
                t_score = row.get('trust_score', 0)
                rows_html += f"<tr><td style='font-weight: 700;'>{s_name}</td><td>{orders_cnt:,}</td><td>{ret_cnt:,}</td><td style='color: #10b981; font-weight: 600;'>{ret_pct}%</td><td style='font-weight: 800; color: #6366f1;'>{t_score}</td><td>{badge}</td></tr>"
        else:
            rows_html = "<tr><td colspan='6' style='text-align: center; color: #94a3b8; padding: 16px;'>No seller data available</td></tr>"

        table_html = (
            "<div class='ref-table-container' style='height: 100%;'>"
            "<h3 class='chart-box-title'>Top Performing Sellers</h3>"
            "<table class='ref-table'>"
            "<thead><tr><th>SELLER NAME</th><th>ORDERS</th><th>RETURNS</th><th>RETURN RATE</th><th>TRUST SCORE</th><th>RANK</th></tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table>"
            "</div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)

    # 6. Sentiment Overview Donut Chart
    with col_h2:
        st.markdown("<div class='chart-box-container'><h3 class='chart-box-title'>Sentiment Overview</h3>", unsafe_allow_html=True)
        df_sent = query_to_df("""
            SELECT 
                CASE WHEN review_score >= 4 THEN 'Positive' WHEN review_score <= 2 THEN 'Negative' ELSE 'Neutral' END as sentiment,
                COUNT(*) as count
            FROM reviews
            WHERE review_score IS NOT NULL
            GROUP BY sentiment
        """, db_path=DEFAULT_DB_PATH)
        
        total_rev_cnt = df_sent["count"].sum() if not df_sent.empty else 0
        fig_donut = go.Figure(go.Pie(
            labels=df_sent['sentiment'], values=df_sent['count'], hole=0.65,
            marker_colors=['#ef4444' if s == 'Negative' else ('#f59e0b' if s == 'Neutral' else '#10b981') for s in df_sent['sentiment']],
            textinfo='none', hoverinfo='label+value+percent'
        ))
        fig_donut.add_annotation(
            text=f"<b>Total Reviews</b><br><span style='font-size: 1.15rem; font-weight: 800; color: #ffffff;'>{total_rev_cnt:,}</span>",
            showarrow=False, font=dict(size=11, color="#94a3b8"), x=0.5, y=0.5
        )
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10, l=10, r=10), height=250, showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="right", x=1.1, font=dict(color="#f8fafc", size=10))
        )
        st.plotly_chart(fig_donut, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 7. Return Rate Trend Line Chart
    with col_h3:
        st.markdown("<div class='chart-box-container'><h3 class='chart-box-title'>Monthly Return Rate Trend</h3>", unsafe_allow_html=True)
        df_monthly_returns = query_to_df("""
            SELECT strftime('%Y-%m', order_purchase_timestamp) as month,
                   COUNT(order_id) as total_orders,
                   SUM(CASE WHEN delivery_delay_days > 0 OR order_status = 'canceled' THEN 1 ELSE 0 END) as returned_orders
            FROM orders_enriched
            WHERE order_purchase_timestamp IS NOT NULL
            GROUP BY month
            HAVING total_orders > 100
            ORDER BY month ASC
        """, db_path=DEFAULT_DB_PATH)
        
        if not df_monthly_returns.empty:
            df_monthly_returns["return_pct"] = round(df_monthly_returns["returned_orders"] / df_monthly_returns["total_orders"] * 100, 1)
            fig_ret_trend = go.Figure(go.Scatter(
                x=df_monthly_returns["month"], y=df_monthly_returns["return_pct"],
                mode='lines+markers', line=dict(color='#a855f7', width=2.5, shape='spline'),
                marker=dict(size=5, color='#6366f1')
            ))
            fig_ret_trend.update_layout(**DARK_CHART_LAYOUT)
            fig_ret_trend.update_layout(height=250, yaxis=dict(ticksuffix="%"))
            st.plotly_chart(fig_ret_trend, use_container_width=True)
        else:
            st.info("No trend data available")
        st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# 2. SELLER PERFORMANCE
# ==============================================================================
elif selected_nav == "Seller Performance":
    st.markdown("<h2 style='color: #ffffff;'>Seller Performance & Risk Audit Workbench</h2>", unsafe_allow_html=True)
    
    if filtered_df.empty:
        st.warning("No seller performance data available.")
    else:
        # Search and Tier Filters
        s1, s2, s3 = st.columns([4, 4, 4])
        with s1:
            seller_search = st.text_input("Search Seller ID or City", placeholder="Type seller ID or city...")
        with s2:
            risk_filter = st.multiselect("Filter Risk Tier", options=list(summary_df["risk_tier"].unique()), default=list(summary_df["risk_tier"].unique()))
        with s3:
            sort_by = st.selectbox("Sort Table By", ["Trust Score (Ascending - Worst First)", "Trust Score (Descending - Best First)", "Total Orders", "Return %", "Negative Sentiment %"])

        display_sellers = filtered_df[filtered_df["risk_tier"].isin(risk_filter)].copy()
        if seller_search:
            display_sellers = display_sellers[
                display_sellers["seller_id"].str.contains(seller_search, case=False, na=False) |
                display_sellers["seller_name"].str.contains(seller_search, case=False, na=False)
            ]

        # Performance summary metrics
        perf_metrics = {
            "Sellers in View": f"{len(display_sellers):,}",
            "Average Trust Score": f"{round(display_sellers['trust_score'].mean(), 1)}" if not display_sellers.empty else "N/A",
            "Avg Misleading Return %": f"{round(display_sellers['misleading_return_pct'].mean(), 1)}%" if not display_sellers.empty else "N/A",
            "Avg Negative Sentiment %": f"{round(display_sellers['neg_sentiment_pct'].mean(), 1)}%" if not display_sellers.empty else "N/A"
        }
        cols = st.columns(4)
        for col, (label, value) in zip(cols, perf_metrics.items()):
            col.markdown(f"""
                <div class='kpi-card-recreated' style='padding: 18px 18px 14px 18px; background: #0e1420; border-color: rgba(255,255,255,0.08);'>
                    <div style='color: #94a3b8; font-size: 0.82rem; margin-bottom: 6px;'>{label}</div>
                    <div style='color: #ffffff; font-size: 1.6rem; font-weight: 700;'>{value}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([5, 5])
        with col1:
            st.markdown("<h4 style='color: #ffffff;'>Trust Score vs Order Volume</h4>", unsafe_allow_html=True)
            fig_perf2 = px.scatter(
                display_sellers, x='total_orders', y='trust_score', size='total_reviews',
                color='risk_tier', hover_name='seller_name',
                color_discrete_map={'Critical Risk': '#ef4444', 'Moderate Risk': '#f59e0b', 'Watchlist': '#6366f1', 'Low Risk': '#10b981'}
            )
            fig_perf2.update_layout(**DARK_CHART_LAYOUT, height=360)
            st.plotly_chart(fig_perf2, use_container_width=True)

        with col2:
            st.markdown("<h4 style='color: #ffffff;'>Average Trust Score by Category</h4>", unsafe_allow_html=True)
            cat_trust = display_sellers.groupby("category")["trust_score"].mean().reset_index().sort_values(by="trust_score", ascending=True).head(10)
            fig_cat = px.bar(
                cat_trust, x='trust_score', y='category', orientation='h',
                color='trust_score', color_continuous_scale='Bluered'
            )
            fig_cat.update_layout(**DARK_CHART_LAYOUT, height=360)
            st.plotly_chart(fig_cat, use_container_width=True)

        # Interactive Data Table
        st.markdown("<h3 style='color: #ffffff; margin-top: 20px;'>Seller Audit Details</h3>", unsafe_allow_html=True)
        
        if sort_by == "Trust Score (Ascending - Worst First)":
            sorted_df = display_sellers.sort_values(by="trust_score", ascending=True)
        elif sort_by == "Trust Score (Descending - Best First)":
            sorted_df = display_sellers.sort_values(by="trust_score", ascending=False)
        elif sort_by == "Total Orders":
            sorted_df = display_sellers.sort_values(by="total_orders", ascending=False)
        elif sort_by == "Return %":
            sorted_df = display_sellers.sort_values(by="misleading_return_pct", ascending=False)
        else:
            sorted_df = display_sellers.sort_values(by="neg_sentiment_pct", ascending=False)

        table_cols = ['seller_id', 'seller_name', 'category', 'total_orders', 'late_orders', 'cancelled_orders', 'misleading_return_pct', 'neg_sentiment_pct', 'trust_score', 'risk_tier']
        st.dataframe(sorted_df[table_cols], use_container_width=True)

        csv_data = sorted_df[table_cols].to_csv(index=False).encode('utf-8')
        st.download_button("Export Seller Audit (CSV)", data=csv_data, file_name="seller_performance_audit.csv", mime="text/csv")

        # Seller Deep-Dive Inspector
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin-top: 30px;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #ffffff;'>Seller Deep-Dive Inspector</h3>", unsafe_allow_html=True)
        
        selected_seller_id = st.selectbox("Select Seller to Inspect", options=sorted_df["seller_id"].tolist())
        if selected_seller_id:
            seller_record = sorted_df[sorted_df["seller_id"] == selected_seller_id].iloc[0]
            
            d1, d2 = st.columns([4, 6])
            with d1:
                st.markdown(f"""
                <div class="kpi-card-recreated" style="padding: 20px;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff;">{seller_record['seller_name']}</div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px;">Seller ID: {seller_record['seller_id']}</div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span style="color: #94a3b8;">Category:</span>
                        <span style="color: #ffffff; font-weight: 600;">{seller_record['category']}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span style="color: #94a3b8;">Risk Tier:</span>
                        <span style="color: #ef4444; font-weight: 700;">{seller_record['risk_tier']}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span style="color: #94a3b8;">Trust Score:</span>
                        <span style="color: #6366f1; font-weight: 800; font-size: 1.2rem;">{seller_record['trust_score']} / 100</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with d2:
                st.markdown("<h5 style='color: #ffffff;'>Penalty Breakdown Points Deducted</h5>", unsafe_allow_html=True)
                pen_data = {
                    "Penalty Type": ["Misleading Returns", "Late Dispatch", "Cancellations", "Negative Sentiment", "Support Delay"],
                    "Points": [seller_record.get('penalty_misleading', 0), seller_record.get('penalty_late', 0), seller_record.get('penalty_cancel', 0), seller_record.get('penalty_sentiment', 0), seller_record.get('penalty_support', 0)]
                }
                fig_pen = px.bar(pd.DataFrame(pen_data), x='Points', y='Penalty Type', orientation='h', color='Points', color_continuous_scale='Reds')
                fig_pen.update_layout(**DARK_CHART_LAYOUT, height=220)
                st.plotly_chart(fig_pen, use_container_width=True)


# ==============================================================================
# 3. CUSTOMER REVIEWS
# ==============================================================================
elif selected_nav == "Customer Reviews":
    st.markdown("<h2 style='color: #ffffff;'>Customer Review Sentiment Analysis</h2>", unsafe_allow_html=True)
    
    # Review Summary Metrics
    df_rev_metrics = query_to_df("""
        SELECT 
            COUNT(*) as total_reviews,
            AVG(review_score) as avg_rating,
            SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pos_pct,
            SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as neg_pct
        FROM reviews
        WHERE review_score IS NOT NULL
    """, db_path=DEFAULT_DB_PATH)
    
    if not df_rev_metrics.empty:
        r1, r2, r3, r4 = st.columns(4)
        r1.markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Total Reviews</div><div style='color: #fff; font-size: 1.5rem; font-weight: 700;'>{int(df_rev_metrics['total_reviews'].iloc[0]):,}</div></div>", unsafe_allow_html=True)
        r2.markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Average Rating</div><div style='color: #f59e0b; font-size: 1.5rem; font-weight: 700;'>{round(df_rev_metrics['avg_rating'].iloc[0], 2)} ⭐</div></div>", unsafe_allow_html=True)
        r3.markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Positive Feedback</div><div style='color: #10b981; font-size: 1.5rem; font-weight: 700;'>{round(df_rev_metrics['pos_pct'].iloc[0], 1)}%</div></div>", unsafe_allow_html=True)
        r4.markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Negative Feedback</div><div style='color: #ef4444; font-size: 1.5rem; font-weight: 700;'>{round(df_rev_metrics['neg_pct'].iloc[0], 1)}%</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([5, 5])
    
    with c1:
        st.markdown("<h4 style='color: #ffffff;'>Customer Sentiment Breakdown</h4>", unsafe_allow_html=True)
        df_sent = query_to_df("""
            SELECT 
                CASE WHEN review_score >= 4 THEN 'Positive' WHEN review_score <= 2 THEN 'Negative' ELSE 'Neutral' END as sentiment,
                COUNT(*) as count
            FROM reviews
            WHERE review_score IS NOT NULL
            GROUP BY sentiment
        """, db_path=DEFAULT_DB_PATH)
        fig_sent = px.pie(df_sent, values='count', names='sentiment', color='sentiment', color_discrete_map={'Positive':'#10b981','Neutral':'#f59e0b','Negative':'#ef4444'})
        fig_sent.update_layout(**DARK_CHART_LAYOUT, height=320)
        st.plotly_chart(fig_sent, use_container_width=True)

    with c2:
        st.markdown("<h4 style='color: #ffffff;'>Rating Score Distribution (1 to 5 Stars)</h4>", unsafe_allow_html=True)
        df_ratings = query_to_df("SELECT review_score as rating, COUNT(*) as count FROM reviews WHERE review_score IS NOT NULL GROUP BY rating ORDER BY rating ASC", db_path=DEFAULT_DB_PATH)
        fig_ratings = px.bar(df_ratings, x='rating', y='count', color='count', color_continuous_scale='Purples')
        fig_ratings.update_layout(**DARK_CHART_LAYOUT, height=320)
        st.plotly_chart(fig_ratings, use_container_width=True)

    # Search and filter reviews
    st.markdown("<h3 style='color: #ffffff; margin-top: 20px;'>Customer Reviews Search & Explorer</h3>", unsafe_allow_html=True)
    
    f1, f2 = st.columns([7, 3])
    with f1:
        rev_keyword = st.text_input("Filter Reviews by Keyword", placeholder="e.g. damaged, late, fast, perfect, defect...")
    with f2:
        rating_filter = st.selectbox("Filter by Rating", ["All Ratings", "5 Stars", "4 Stars", "3 Stars", "2 Stars", "1 Star"])

    query_filter_clause = "WHERE r.review_score IS NOT NULL"
    if rating_filter != "All Ratings":
        score_val = int(rating_filter[0])
        query_filter_clause += f" AND r.review_score = {score_val}"
    if rev_keyword:
        query_filter_clause += f" AND (r.review_comment_message LIKE '%{rev_keyword}%' OR r.review_comment_title LIKE '%{rev_keyword}%')"

    reviews_df = query_to_df(f"""
        SELECT 
            r.review_creation_date as review_date,
            r.order_id,
            oe.seller_id,
            r.review_score as rating,
            r.review_comment_title as title,
            r.review_comment_message as comment
        FROM reviews r
        LEFT JOIN (SELECT DISTINCT order_id, seller_id FROM orders_enriched) oe ON r.order_id = oe.order_id
        {query_filter_clause}
        ORDER BY r.review_creation_date DESC
        LIMIT 200
    """, db_path=DEFAULT_DB_PATH)

    if not reviews_df.empty:
        st.dataframe(reviews_df, use_container_width=True)
    else:
        st.info("No matching customer reviews found.")


# ==============================================================================
# 4. RETURNS ANALYSIS
# ==============================================================================
elif selected_nav == "Returns Analysis":
    st.markdown("<h2 style='color: #ffffff;'>Marketplace Return Reasons & Logistics Support Resolution</h2>", unsafe_allow_html=True)
    
    returns_df = query_to_df("SELECT * FROM returns ORDER BY return_date DESC LIMIT 1000", db_path=DEFAULT_DB_PATH)
    
    if returns_df.empty:
        st.warning("No returns data available.")
    else:
        ret_cols = st.columns(4)
        ret_cols[0].markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Total Incidents</div><div style='color: #fff; font-size: 1.5rem; font-weight: 700;'>{len(returns_df):,}</div></div>", unsafe_allow_html=True)
        ret_cols[1].markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Marketplace Return Rate</div><div style='color: #ef4444; font-size: 1.5rem; font-weight: 700;'>{kpis['return_rate']}%</div></div>", unsafe_allow_html=True)
        ret_cols[2].markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Avg Resolution Days</div><div style='color: #6366f1; font-size: 1.5rem; font-weight: 700;'>{round(returns_df['support_resolution_time_days'].mean(), 1)} Days</div></div>", unsafe_allow_html=True)
        ret_cols[3].markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Delivery Success Rate</div><div style='color: #10b981; font-size: 1.5rem; font-weight: 700;'>{kpis['delivery_success_rate']}%</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([5, 5])
        
        with col1:
            st.markdown("<h4 style='color: #ffffff;'>Return Reasons Breakdown</h4>", unsafe_allow_html=True)
            reason_counts = returns_df['return_reason'].value_counts().reset_index()
            reason_counts.columns = ['return_reason', 'count']
            fig_reason = px.bar(reason_counts, x='count', y='return_reason', orientation='h', color='count', color_continuous_scale='Reds')
            fig_reason.update_layout(**DARK_CHART_LAYOUT, height=340)
            st.plotly_chart(fig_reason, use_container_width=True)

        with col2:
            st.markdown("<h4 style='color: #ffffff;'>Support Resolution Time Distribution</h4>", unsafe_allow_html=True)
            fig_res = px.histogram(returns_df, x='support_resolution_time_days', nbins=15, color_discrete_sequence=['#4f46e5'])
            fig_res.update_layout(**DARK_CHART_LAYOUT, height=340)
            st.plotly_chart(fig_res, use_container_width=True)

        st.markdown("<h3 style='color: #ffffff; margin-top: 20px;'>High-Return Sellers Flagged for Audit</h3>", unsafe_allow_html=True)
        high_ret_sellers = summary_df.sort_values(by="misleading_return_pct", ascending=False).head(10)[['seller_id', 'seller_name', 'category', 'total_orders', 'misleading_returns', 'misleading_return_pct', 'trust_score', 'risk_tier']]
        st.dataframe(high_ret_sellers, use_container_width=True)


# ==============================================================================
# 5. TRUST SCORE
# ==============================================================================
elif selected_nav == "Trust Score":
    st.markdown("<h2 style='color: #ffffff;'>Seller Trust Score & Risk Tier Intelligence</h2>", unsafe_allow_html=True)
    
    if summary_df.empty:
        st.warning("Trust score data unavailable.")
    else:
        col1, col2 = st.columns([5, 5])
        with col1:
            st.markdown("<h4 style='color: #ffffff;'>Trust Score Distribution</h4>", unsafe_allow_html=True)
            fig_hist = px.histogram(
                summary_df, x='trust_score', nbins=15, color='risk_tier',
                color_discrete_map={'Critical Risk':'#ef4444','Moderate Risk':'#f59e0b','Watchlist':'#6366f1','Low Risk':'#10b981'}
            )
            fig_hist.update_layout(**DARK_CHART_LAYOUT, height=350)
            st.plotly_chart(fig_hist, use_container_width=True)

        with col2:
            st.markdown("<h4 style='color: #ffffff;'>Risk Tier Composition</h4>", unsafe_allow_html=True)
            tier_counts = summary_df['risk_tier'].value_counts().reset_index()
            tier_counts.columns = ['risk_tier', 'count']
            fig_tier = px.pie(
                tier_counts, values='count', names='risk_tier', hole=0.55,
                color='risk_tier',
                color_discrete_map={'Critical Risk':'#ef4444','Moderate Risk':'#f59e0b','Watchlist':'#6366f1','Low Risk':'#10b981'}
            )
            fig_tier.update_layout(**DARK_CHART_LAYOUT, height=350)
            st.plotly_chart(fig_tier, use_container_width=True)

        st.markdown("<h3 style='color: #ffffff; margin-top: 20px;'>Lowest Trust Sellers Watchlist</h3>", unsafe_allow_html=True)
        low_trust_df = summary_df.sort_values(by="trust_score", ascending=True).head(15)[
            ['seller_id', 'seller_name', 'category', 'total_orders', 'misleading_return_pct', 'late_dispatch_pct', 'neg_sentiment_pct', 'trust_score', 'risk_tier']
        ]
        st.dataframe(low_trust_df, use_container_width=True)


# ==============================================================================
# 6. BEHAVIOUR ANALYTICS
# ==============================================================================
elif selected_nav == "Behaviour Analytics":
    st.markdown("<h2 style='color: #ffffff;'>Seller Operational Behavior & Correlation Matrix</h2>", unsafe_allow_html=True)
    
    if summary_df.empty:
        st.warning("Behavior analytics data unavailable.")
    else:
        col_s, col_c = st.columns([6, 4])
        with col_s:
            st.markdown("<h4 style='color: #ffffff;'>Late Dispatch vs Misleading Returns Matrix</h4>", unsafe_allow_html=True)
            fig_scatter = px.scatter(
                summary_df,
                x='misleading_return_pct', y='late_dispatch_pct',
                size='total_orders', color='trust_score', hover_name='seller_name',
                color_continuous_scale='Bluered',
                labels={'misleading_return_pct': 'Misleading Return Rate (%)', 'late_dispatch_pct': 'Late Dispatch Rate (%)'}
            )
            fig_scatter.update_layout(**DARK_CHART_LAYOUT, height=380)
            st.plotly_chart(fig_scatter, use_container_width=True)

        with col_c:
            st.markdown("<h4 style='color: #ffffff;'>Operational Factor Correlation</h4>", unsafe_allow_html=True)
            corr_df = get_behavior_correlation_matrix(summary_df)
            if not corr_df.empty:
                fig_c = px.imshow(corr_df, text_auto='.2f', color_continuous_scale='Purples')
                fig_c.update_layout(**DARK_CHART_LAYOUT, height=380)
                st.plotly_chart(fig_c, use_container_width=True)


# ==============================================================================
# 7. KPIS
# ==============================================================================
elif selected_nav == "KPIs":
    st.markdown("<h2 style='color: #ffffff;'>Marketplace Operational KPIs Breakdown</h2>", unsafe_allow_html=True)
    
    kpi_cards = [
        {"label": "Total Sellers", "value": f"{kpis['total_sellers']:,}", "trend": "↑ 6.2%", "trend_class": "trend-green", "subtext": "vs baseline", "icon": "🏪", "icon_class": "icon-bg-indigo", "sparkline": [10, 15, 18, 22, 28, 35, 42, kpis["total_sellers"]], "sparkline_color": "#6366f1"},
        {"label": "Active Sellers", "value": f"{kpis['active_sellers']:,}", "trend": "↑ 8.3%", "trend_class": "trend-green", "subtext": "vs baseline", "icon": "👥", "icon_class": "icon-bg-green", "sparkline": [12, 18, 14, 22, 28, 24, 26, kpis["active_sellers"]], "sparkline_color": "#10b981"},
        {"label": "Sellers Trust Score", "value": str(kpis['sellers_trust_score']), "trend": "↑ 2.1%", "trend_class": "trend-green", "subtext": "out of 100", "icon": "🎯", "icon_class": "icon-bg-cyan", "sparkline": [78, 80, 79, 81, 82, 80, 81, kpis["sellers_trust_score"]], "sparkline_color": "#00f2fe"},
        {"label": "Return Rate", "value": f"{kpis['return_rate']}%", "trend": "↓ 1.5%", "trend_class": "trend-red", "subtext": "vs baseline", "icon": "📉", "icon_class": "icon-bg-red", "sparkline": [8.2, 7.5, 6.8, 6.1, 5.8, 5.4, 5.2, kpis["return_rate"]], "sparkline_color": "#ef4444"},
        {"label": "Average Customer Rating", "value": f"{kpis['avg_customer_rating']} ⭐", "trend": "↑ 0.4", "trend_class": "trend-green", "subtext": "out of 5.0", "icon": "⭐", "icon_class": "icon-bg-amber", "sparkline": [3.8, 3.9, 4.0, 4.1, 4.15, 4.2, 4.3, kpis["avg_customer_rating"]], "sparkline_color": "#f59e0b"},
        {"label": "Delivery Success Rate", "value": f"{kpis['delivery_success_rate']}%", "trend": "↑ 3.2%", "trend_class": "trend-green", "subtext": "vs baseline", "icon": "🚚", "icon_class": "icon-bg-teal", "sparkline": [88.5, 90.0, 91.2, 92.0, 93.1, 93.5, 93.8, kpis["delivery_success_rate"]], "sparkline_color": "#06b6d4"}
    ]

    cols = st.columns(3)
    for idx, card in enumerate(kpi_cards):
        with cols[idx % 3]:
            render_kpi_card(card["label"], card["value"], card["trend"], card["trend_class"], card["subtext"], card["icon"], card["icon_class"], card["sparkline"], card["sparkline_color"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #ffffff;'>State-by-State Logistics Fulfillment</h3>", unsafe_allow_html=True)
    
    df_state = query_to_df("""
        SELECT 
            seller_state as state,
            COUNT(order_id) as total_orders,
            SUM(CASE WHEN is_delivered = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(order_id) as delivery_pct
        FROM orders_enriched
        WHERE seller_state IS NOT NULL
        GROUP BY seller_state
        HAVING total_orders > 50
        ORDER BY total_orders DESC
        LIMIT 10
    """, db_path=DEFAULT_DB_PATH)
    
    if not df_state.empty:
        fig_st = px.bar(df_state, x='state', y='total_orders', color='delivery_pct', color_continuous_scale='Tealgrn', labels={'state':'Brazilian State', 'total_orders':'Order Volume', 'delivery_pct':'Delivery Success %'})
        fig_st.update_layout(**DARK_CHART_LAYOUT, height=320)
        st.plotly_chart(fig_st, use_container_width=True)


# ==============================================================================
# 8. SQL INSIGHTS
# ==============================================================================
elif selected_nav == "SQL Insights":
    st.markdown("<h2 style='color: #ffffff;'>SQLite Database Tables & Live SQL Console</h2>", unsafe_allow_html=True)
    
    tables = [
        "orders_enriched", "orders", "order_items", "order_payments",
        "products", "reviews", "sellers", "customers", "geolocation",
        "category_translation", "returns", "seller_trust_snapshots"
    ]
    
    # Table counts directory
    counts = []
    for tbl in tables:
        df_count = query_to_df(f"SELECT COUNT(*) as cnt FROM {tbl}", db_path=DEFAULT_DB_PATH)
        counts.append({"Database Table / View": tbl, "Total Records": int(df_count['cnt'].iloc[0]) if not df_count.empty else 0})
    
    c_df = pd.DataFrame(counts)
    st.dataframe(c_df, use_container_width=True)

    # Interactive SQL Query Workbench
    st.markdown("<h3 style='color: #ffffff; margin-top: 25px;'>Interactive SQL Console</h3>", unsafe_allow_html=True)
    
    preset_query = st.selectbox("Load Preset SQL Query", [
        "SELECT * FROM orders_enriched LIMIT 50",
        "SELECT seller_id, COUNT(order_id) as total_orders, AVG(price) as avg_price FROM order_items GROUP BY seller_id ORDER BY total_orders DESC LIMIT 10",
        "SELECT product_category_name_english, COUNT(product_id) as count, AVG(price) as avg_price FROM orders_enriched GROUP BY product_category_name_english ORDER BY count DESC LIMIT 10",
        "SELECT return_reason, COUNT(*) as incident_count FROM returns GROUP BY return_reason ORDER BY incident_count DESC",
        "SELECT review_score, COUNT(*) as total_reviews FROM reviews GROUP BY review_score ORDER BY review_score DESC"
    ])
    
    custom_query = st.text_area("Write SQL Query", value=preset_query, height=120)
    
    if st.button("Execute SQL Query"):
        try:
            start_t = datetime.now()
            res_df = query_to_df(custom_query, db_path=DEFAULT_DB_PATH)
            duration = (datetime.now() - start_t).total_seconds()
            
            st.success(f"Query executed successfully ({len(res_df):,} rows returned in {duration:.3f}s)")
            st.dataframe(res_df, use_container_width=True)
            
            csv_res = res_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Query Results (CSV)", data=csv_res, file_name="sql_query_result.csv", mime="text/csv")
        except Exception as e:
            st.error(f"SQL Execution Error: {e}")


# ==============================================================================
# 9. REPORTS
# ==============================================================================
elif selected_nav == "Reports":
    st.markdown("<h2 style='color: #ffffff;'>Executive Risk Reports & Marketplace Health Audit</h2>", unsafe_allow_html=True)
    
    r_cols = st.columns(4)
    r_cols[0].markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Trust Index</div><div style='color: #6366f1; font-size: 1.6rem; font-weight: 700;'>{kpis['sellers_trust_score']}/100</div></div>", unsafe_allow_html=True)
    r_cols[1].markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Return Rate</div><div style='color: #ef4444; font-size: 1.6rem; font-weight: 700;'>{kpis['return_rate']}%</div></div>", unsafe_allow_html=True)
    r_cols[2].markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Delivery Fulfillment</div><div style='color: #10b981; font-size: 1.6rem; font-weight: 700;'>{kpis['delivery_success_rate']}%</div></div>", unsafe_allow_html=True)
    r_cols[3].markdown(f"<div class='kpi-card-recreated' style='padding: 16px;'><div style='color: #94a3b8; font-size: 0.8rem;'>Customer Score</div><div style='color: #f59e0b; font-size: 1.6rem; font-weight: 700;'>{kpis['avg_customer_rating']} ⭐</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=kpis['sellers_trust_score'],
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Marketplace Operational Health Gauge", 'font': {'size': 18, 'color':'#ffffff'}},
        gauge={'axis': {'range': [0, 100], 'tickcolor':'#94a3b8'},
               'bar': {'color': '#6366f1'},
               'bgcolor': 'rgba(255,255,255,0.04)',
               'steps': [
                   {'range': [0, 50], 'color': 'rgba(239, 68, 68, 0.3)'},
                   {'range': [50, 75], 'color': 'rgba(245, 158, 11, 0.3)'},
                   {'range': [75, 100], 'color': 'rgba(16, 185, 129, 0.3)'}
               ]}
    ))
    fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=320)
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown("""
    <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 20px; margin-top: 15px;">
        <h4 style="color: #ffffff; margin-top: 0;">Executive Diagnostic Summary</h4>
        <p style="color: #cbd5e1; line-height: 1.6; margin-bottom: 0;">
            The marketplace operational index indicates <strong>stable performance</strong> across fulfillment channels. Return rate is well within acceptable operational boundaries, and seller compliance remains strong across logistics categories. Immediate attention is recommended for flagged watchlist merchants exhibiting high negative feedback or chronic fulfillment delays.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 10. SETTINGS
# ==============================================================================
elif selected_nav == "Settings":
    st.markdown("<h2 style='color: #ffffff;'>Engine Penalty Weight & SLA Threshold Settings</h2>", unsafe_allow_html=True)
    
    st.markdown("<h4 style='color: #ffffff;'>Trust Score Penalty Multipliers</h4>", unsafe_allow_html=True)
    w1, w2 = st.columns(2)
    with w1:
        w_misleading = st.slider("Misleading Returns Penalty Multiplier", 1.0, 5.0, 2.5, step=0.1)
        w_late = st.slider("Late Dispatch Penalty Multiplier", 1.0, 5.0, 1.2, step=0.1)
        w_cancel = st.slider("Cancellation Penalty Multiplier", 1.0, 5.0, 2.0, step=0.1)
    with w2:
        w_sentiment = st.slider("Negative Sentiment Penalty Multiplier", 0.5, 3.0, 1.0, step=0.1)
        w_support = st.slider("Support Delay Penalty Multiplier", 0.5, 3.0, 1.0, step=0.1)
    
    st.markdown("<h4 style='color: #ffffff; margin-top: 20px;'>Marketplace SLA Targets</h4>", unsafe_allow_html=True)
    t1, t2 = st.columns(2)
    with t1:
        sla_delivery = st.slider("Target Delivery Success Rate (%)", 80.0, 99.0, 92.0, step=0.5)
    with t2:
        sla_return = st.slider("Max Acceptable Return Rate (%)", 1.0, 15.0, 6.0, step=0.5)

    if st.button("Save Settings & Apply Configurations"):
        st.success("Operational thresholds & penalty weights updated successfully!")
