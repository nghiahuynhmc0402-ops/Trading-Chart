import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
import sqlite3
import os
from datetime import datetime, timedelta

# Thư viện chỉ báo kỹ thuật
from ta.trend import EMAIndicator, SMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

try:
    import pyvsmc as smc
    HAS_SMC = True
except ImportError:
    HAS_SMC = False

# ============================================================
# 1. CẤU HÌNH GIAO DIỆN & CSS (INSTITUTIONAL DARK UI)
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro | Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Nâng cấp toàn diện
st.markdown("""
    <style>
    /* Import Font chữ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    
    /* Nền tảng chính (Deep Slate) */
    .stApp { 
        background-color: #0F111A;
        background-image: radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), radial-gradient(at 50% 0%, hsla(225,39%,30%,0.1) 0, transparent 50%);
        color: #E2E8F0 !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar (Tối giản, viền mỏng) */
    [data-testid="stSidebar"] { 
        background-color: #151A27 !important;
        border-right: 1px solid #1E293B;
    }
    
    /* Menu Điều Hướng (Navigation Pills) */
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 6px !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 12px 16px !important; 
        background-color: transparent !important; 
        border: 1px solid transparent !important;
        border-radius: 8px !important; 
        cursor: pointer !important; 
        transition: all 0.2s ease !important;
        width: 100% !important; 
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { 
        background-color: #1E293B !important; 
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] { 
        background-color: #1E293B !important;
        border-left: 3px solid #3B82F6 !important;
        border-radius: 4px 8px 8px 4px !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p { 
        font-size: 14px !important; 
        font-weight: 500 !important; 
        color: #94A3B8 !important; 
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p { 
        color: #F8FAFC !important; 
        font-weight: 600 !important;
    }
    
    /* Input / Selectbox */
    .stSelectbox div[data-baseweb="select"] { 
        background-color: #0F111A !important; 
        border: 1px solid #334155 !important; 
        border-radius: 6px !important; 
    }
    .stSelectbox div[data-baseweb="select"]:hover { border-color: #3B82F6 !important; }
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background-color: #0F111A !important;
        color: #E2E8F0 !important;
        border: 1px solid #334155 !important;
        border-radius: 6px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 1px #3B82F6 !important;
    }
    
    /* Nút bấm */
    .stButton>button { 
        width: 100%; 
        border-radius: 6px; 
        background: #3B82F6;
        color: white; 
        border: none; 
        font-weight: 500; 
        padding: 10px; 
        transition: all 0.2s ease;
    }
    .stButton>button:hover { 
        background: #2563EB;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
    }
    
    /* Typography */
    .stMetricValue, [data-testid="stMetricValue"] { 
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 24px !important; 
        font-weight: 600 !important; 
    }
    
    /* Bảng dữ liệu */
    [data-testid="stDataFrame"] { 
        border-radius: 8px; 
        border: 1px solid #1E293B; 
        overflow: hidden;
    }
    
    /* Tiêu đề */
    h1, h2, h3 { color: #F8FAFC !important; font-weight: 600 !important; letter-spacing: -0.02em; }
    hr { border-color: #1E293B !important; }
    
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 2. KHỞI TẠO DATABASE (GIỮ NGUYÊN)
# ============================================================
DB_FILE = "trading_journal.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, asset TEXT, direction TEXT, result TEXT, reason TEXT, pnl REAL)''')
    conn.commit(); conn.close()

init_db()

def add_trade(date, asset, direction, result, reason, pnl):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO journal (date, asset, direction, result, reason, pnl) VALUES (?, ?, ?, ?, ?, ?)", (date, asset, direction, result, reason, pnl))
    conn.commit(); conn.close()

def get_trades():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM journal ORDER BY date DESC", conn)
    conn.close(); return df

# ============================================================
# 3. CÁC HÀM TIỆN ÍCH & UI COMPONENTS
# ============================================================
def format_vn_price(value) -> str:
    if pd.isna(value) or value is None: return "N/A"
    try: return f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except: return str(value)

def premium_copyable_metric(label, value_str, delta_text=None, is_positive=None):
    """Thẻ KPI phong cách hiện đại, viền mỏng, có nút Copy."""
    
    # Xác định màu sắc viền trái
    border_color = "#334155" # Mặc định
    text_color = "#E2E8F0"   # Mặc định
    delta_color = "#94A3B8"
    
    if is_positive is not None:
        border_color = "#10B981" if is_positive else "#F43F5E"
        text_color = "#10B981" if is_positive else "#F43F5E"
        delta_color = "#10B981" if is_positive else "#F43F5E"
        
    delta_html = ""
    if delta_text:
        if is_positive is None:
            delta_color = "#10B981" if ("+" in str(delta_text) or "LONG" in str(delta_text)) else ("#F43F5E" if ("-" in str(delta_text) or "SHORT" in str(delta_text)) else "#94A3B8")
        delta_html = f"<div style='color: {delta_color}; font-size: 12px; font-weight: 500; margin-top: 6px; display: flex; align-items: center; gap: 4px;'>{delta_text}</div>"
        
    html_code = f"""
    <div style="
        background-color: #151A27;
        padding: 16px 20px;
        border-radius: 8px;
        border: 1px solid #1E293B;
        border-left: 3px solid {border_color};
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        font-family: 'Inter', sans-serif;
        position: relative;
        min-height: 105px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    ">
        <div style="color: #94A3B8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">{label}</div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: {text_color if is_positive is not None else '#F8FAFC'}; font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 600; line-height: 1;">{value_str}</span>
            <button onclick="navigator.clipboard.writeText('{value_str}'); this.innerHTML='<svg width=\\'16\\' height=\\'16\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'#10B981\\' stroke-width=\\'2\\' stroke-linecap=\\'round\\' stroke-linejoin=\\'round\\'><polyline points=\\'20 6 9 17 4 12\\'></polyline></svg>'; setTimeout(() => this.innerHTML='<svg width=\\'16\\' height=\\'16\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'#64748B\\' stroke-width=\\'2\\' stroke-linecap=\\'round\\' stroke-linejoin=\\'round\\'><rect x=\\'9\\' y=\\'9\\' width=\\'13\\' height=\\'13\\' rx=\\'2\\' ry=\\'2\\'></rect><path d=\\'M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1\\'></path></svg>', 2000);"
                    style="background: transparent; border: none; cursor: pointer; padding: 4px; display: flex; align-items: center; justify-content: center; transition: 0.2s; opacity: 0.7;"
                    onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'"
                    title="Copy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            </button>
        </div>
        {delta_html}
    </div>
    """
    components.html(html_code, height=115)

# ============================================================
# 4. DỮ LIỆU & TÍNH TOÁN (GIỮ NGUYÊN)
# ============================================================
POPULAR_ASSETS = {
    "🔥 Hàng Hóa": {"Vàng (XAUUSD)": "GC=F", "Bạc (XAGUSD)": "SI=F", "Dầu WTI": "CL=F"},
    "₿ Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD"},
    "💵 Forex": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"},
    "🏦 Chỉ Số & CK Mỹ": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "Apple (AAPL)": "AAPL", "Tesla (TSLA)": "TSLA"}
}
flat_assets = {f"{cat} - {name}": tick for cat, assets in POPULAR_ASSETS.items() for name, tick in assets.items()}

@st.cache_data(ttl=300, show_spinner="⏳ Đang kết nối luồng dữ liệu...")
def load_data(ticker: str, interval: str):
    period = "1y"
    if interval in ["1m", "5m", "15m", "60m"]: period = "1mo"
    elif interval in ["1d", "1wk"]: period = "2y"
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        time_col = "Datetime" if "Datetime" in df.columns else "Date"
        df.rename(columns={time_col: "Time"}, inplace=True)
        df["Time"] = pd.to_datetime(df["Time"])
        return df.dropna(subset=["Close"])
    except: return None

@st.cache_data(ttl=600, show_spinner="📰 Đang trích xuất tin tức...")
def fetch_news(ticker_name: str):
    search_query = ticker_name.replace(" ", "+")
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={search_query}&region=US&lang=en-US"
    feed = feedparser.parse(url)
    return [{"title": e.title, "link": e.link, "published": e.get("published", "N/A")} for e in feed.entries[:5]]

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close, high, low = df["Close"], df["High"], df["Low"]
    df["EMA20"] = EMAIndicator(close=close, window=20).ema_indicator()
    df["EMA50"] = EMAIndicator(close=close, window=50).ema_indicator()
    df["SMA200"] = SMAIndicator(close=close, window=200).sma_indicator()
    df["RSI"] = RSIIndicator(close=close, window=14).rsi()
    macd = MACD(close=close)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()
    bb = BollingerBands(close=close, window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
    df["ATR"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    df["ADX"] = ADXIndicator(high=high, low=low, close=close, window=14).adx()
    return df

def calculate_trade_levels(df: pd.DataFrame, risk_reward: float = 2.0) -> dict:
    if len(df) < 20: return None
    last = df.iloc[-1]
    atr = last["ATR"]
    recent_df = df.tail(20)
    recent_high = recent_df["High"].max()
    recent_low = recent_df["Low"].min()
    trend_bullish = last["EMA20"] > last["EMA50"]
    
    if trend_bullish:
        entry, sl, direction = last["Close"], recent_low - (atr * 0.5), "LONG"
        tp = entry + (entry - sl) * risk_reward
    else:
        entry, sl, direction = last["Close"], recent_high + (atr * 0.5), "SHORT"
        tp = entry - (sl - entry) * risk_reward
        
    return {"direction": direction, "entry": entry, "sl": sl, "tp": tp}

# ============================================================
# 5. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
        <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 24px; margin-top: 10px;'>
            <div style='background: #3B82F6; padding: 8px; border-radius: 8px; display: flex; align-items: center; justify-content: center;'>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>
            </div>
            <div>
                <h2 style='margin: 0; font-size: 18px; line-height: 1.2; color: #F8FAFC;'>TradeDesk <span style='color: #3B82F6;'>Pro</span></h2>
                <p style='margin: 0; color: #64748B; font-size: 10px; letter-spacing: 1.5px; font-weight: 600;'>TERMINAL</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='color: #64748B; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 6px;'>TÀI SẢN</p>", unsafe_allow_html=True)
    selected_asset = st.selectbox("Asset", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    st.markdown("<p style='color: #64748B; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 6px; margin-top: 15px;'>KHUNG THỜI GIAN</p>", unsafe_allow_html=True)
    timeframe = st.selectbox("TF", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval_map = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}
    interval = interval_map[timeframe]
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    if st.button("Đồng bộ dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
    
    st.markdown("<p style='color: #64748B; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 6px;'>HỆ THỐNG PHÂN TÍCH</p>", unsafe_allow_html=True)
    menu_selection = st.radio(
        "Menu",
        [
            "📊 Biểu Đồ Kỹ Thuật",
            "🎯 Kế Hoạch Giao Dịch",
            "🧠 Cấu Trúc Thị Trường",
            "📰 Tin Tức & Sự Kiện",
            "📓 Nhật Ký Giao Dịch"
        ],
        label_visibility="collapsed"
    )

# ============================================================
# 6. MAIN AREA
# ============================================================
df = load_data(ticker, interval)

if df is None or len(df) < 50:
    st.error(f"❌ Không lấy được dữ liệu cho **{selected_asset}**.")
    st.stop()

with st.spinner("⚙️ Đang xử lý thuật toán..."):
    df = compute_indicators(df)
    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_close
    change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

# HEADER KPI
col_header, col_status = st.columns([3, 1])
with col_header:
    st.markdown(f"""
        <div style='margin-bottom: 20px;'>
            <h1 style='margin: 0; font-size: 26px; color: #F8FAFC; font-weight: 700;'>{selected_asset.split(' - ')[1]}</h1>
            <p style='margin: 0; color: #64748B; font-family: "JetBrains Mono", monospace; font-size: 14px;'>{ticker} • {timeframe}</p>
        </div>
    """, unsafe_allow_html=True)
with col_status:
    st.markdown("""
        <div style='display: flex; justify-content: flex-end; align-items: center; height: 100%;'>
            <div style='background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); padding: 6px 12px; border-radius: 20px; display: flex; align-items: center; gap: 8px;'>
                <div style='width: 8px; height: 8px; background-color: #10B981; border-radius: 50%; box-shadow: 0 0 8px #10B981;'></div>
                <span style='color: #10B981; font-size: 12px; font-weight: 600;'>Live Market</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: premium_copyable_metric("Giá Hiện Tại", format_vn_price(last_close), f"{change_pct:+.2f}%", is_positive=(change_pct >= 0))
with kpi2: premium_copyable_metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}", "Quá mua" if df['RSI'].iloc[-1]>70 else ("Quá bán" if df['RSI'].iloc[-1]<30 else "Trung tính"), is_positive=(df['RSI'].iloc[-1]<70))
with kpi3: premium_copyable_metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}", "Xu hướng mạnh" if df['ADX'].iloc[-1]>25 else "Đi ngang", is_positive=None)
with kpi4: premium_copyable_metric("ATR (14)", format_vn_price(df['ATR'].iloc[-1]), "Biến động", is_positive=None)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 1: BIỂU ĐỒ
# ------------------------------------------------------------
if menu_selection == "📊 Biểu Đồ Kỹ Thuật":
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI (14)", "MACD (12, 26, 9)"))
    
    # Sử dụng màu Xanh lá mạ (Emerald) và Đỏ san hô (Rose) cho nến
    fig.add_trace(go.Candlestick(
        x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Giá", 
        increasing_line_color="#10B981", decreasing_line_color="#F43F5E",
        increasing_fillcolor="#10B981", decreasing_fillcolor="#F43F5E"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA 20", line=dict(color="#60A5FA", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA 50", line=dict(color="#A78BFA", width=1.5)), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#38BDF8")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#F43F5E", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#10B981", row=2, col=1)
    
    fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="Histogram", marker_color=["#10B981" if v >= 0 else "#F43F5E" for v in df["MACD_hist"]]), row=3, col=1)
    
    # Cấu hình nền trong suốt hòa vào UI
    fig.update_layout(
        template="plotly_dark", 
        height=750, 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)", 
        hovermode="x unified", 
        showlegend=False, 
        margin=dict(l=10, r=50, t=30, b=10), 
        dragmode="pan"
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1E293B", rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="#1E293B", side="right", tickfont=dict(family="JetBrains Mono, monospace", color="#64748B"))
    
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "🎯 Kế Hoạch Giao Dịch":
    st.subheader("Thiết Lập Vị Thế")
    
    col_slider, _ = st.columns([1, 2])
    with col_slider: 
        rr_ratio = st.slider("Tỷ lệ Risk:Reward", 1.0, 4.0, 2.0, 0.5)
        
    trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
    if trade_plan:
        direction_color = "#10B981" if trade_plan['direction'] == "LONG" else "#F43F5E"
        direction_bg = "rgba(16, 185, 129, 0.1)" if trade_plan['direction'] == "LONG" else "rgba(244, 63, 94, 0.1)"
        
        st.markdown(f"""
            <div style='background: {direction_bg}; border: 1px solid {direction_color}; padding: 15px; border-radius: 8px; margin-top: 10px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;'>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{direction_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
                <h3 style='color: {direction_color}; margin: 0;'>Hướng Khuyến Nghị: {trade_plan['direction']}</h3>
            </div>
        """, unsafe_allow_html=True)
        
        col_entry, col_sl, col_tp = st.columns(3)
        with col_entry: premium_copyable_metric("Entry (Vào lệnh)", format_vn_price(trade_plan['entry']), "Giá hiện tại", is_positive=None)
        with col_sl: premium_copyable_metric("Stop-Loss (Cắt lỗ)", format_vn_price(trade_plan['sl']), "Bảo vệ vốn", is_positive=False)
        with col_tp: premium_copyable_metric("Take-Profit (Chốt lời)", format_vn_price(trade_plan['tp']), "Mục tiêu lợi nhuận", is_positive=True)

