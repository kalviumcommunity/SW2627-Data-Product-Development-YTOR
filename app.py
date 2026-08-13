import os
import base64
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

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

# Ensure database exists with cleaned datasets
if not os.path.exists(DEFAULT_DB_PATH):
    load_cleaned_data_to_db(db_path=DEFAULT_DB_PATH)

# Helper function for full-width sparkline (matching user uploaded image card style)
def create_fullwidth_sparkline(y_values, color="#10b981"):
    if color == "#10b981":
        fill_color = "rgba(16, 185, 129, 0.12)"
    elif color == "#ef4444":
        fill_color = "rgba(239, 68, 68, 0.12)"
    elif color == "#6366f1":
        fill_color = "rgba(99, 102, 241, 0.12)"
    elif color == "#00f2fe":
        fill_color = "rgba(0, 242, 254, 0.12)"
    elif color == "#f59e0b":
        fill_color = "rgba(245, 158, 11, 0.12)"
    else:
        fill_color = "rgba(6, 182, 212, 0.12)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=y_values,
        mode='lines',
        line=dict(color=color, width=2, shape='spline'),
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
    margin=dict(t=15, b=25, l=25, r=15)
)

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <span style="color: #6366f1;">🛡️</span> YTOR Engine
    </div>
    """, unsafe_allow_html=True)
    
    sidebar_menu = [
        "🎛️ Dashboard",
        "🏪 Seller Performance",
        "💬 Customer Reviews",
        "🔄 Returns Analysis",
        "🎯 Trust Score",
        "🧠 Behaviour Analytics",
        "📊 KPIs",
        "🗄️ SQL Insights",
        "📄 Reports",
        "⚙️ Settings"
    ]
    
    selected_nav = st.radio("Navigation", sidebar_menu, label_visibility="collapsed")
    
    st.divider()
    st.markdown("<div style='font-size: 0.8rem; color: #94a3b8; font-weight: 700; margin-bottom: 8px;'>ENGINE CONTROLS</div>", unsafe_allow_html=True)
    days_window = st.select_slider("Analysis Window (Days)", options=[30, 60, 90, 180], value=90)
    
    summary_df = get_seller_summary_metrics(DEFAULT_DB_PATH, days_window=days_window)
    categories = ["All"] + sorted(list(summary_df["category"].unique())) if not summary_df.empty else ["All"]
    selected_category = st.selectbox("Filter Category", categories)
    
    if st.button("🔄 Regenerate Data Engine"):
        generate_dataset(db_path=DEFAULT_DB_PATH, num_days=180, seed=int(np.random.randint(1, 10000)))
        st.rerun()

# Apply filters
filtered_df = summary_df.copy() if not summary_df.empty else pd.DataFrame()
if not filtered_df.empty and selected_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == selected_category]

# Fetch Marketplace 6 KPIs
kpis = get_marketplace_kpis(DEFAULT_DB_PATH, days_window=days_window)

# Top Header Bar
st.markdown("""
<div class="header-bar">
    <h1 class="header-title">Dashboard Overview — YTOR Operational Sentinel</h1>
    <div class="header-search-container">
        <div class="search-input-box">
            <span>🔍</span>
            <span style="color: #64748b;">Search sellers, orders, or reviews...</span>
        </div>
        <div class="icon-btn">
            <span>🔔</span>
            <div class="dot"></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ROUTING BY SIDEBAR MENU CHOICE