# ------------------------------------------------------------
# KHU VỰC 3: SMC
# ------------------------------------------------------------
elif menu_selection == "🧠 Cấu Trúc Thị Trường":
    st.subheader("Phân Tích Cấu Trúc (SMC)")
    st.info("Hệ thống đang phân tích dòng tiền thông minh...")

# ------------------------------------------------------------
# KHU VỰC 4: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 Tin Tức & Sự Kiện":
    st.subheader(f"Tin Tức: {selected_asset.split(' - ')[1]}")
    news = fetch_news(ticker)
    
    for item in news:
        st.markdown(f"""
            <div style='background: #151A27; padding: 16px; border-radius: 8px; border: 1px solid #1E293B; border-left: 3px solid #3B82F6; margin-bottom: 12px; transition: transform 0.2s;'>
                <div style='color: #F8FAFC; font-weight: 500; font-size: 15px; margin-bottom: 8px; line-height: 1.4;'>
                    <a href='{item['link']}' target='_blank' style='color: #F8FAFC; text-decoration: none;' onmouseover="this.style.color='#60A5FA'" onmouseout="this.style.color='#F8FAFC'">{item['title']}</a>
                </div>
                <div style='color: #64748B; font-size: 12px; display: flex; align-items: center; gap: 6px; font-family: "JetBrains Mono", monospace;'>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    {item['published']}
                </div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 5: NHẬT KÝ GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "📓 Nhật Ký Giao Dịch":
    st.subheader("Nhật Ký Giao Dịch")
    
    col_form, col_history = st.columns([1, 2], gap="large")
    
    with col_form:
        st.markdown("<div style='background: #151A27; padding: 20px; border-radius: 8px; border: 1px solid #1E293B;'>", unsafe_allow_html=True)
        with st.form("journal_form", clear_on_submit=True):
            st.markdown("<p style='font-weight:600; color:#F8FAFC; font-size: 16px; margin-bottom: 15px;'>➕ Ghi Lệnh Mới</p>", unsafe_allow_html=True)
            trade_date = st.date_input("Ngày", datetime.today())
            asset_name = st.text_input("Tài sản", value=selected_asset.split(' - ')[1])
            direction = st.selectbox("Hướng", ["LONG", "SHORT"])
            result = st.selectbox("Kết quả", ["WIN", "LOSS", "HÒA"])
            pnl_val = st.number_input("PnL (% hoặc $)", value=0.0, step=0.1)
            reason = st.text_area("Lý do", placeholder="Ghi chú kỷ luật...")
            
            submitted = st.form_submit_button("Lưu Lệnh")
            if submitted:
                add_trade(str(trade_date), asset_name.upper(), direction, result, reason, pnl_val)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
                
        # Backup tools
        journal_df = get_trades()
        if not journal_df.empty:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            csv = journal_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Tải file Backup (CSV)", data=csv, file_name="journal.csv", mime="text/csv", use_container_width=True)

    with col_history:
        if journal_df.empty:
            st.info("Chưa có dữ liệu giao dịch.")
        else:
            journal_df['date'] = pd.to_datetime(journal_df['date'], errors='coerce')
            journal_df['pnl'] = pd.to_numeric(journal_df['pnl'], errors='coerce')
            
            total_trades = len(journal_df)
            wins = len(journal_df[journal_df['result'] == 'WIN'])
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = journal_df['pnl'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng Lệnh", total_trades)
            c2.metric("Tỷ Lệ Thắng", f"{win_rate:.1f}%")
            c3.metric("Tổng PnL", f"{total_pnl:+.2f}", delta_color="normal" if total_pnl >=0 else "inverse")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_filter1, col_filter2 = st.columns(2)
            years = journal_df['date'].dt.year.dropna().unique()
            if len(years) > 0:
                selected_year = col_filter1.selectbox("Năm", sorted(years, reverse=True))
                months = journal_df[journal_df['date'].dt.year == selected_year]['date'].dt.month.dropna().unique()
                selected_month = col_filter2.selectbox("Tháng", sorted(months, reverse=True))
                
                filtered_df = journal_df[(journal_df['date'].dt.year == selected_year) & (journal_df['date'].dt.month == selected_month)].copy()
                filtered_df['date'] = filtered_df['date'].dt.strftime('%d/%m/%Y')
                
                def color_result(val):
                    if val == 'WIN': return 'color: #10B981; font-weight: 600;'
                    elif val == 'LOSS': return 'color: #F43F5E; font-weight: 600;'
                    return 'color: #94A3B8;'
                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #10B981;'
                        elif val < 0: return 'color: #F43F5E;'
                    except: pass
                    return 'color: #94A3B8;'

                styled_df = filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style \
                    .map(color_result, subset=['result']) \
                    .map(color_pnl, subset=['pnl'])
                
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