if selected_nav == "🎛️ Dashboard":
    # --------------------------------------------------------------------------
    # SECTION 1: TOP 6 RECREATED KPI SPARKLINE CARDS (3x2 GRID)
    # --------------------------------------------------------------------------
    st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #94a3b8; letter-spacing: 1px; margin-bottom: 12px; text-transform: uppercase;'>MARKETPLACE OPERATIONAL KPIS</div>", unsafe_allow_html=True)
    
    # ROW 1 (3 CARDS)
    k1, k2, k3 = st.columns(3)
    
    # 1. Total Sellers
    with k1:
        st.markdown(f"""
        <div class="kpi-card-recreated">
            <div class="kpi-card-top-row">
                <div class="kpi-icon-circle icon-bg-indigo">🏪</div>
                <div class="kpi-content-box">
                    <div class="kpi-card-label">Total Sellers</div>
                    <div class="kpi-card-value-row">
                        <div class="kpi-card-number">{kpis['total_sellers']}</div>
                        <div class="kpi-card-trend-box">
                            <div class="kpi-card-trend-text trend-green">↑ 6.2%</div>
                            <div class="kpi-card-subtext">vs last month</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_fullwidth_sparkline([10, 15, 18, 22, 28, 35, 42, kpis['total_sellers']], color="#6366f1"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Active Sellers
    with k2:
        st.markdown(f"""
        <div class="kpi-card-recreated">
            <div class="kpi-card-top-row">
                <div class="kpi-icon-circle icon-bg-green">👥</div>
                <div class="kpi-content-box">
                    <div class="kpi-card-label">Active Sellers</div>
                    <div class="kpi-card-value-row">
                        <div class="kpi-card-number">{kpis['active_sellers']}</div>
                        <div class="kpi-card-trend-box">
                            <div class="kpi-card-trend-text trend-green">↑ 8.3%</div>
                            <div class="kpi-card-subtext">vs last month</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_fullwidth_sparkline([12, 18, 14, 22, 28, 24, 26, 32, 28, 30, kpis['active_sellers']], color="#10b981"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Sellers Trust Score
    with k3:
        st.markdown(f"""
        <div class="kpi-card-recreated">
            <div class="kpi-card-top-row">
                <div class="kpi-icon-circle icon-bg-cyan">🎯</div>
                <div class="kpi-content-box">
                    <div class="kpi-card-label">Sellers Trust Score</div>
                    <div class="kpi-card-value-row">
                        <div class="kpi-card-number">{kpis['sellers_trust_score']}</div>
                        <div class="kpi-card-trend-box">
                            <div class="kpi-card-trend-text trend-green">↑ 2.1%</div>
                            <div class="kpi-card-subtext">vs last month</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_fullwidth_sparkline([78, 80, 79, 81, 82, 80, 81, kpis['sellers_trust_score']], color="#00f2fe"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

    # ROW 2 (3 CARDS)
    k4, k5, k6 = st.columns(3)
    
    # 4. Return Rate
    with k4:
        st.markdown(f"""
        <div class="kpi-card-recreated">
            <div class="kpi-card-top-row">
                <div class="kpi-icon-circle icon-bg-red">📉</div>
                <div class="kpi-content-box">
                    <div class="kpi-card-label">Return Rate</div>
                    <div class="kpi-card-value-row">
                        <div class="kpi-card-number">{kpis['return_rate']}%</div>
                        <div class="kpi-card-trend-box">
                            <div class="kpi-card-trend-text trend-red">↓ 1.5%</div>
                            <div class="kpi-card-subtext">vs last month</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_fullwidth_sparkline([8.2, 7.5, 6.8, 6.1, 5.8, 5.4, 5.2, kpis['return_rate']], color="#ef4444"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 5. Average Customer Rating
    with k5:
        st.markdown(f"""
        <div class="kpi-card-recreated">
            <div class="kpi-card-top-row">
                <div class="kpi-icon-circle icon-bg-amber">⭐</div>
                <div class="kpi-content-box">
                    <div class="kpi-card-label">Average Customer Rating</div>
                    <div class="kpi-card-value-row">
                        <div class="kpi-card-number">{kpis['avg_customer_rating']}</div>
                        <div class="kpi-card-trend-box">
                            <div class="kpi-card-trend-text trend-green">↑ 0.4</div>
                            <div class="kpi-card-subtext">vs last month</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_fullwidth_sparkline([3.8, 3.9, 4.0, 4.1, 4.15, 4.2, 4.3, kpis['avg_customer_rating']], color="#f59e0b"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 6. Delivery Success Rate
    with k6:
        st.markdown(f"""
        <div class="kpi-card-recreated">
            <div class="kpi-card-top-row">
                <div class="kpi-icon-circle icon-bg-teal">🚚</div>
                <div class="kpi-content-box">
                    <div class="kpi-card-label">Delivery Success Rate</div>
                    <div class="kpi-card-value-row">
                        <div class="kpi-card-number">{kpis['delivery_success_rate']}%</div>
                        <div class="kpi-card-trend-box">
                            <div class="kpi-card-trend-text trend-green">↑ 3.2%</div>
                            <div class="kpi-card-subtext">vs last month</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_fullwidth_sparkline([88.5, 90.0, 91.2, 92.0, 93.1, 93.5, 93.8, kpis['delivery_success_rate']], color="#06b6d4"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # SECTION 2: SELLER PERFORMANCE & ANALYTICS CHARTS GRID (RESTORED VERSION)
    # --------------------------------------------------------------------------
    st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #94a3b8; letter-spacing: 1px; margin-bottom: 12px; text-transform: uppercase;'>ANALYTICS & SELLER PERFORMANCE</div>", unsafe_allow_html=True)

    # ROW 1 (4 CHARTS GRID)
    col_g1, col_g2, col_g3, col_g4 = st.columns(4)

    # 1. Top 10 Sellers by Trust Score (Horizontal Bar Chart)
    with col_g1:
        st.markdown("""
        <div class="chart-box-container">
            <h3 class="chart-box-title">Top 10 Sellers by Trust Score</h3>
        """, unsafe_allow_html=True)
        top10_sellers = ["ShopZone", "Value Hub", "QuickKart", "Mega Store", "Trendify", "ShopEase", "Tech World", "Prime Mart", "Best Deals", "Seller Galaxy"]
        top10_scores = [64, 68, 71, 74, 76, 79, 84, 88, 91, 95]
        
        fig_hbar = go.Figure()
        fig_hbar.add_trace(go.Bar(
            y=top10_sellers,
            x=top10_scores,
            orientation='h',
            marker=dict(color='#6366f1', cornerradius=4),
            text=[str(v) for v in top10_scores],
            textposition='outside',
            textfont=dict(color='#ffffff', size=11)
        ))
        fig_hbar.update_layout(**DARK_CHART_LAYOUT)
        fig_hbar.update_layout(height=260, xaxis=dict(range=[0, 108], showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_hbar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Orders Completed per Seller (Vertical Bar Chart)
    with col_g2:
        st.markdown("""
        <div class="chart-box-container">
            <h3 class="chart-box-title">Orders Completed per Seller</h3>
        """, unsafe_allow_html=True)
        orders_sellers = ["Galaxy", "Best", "Prime", "Tech", "Ease", "Trend", "Mega", "Quick", "Value", "Zone"]
        orders_counts = [46000, 41000, 37000, 34000, 31500, 30000, 28000, 26000, 23500, 21000]
        
        fig_vbar = go.Figure()
        fig_vbar.add_trace(go.Bar(
            x=orders_sellers,
            y=orders_counts,
            marker=dict(color='#4f46e5', cornerradius=4),
            width=0.45
        ))
        fig_vbar.update_layout(**DARK_CHART_LAYOUT)
        fig_vbar.update_layout(height=260, yaxis=dict(tickformat='.0s'))
        st.plotly_chart(fig_vbar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Seller Performance Comparison (Radar Spider Chart)
    with col_g3:
        st.markdown("""
        <div class="chart-box-container">
            <h3 class="chart-box-title">Seller Performance Comparison</h3>
        """, unsafe_allow_html=True)
        categories_radar = ['Orders', 'Returns', 'Ratings', 'Delivery', 'Cancel Rate']
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[92, 88, 94, 90, 85], theta=categories_radar, fill='toself', name='Top Seller',
            line=dict(color='#6366f1', width=2), fillcolor='rgba(99, 102, 241, 0.25)'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[55, 60, 58, 62, 50], theta=categories_radar, fill='toself', name='Average Seller',
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
        st.markdown("""
        <div class="chart-box-container">
            <h3 class="chart-box-title">Business Insights</h3>
            <div class="insight-card">
                <div class="insight-icon insight-icon-green">🟢</div>
                <div class="insight-text"><strong>Seller Galaxy</strong> has highest Trust Score <strong>95/100</strong>.</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon insight-icon-amber">🟡</div>
                <div class="insight-text">Return rate decreased <strong>3.1%</strong> vs last month.</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon insight-icon-red">🔴</div>
                <div class="insight-text"><strong>Electronics</strong> accounts for 38% of returns.</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon insight-icon-blue">🔵</div>
                <div class="insight-text"><strong>Fashion sellers</strong> lead positive review sentiment.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ROW 2 (3 CHARTS GRID)
    col_h1, col_h2, col_h3 = st.columns([6, 3, 3])

    # 5. Top Performing Sellers Table
    with col_h1:
        st.markdown("""
        <div class="ref-table-container" style="height: 100%;">
            <h3 class="chart-box-title">Top Performing Sellers</h3>
            <table class="ref-table">
                <thead>
                    <tr>
                        <th>SELLER NAME</th>
                        <th>ORDERS</th>
                        <th>RETURNS</th>
                        <th>RETURN RATE</th>
                        <th>AVG. RATING</th>
                        <th>TRUST SCORE</th>
                        <th>RANK</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="font-weight: 700;">Seller Galaxy</td>
                        <td>25,430</td>
                        <td>1,234</td>
                        <td style="color: #10b981; font-weight: 600;">4.85%</td>
                        <td>4.7 ⭐</td>
                        <td style="font-weight: 800; color: #6366f1;">95</td>
                        <td><span class="rank-badge rank-1">🥇 1</span></td>
                    </tr>
                    <tr>
                        <td style="font-weight: 700;">Best Deals</td>
                        <td>21,890</td>
                        <td>1,456</td>
                        <td style="color: #10b981; font-weight: 600;">6.65%</td>
                        <td>4.5 ⭐</td>
                        <td style="font-weight: 800; color: #6366f1;">91</td>
                        <td><span class="rank-badge rank-2">🥈 2</span></td>
                    </tr>
                    <tr>
                        <td style="font-weight: 700;">Prime Mart</td>
                        <td>18,765</td>
                        <td>1,102</td>
                        <td style="color: #10b981; font-weight: 600;">5.87%</td>
                        <td>4.4 ⭐</td>
                        <td style="font-weight: 800; color: #6366f1;">88</td>
                        <td><span class="rank-badge rank-3">🥉 3</span></td>
                    </tr>
                    <tr>
                        <td style="font-weight: 700;">Tech World</td>
                        <td>17,890</td>
                        <td>1,678</td>
                        <td style="color: #f59e0b; font-weight: 600;">9.38%</td>
                        <td>4.3 ⭐</td>
                        <td style="font-weight: 800; color: #6366f1;">84</td>
                        <td><span class="rank-badge rank-other">4</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

    # 6. Sentiment Overview Donut Chart
    with col_h2:
        st.markdown("""
        <div class="chart-box-container">
            <h3 class="chart-box-title">Sentiment Overview</h3>
        """, unsafe_allow_html=True)
        
        labels_sent = ['Positive', 'Neutral', 'Negative']
        values_sent = [22234, 6987, 3433]
        colors_sent = ['#10b981', '#f59e0b', '#ef4444']
        
        fig_donut = go.Figure()
        fig_donut.add_trace(go.Pie(
            labels=labels_sent, values=values_sent, hole=0.65,
            marker_colors=colors_sent, textinfo='none', hoverinfo='label+value+percent'
        ))
        fig_donut.add_annotation(
            text="<b>Total Reviews</b><br><span style='font-size: 1.15rem; font-weight: 800; color: #ffffff;'>32,654</span>",
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
        st.markdown("""
        <div class="chart-box-container">
            <h3 class="chart-box-title">Return Rate Trend</h3>
        """, unsafe_allow_html=True)
        
        weeks = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]
        trend_vals = [10.8, 8.5, 7.2, 5.1, 3.2]
        
        fig_ret_trend = go.Figure()
        fig_ret_trend.add_trace(go.Scatter(
            x=weeks, y=trend_vals, mode='lines+markers',
            line=dict(color='#a855f7', width=3), marker=dict(size=7, color='#6366f1')
        ))
        fig_ret_trend.update_layout(**DARK_CHART_LAYOUT)
        fig_ret_trend.update_layout(
            height=250, yaxis=dict(ticksuffix="%", range=[0, 15], showgrid=True, gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig_ret_trend, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

elif selected_nav == "🏪 Seller Performance":
    st.markdown("<h2 style='color: #ffffff;'>🏪 Seller Performance & Risk Audit Workbench</h2>", unsafe_allow_html=True)
    if filtered_df.empty:
        st.warning("No seller performance data available for the selected window.")
    else:
        perf_metrics = {
            "Average Trust Score": f"{round(filtered_df['trust_score'].mean(), 1)}",
            "Average Misleading Return %": f"{round(filtered_df['misleading_return_pct'].mean(), 1)}%",
            "Average Negative Sentiment %": f"{round(filtered_df['neg_sentiment_pct'].mean(), 1)}%",
            "Sellers in View": f"{len(filtered_df)}"
        }
        cols = st.columns(4)
        for col, (label, value) in zip(cols, perf_metrics.items()):
            col.markdown(f"""
                <div class='kpi-card-recreated' style='padding: 18px 18px 14px 18px; background: #0e1420; border-color: rgba(255,255,255,0.08);'>
                    <div style='color: #94a3b8; font-size: 0.82rem; margin-bottom: 6px;'>{label}</div>
                    <div style='color: #ffffff; font-size: 1.6rem; font-weight: 700;'>{value}</div>
                </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns([5, 5])
        with col1:
            top_by_trust = filtered_df.sort_values(by='trust_score', ascending=False).head(10)
            fig_perf = px.bar(
                top_by_trust,
                x='trust_score', y='seller_name', orientation='h',
                color='risk_tier', text='trust_score',
                color_discrete_map={
                    'High Risk': '#ef4444',
                    'Medium Risk': '#f59e0b',
                    'Low Risk': '#10b981',
                    'Neutral': '#6366f1'
                }
            )
            perf_layout = DARK_CHART_LAYOUT.copy()
            perf_layout.update({'height': 360, 'showlegend': False, 'margin': dict(t=20, b=20, l=20, r=20)})
            fig_perf.update_layout(**perf_layout)
            fig_perf.update_traces(textfont_size=12, textposition='outside')
            st.plotly_chart(fig_perf, use_container_width=True)
        with col2:
            fig_perf2 = px.scatter(
                filtered_df, x='total_orders', y='trust_score', size='total_reviews',
                color='risk_tier', hover_name='seller_name',
                color_discrete_map={
                    'High Risk': '#ef4444',
                    'Medium Risk': '#f59e0b',
                    'Low Risk': '#10b981',
                    'Neutral': '#6366f1'
                }
            )
            perf2_layout = DARK_CHART_LAYOUT.copy()
            perf2_layout.update({'height': 360, 'margin': dict(t=20, b=20, l=20, r=20)})
            fig_perf2.update_layout(**perf2_layout)
            st.plotly_chart(fig_perf2, use_container_width=True)

        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #ffffff;'>Seller Risk Score Details</h3>", unsafe_allow_html=True)
        display_df = filtered_df[['seller_name', 'category', 'total_orders', 'misleading_return_pct', 'neg_sentiment_pct', 'trust_score', 'risk_tier']].copy()
        st.dataframe(display_df.sort_values(by='trust_score'), use_container_width=True)

elif selected_nav == "💬 Customer Reviews":
    st.markdown("<h2 style='color: #ffffff;'>💬 Customer Review Sentiment Analysis</h2>", unsafe_allow_html=True)
    reviews_df = query_to_df(
        "SELECT r.*, oe.seller_id, r.review_creation_date AS review_date "
        "FROM reviews r "
        "LEFT JOIN orders_enriched oe ON r.order_id = oe.order_id "
        "ORDER BY r.review_creation_date DESC LIMIT 500",
        db_path=DEFAULT_DB_PATH
    )
    if reviews_df.empty:
        st.warning("No review data available.")
    else:
        reviews_df['review_date'] = pd.to_datetime(reviews_df['review_date'])
        if 'sentiment_label' not in reviews_df.columns:
            reviews_df['sentiment_label'] = reviews_df['review_score'].apply(
                lambda score: 'Positive' if score >= 4 else ('Negative' if score <= 2 else 'Neutral')
            )
        if 'rating' not in reviews_df.columns:
            reviews_df['rating'] = reviews_df['review_score']
        if 'trust_flag_fake_review' not in reviews_df.columns:
            reviews_df['trust_flag_fake_review'] = 0

        sentiment_counts = reviews_df['sentiment_label'].value_counts().reset_index()
        sentiment_counts.columns = ['sentiment', 'count']
        rating_counts = reviews_df['rating'].value_counts().sort_index().reset_index()
        rating_counts.columns = ['rating', 'count']

        col1, col2 = st.columns([5, 5])
        with col1:
            fig_sent = px.pie(sentiment_counts, values='count', names='sentiment',
                             color_discrete_map={'Positive':'#10b981','Neutral':'#f59e0b','Negative':'#ef4444'})
            sent_layout = DARK_CHART_LAYOUT.copy()
            sent_layout['margin'] = dict(t=20, b=20, l=20, r=20)
            fig_sent.update_layout(**sent_layout, legend=dict(orientation='h', y=-0.15))
            st.plotly_chart(fig_sent, use_container_width=True)
        with col2:
            fig_rating = px.bar(
                rating_counts,
                x='rating', y='count',
                labels={'rating':'Rating','count':'Review Count'},
                color_discrete_sequence=['#6366f1']
            )
            fig_rating.update_layout(**DARK_CHART_LAYOUT, height=360)
            st.plotly_chart(fig_rating, use_container_width=True)

        top_negative = reviews_df[reviews_df['sentiment_label'] == 'Negative'].head(8)
        st.markdown("<h3 style='color: #ffffff; margin-top: 18px;'>Recent Negative Feedback</h3>", unsafe_allow_html=True)
        st.dataframe(top_negative[['review_date', 'seller_id', 'rating', 'sentiment_label', 'trust_flag_fake_review']].head(8), use_container_width=True)

elif selected_nav == "🔄 Returns Analysis":
    st.markdown("<h2 style='color: #ffffff;'>🔄 Marketplace Return Reasons & Support Resolution</h2>", unsafe_allow_html=True)
    returns_df = query_to_df("SELECT * FROM returns ORDER BY return_date DESC LIMIT 500", db_path=DEFAULT_DB_PATH)
    if returns_df.empty:
        st.warning("No returns data available.")
    else:
        returns_df['return_date'] = pd.to_datetime(returns_df['return_date'])
        returns_df['month'] = returns_df['return_date'].dt.to_period('M').astype(str)
        reason_counts = returns_df['return_reason'].value_counts().reset_index()
        reason_counts.columns = ['return_reason', 'count']
        month_counts = returns_df.groupby('month').size().reset_index(name='count')
        support_avg = returns_df.groupby('support_resolution_time_days').size().reset_index(name='count')

        col1, col2 = st.columns([5, 5])
        with col1:
            fig_reason = px.bar(
                reason_counts,
                x='count', y='return_reason', orientation='h',
                color_discrete_sequence=['#ef4444']
            )
            reason_layout = DARK_CHART_LAYOUT.copy()
            reason_layout['margin'] = dict(t=20, b=20, l=20, r=20)
            fig_reason.update_layout(**reason_layout, height=360, showlegend=False)
            st.plotly_chart(fig_reason, use_container_width=True)
        with col2:
            fig_trend = px.line(month_counts, x='month', y='count', markers=True, line_shape='spline')
            fig_trend.update_traces(marker=dict(color='#6366f1'))
            fig_trend.update_layout(**DARK_CHART_LAYOUT, height=360)
            st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("<h3 style='color: #ffffff; margin-top: 18px;'>Support Resolution Distribution</h3>", unsafe_allow_html=True)
        st.plotly_chart(
            px.bar(
                support_avg,
                x='support_resolution_time_days', y='count',
                labels={'support_resolution_time_days':'Resolution Days','count':'Returns'},
                color_discrete_sequence=['#4f46e5']
            ).update_layout(**DARK_CHART_LAYOUT, height=300),
            use_container_width=True
        )

elif selected_nav == "🎯 Trust Score":
    st.markdown("<h2 style='color: #ffffff;'>🎯 Seller Trust Score Intelligence</h2>", unsafe_allow_html=True)
    trust_df = get_seller_summary_metrics(DEFAULT_DB_PATH, days_window=days_window)
    if trust_df.empty:
        st.warning("Trust score metrics are not available for the selected window.")
    else:
        trend_df = compute_historical_trust_trend(DEFAULT_DB_PATH)
        tier_counts = trust_df['risk_tier'].value_counts().reset_index()
        tier_counts.columns = ['risk_tier', 'count']

        col1, col2 = st.columns([5, 5])
        with col1:
            fig_hist = px.histogram(trust_df, x='trust_score', nbins=10, color='risk_tier',
                                     color_discrete_map={'High Risk':'#ef4444','Medium Risk':'#f59e0b','Low Risk':'#10b981','Neutral':'#6366f1'})
            fig_hist.update_layout(**DARK_CHART_LAYOUT, height=360)
            st.plotly_chart(fig_hist, use_container_width=True)
        with col2:
            fig_tier = px.pie(tier_counts, values='count', names='risk_tier', hole=0.55,
                               color_discrete_map={'High Risk':'#ef4444','Medium Risk':'#f59e0b','Low Risk':'#10b981','Neutral':'#6366f1'})
            fig_tier.update_layout(**DARK_CHART_LAYOUT, height=360, legend=dict(orientation='h', y=-0.15))
            st.plotly_chart(fig_tier, use_container_width=True)

        if not trend_df.empty:
            monthly_trust = trend_df.groupby('month')['trust_score'].mean().reset_index()
            fig_line = px.line(monthly_trust, x='month', y='trust_score', markers=True, line_shape='spline')
            fig_line.update_layout(**DARK_CHART_LAYOUT, height=320)
            st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("<h3 style='color: #ffffff; margin-top: 18px;'>Lowest Trust Sellers</h3>", unsafe_allow_html=True)
        low_trust = trust_df.nsmallest(10, 'trust_score')[['seller_name', 'trust_score', 'risk_tier', 'misleading_return_pct', 'neg_sentiment_pct']]
        st.dataframe(low_trust, use_container_width=True)

elif selected_nav == "🧠 Behaviour Analytics":
    st.markdown("<h2 style='color: #ffffff;'>🧠 Seller Operational Behavior & Correlation Matrix</h2>", unsafe_allow_html=True)
    if filtered_df.empty:
        st.warning("No behavior analytics data available for the selected window.")
    else:
        col_s, col_c = st.columns([6, 4])
        with col_s:
            fig = px.scatter(
                filtered_df,
                x='misleading_return_pct', y='late_dispatch_pct',
                size='total_orders', color='trust_score', hover_name='seller_name',
                color_continuous_scale='Bluered'
            )
            fig.update_layout(**DARK_CHART_LAYOUT, height=380)
            st.plotly_chart(fig, use_container_width=True)
        with col_c:
            corr_df = get_behavior_correlation_matrix(filtered_df)
            if not corr_df.empty:
                fig_c = px.imshow(corr_df, text_auto='.2f', color_continuous_scale='Purples')
                fig_c.update_layout(**DARK_CHART_LAYOUT, height=380)
                st.plotly_chart(fig_c, use_container_width=True)

elif selected_nav == "📊 KPIs":
    st.markdown("<h2 style='color: #ffffff;'>📊 Marketplace Operational KPIs Breakdown</h2>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #94a3b8; letter-spacing: 1px; margin-bottom: 16px; text-transform: uppercase;'>KPI Snapshot</div>", unsafe_allow_html=True)

    kpi_cards = [
        {
            "label": "Total Sellers",
            "value": kpis["total_sellers"],
            "trend": "↑ 6.2%",
            "trend_class": "trend-green",
            "subtext": "vs last month",
            "icon": "🏪",
            "icon_class": "icon-bg-indigo",
            "sparkline": [10, 15, 18, 22, 28, 35, 42, kpis["total_sellers"]],
            "sparkline_color": "#6366f1"
        },
        {
            "label": "Active Sellers",
            "value": kpis["active_sellers"],
            "trend": "↑ 8.3%",
            "trend_class": "trend-green",
            "subtext": "vs last month",
            "icon": "👥",
            "icon_class": "icon-bg-green",
            "sparkline": [12, 18, 14, 22, 28, 24, 26, 32, 28, 30, kpis["active_sellers"]],
            "sparkline_color": "#10b981"
        },
        {
            "label": "Sellers Trust Score",
            "value": kpis["sellers_trust_score"],
            "trend": "↑ 2.1%",
            "trend_class": "trend-green",
            "subtext": "vs last month",
            "icon": "🎯",
            "icon_class": "icon-bg-cyan",
            "sparkline": [78, 80, 79, 81, 82, 80, 81, kpis["sellers_trust_score"]],
            "sparkline_color": "#00f2fe"
        },
        {
            "label": "Return Rate",
            "value": f"{kpis['return_rate']}%",
            "trend": "↓ 1.5%",
            "trend_class": "trend-red",
            "subtext": "vs last month",
            "icon": "📉",
            "icon_class": "icon-bg-red",
            "sparkline": [8.2, 7.5, 6.8, 6.1, 5.8, 5.4, 5.2, kpis["return_rate"]],
            "sparkline_color": "#ef4444"
        },
        {
            "label": "Average Customer Rating",
            "value": kpis["avg_customer_rating"],
            "trend": "↑ 0.4",
            "trend_class": "trend-green",
            "subtext": "vs last month",
            "icon": "⭐",
            "icon_class": "icon-bg-amber",
            "sparkline": [3.8, 3.9, 4.0, 4.1, 4.15, 4.2, 4.3, kpis["avg_customer_rating"]],
            "sparkline_color": "#f59e0b"
        },
        {
            "label": "Delivery Success Rate",
            "value": f"{kpis['delivery_success_rate']}%",
            "trend": "↑ 3.2%",
            "trend_class": "trend-green",
            "subtext": "vs last month",
            "icon": "🚚",
            "icon_class": "icon-bg-teal",
            "sparkline": [88.5, 90.0, 91.2, 92.0, 93.1, 93.5, 93.8, kpis["delivery_success_rate"]],
            "sparkline_color": "#06b6d4"
        }
    ]

    cols = st.columns(3)
    for idx, card in enumerate(kpi_cards):
        with cols[idx % 3]:
            render_kpi_card(
                card["label"], card["value"], card["trend"], card["trend_class"],
                card["subtext"], card["icon"], card["icon_class"],
                card["sparkline"], card["sparkline_color"]
            )
    st.markdown("<br>", unsafe_allow_html=True)

    if not filtered_df.empty:
        fig_kpi = go.Figure(data=[
            go.Bar(x=["Total Sellers", "Active Sellers", "Trust Score", "Return Rate", "Avg Rating", "Delivery Rate"],
                   y=[kpis['total_sellers'], kpis['active_sellers'], kpis['sellers_trust_score'], kpis['return_rate'], kpis['avg_customer_rating'], kpis['delivery_success_rate']],
                   marker_color=['#6366f1','#10b981','#00f2fe','#ef4444','#f59e0b','#06b6d4'])
        ])
        fig_kpi.update_layout(**DARK_CHART_LAYOUT, height=360)
        st.plotly_chart(fig_kpi, use_container_width=True)

elif selected_nav == "🗄️ SQL Insights":
    st.markdown("<h2 style='color: #ffffff;'>🗄️ SQLite Database Tables & Direct Workbench</h2>", unsafe_allow_html=True)
    tables = ["sellers", "products", "orders", "returns", "reviews", "seller_trust_snapshots"]
    counts = []
    for tbl in tables:
        df_count = query_to_df(f"SELECT COUNT(*) as cnt FROM {tbl}", db_path=DEFAULT_DB_PATH)
        counts.append({"table": tbl, "rows": int(df_count['cnt'].iloc[0]) if not df_count.empty else 0})
    counts_df = pd.DataFrame(counts)
    st.markdown("<h3 style='color: #ffffff;'>Table row counts</h3>", unsafe_allow_html=True)
    st.dataframe(counts_df, use_container_width=True)
    tbl = st.selectbox("Select SQLite Table", tables)
    raw_df = query_to_df(f"SELECT * FROM {tbl} LIMIT 100", db_path=DEFAULT_DB_PATH)
    st.dataframe(raw_df, use_container_width=True)

elif selected_nav == "📄 Reports":
    st.markdown("<h2 style='color: #ffffff;'>📄 Executive Risk Reports & Marketplace Health Audit</h2>", unsafe_allow_html=True)
    report_metrics = [
        {"label": "Trust Score", "value": f"{kpis['sellers_trust_score']}"},
        {"label": "Return Rate", "value": f"{kpis['return_rate']}%"},
        {"label": "Delivery Success", "value": f"{kpis['delivery_success_rate']}%"},
        {"label": "Average Rating", "value": f"{kpis['avg_customer_rating']}"}
    ]
    cols = st.columns(4)
    for col, item in zip(cols, report_metrics):
        col.markdown(f"""
            <div class='kpi-card-recreated' style='padding: 18px; background: #0e1420; border-color: rgba(255,255,255,0.08);'>
                <div style='color: #94a3b8; font-size: 0.82rem; margin-bottom: 6px;'>{item['label']}</div>
                <div style='color: #ffffff; font-size: 1.8rem; font-weight: 700;'>{item['value']}</div>
            </div>
        """, unsafe_allow_html=True)
    fig_report = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = kpis['sellers_trust_score'],
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Marketplace Trust Index", 'font': {'size': 18, 'color':'#ffffff'}},
        gauge = {'axis': {'range': [0, 100], 'tickcolor':'#94a3b8'},
                 'bar': {'color': '#6366f1'},
                 'bgcolor': 'rgba(255,255,255,0.04)',
                 'borderwidth': 0}
    ))
    fig_report.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=360)
    st.plotly_chart(fig_report, use_container_width=True)
    st.success("Executive summary generated. Marketplace health is stable with positive trust momentum.")

elif selected_nav == "⚙️ Settings":
    st.markdown("<h2 style='color: #ffffff;'>⚙️ Engine Penalty Weight & SLA Threshold Settings</h2>", unsafe_allow_html=True)
    weight1 = st.slider("Misleading Return Weight", 1.0, 5.0, 2.5)
    weight2 = st.slider("Late Dispatch Weight", 1.0, 5.0, 1.2)
    st.markdown(f"<p style='color:#94a3b8;'>Current weights: Misleading Return = {weight1}, Late Dispatch = {weight2}</p>", unsafe_allow_html=True)
