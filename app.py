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
# 1. CẤU HÌNH GIAO DIỆN & CSS (NEXT-GEN TERMINAL UI)
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Nâng cấp toàn diện
st.markdown("""
    <style>
    /* Import Font chữ hiện đại */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Nền tảng chính (Deep Space Dark) */
    .stApp { 
        background: radial-gradient(circle at 50% -20%, #1A2233, #0B0E14);
        color: #E6EDF3 !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar (Kính mờ) */
    [data-testid="stSidebar"] { 
        background: rgba(13, 17, 23, 0.7) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Làm đẹp Menu Điều Hướng (Navigation Pills) */
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 8px !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 12px 16px !important; 
        background-color: transparent !important; 
        border: 1px solid transparent !important;
        border-radius: 8px !important; 
        cursor: pointer !important; 
        transition: all 0.2s ease !important;
        width: 100% !important; 
        display: flex !important; 
        align-items: center !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { 
        background-color: rgba(255,255,255,0.05) !important; 
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] { 
        background: linear-gradient(90deg, rgba(41,98,255,0.15) 0%, rgba(41,98,255,0) 100%) !important;
        border-left: 3px solid #2962FF !important;
        border-radius: 0 8px 8px 0 !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p { 
        font-size: 15px !important; 
        font-weight: 600 !important; 
        color: #8B949E !important; 
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p { 
        color: #FFFFFF !important; 
    }
    
    /* Input / Selectbox (Viền mỏng, nền tối) */
    .stSelectbox div[data-baseweb="select"] { 
        background-color: #161B22 !important; 
        border: 1px solid #30363D !important; 
        border-radius: 8px !important; 
        color: #E6EDF3 !important;
    }
    .stSelectbox div[data-baseweb="select"]:hover { border-color: #58A6FF !important; }
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background-color: #161B22 !important;
        color: #E6EDF3 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
    }
    
    /* Nút bấm (Gradient hiện đại) */
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        background: linear-gradient(135deg, #2962FF, #0055FF);
        color: white; 
        border: none; 
        font-weight: 600; 
        padding: 10px; 
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(41, 98, 255, 0.3);
    }
    .stButton>button:hover { 
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(41, 98, 255, 0.5);
    }
    
    /* Typography cho số liệu */
    .stMetricValue, [data-testid="stMetricValue"] { 
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 26px !important; 
        font-weight: 700 !important; 
    }
    
    /* Làm đẹp bảng dữ liệu */
    [data-testid="stDataFrame"] { 
        border-radius: 12px; 
        border: 1px solid #30363D; 
        overflow: hidden;
    }
    
    /* Tiêu đề */
    h1, h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; letter-spacing: -0.5px; }
    
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
# 3. CÁC HÀM TIỆN ÍCH & UI COMPONENTS (GLASSMORPHISM CARDS)
# ============================================================
def format_vn_price(value) -> str:
    if pd.isna(value) or value is None: return "N/A"
    try: return f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except: return str(value)

def premium_copyable_metric(label, value_str, delta_text=None, is_positive=None):
    """Thẻ KPI phong cách Glassmorphism, có viền phát sáng và nút Copy."""
    
    # Xác định màu sắc dựa trên xu hướng
    color = "#8B949E" # Mặc định xám
    glow = "rgba(255,255,255,0.05)"
    if is_positive is not None:
        color = "#00E676" if is_positive else "#FF1744"
        glow = "rgba(0, 230, 118, 0.15)" if is_positive else "rgba(255, 23, 68, 0.15)"
        
    delta_html = ""
    if delta_text:
        delta_color = "#00E676" if (is_positive or "+" in str(delta_text) or "LONG" in str(delta_text)) else "#FF1744"
        delta_html = f"<div style='color: {delta_color}; font-size: 13px; font-weight: 600; margin-top: 4px;'>{delta_text}</div>"
        
    html_code = f"""
    <div style="
        background: rgba(22, 27, 34, 0.6);
        backdrop-filter: blur(10px);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 4px 6px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05);
        font-family: 'Inter', sans-serif;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s;
    ">
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 2px; background: {color}; opacity: 0.8; box-shadow: 0 0 10px {glow};"></div>
        <div style="color: #8B949E; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">{label}</div>
        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
            <span style="color: #FFFFFF; font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 700; letter-spacing: -0.5px; line-height: 1;">{value_str}</span>
            <button onclick="navigator.clipboard.writeText('{value_str}'); this.innerHTML='✅'; setTimeout(() => this.innerHTML='<svg width=\\'16\\' height=\\'16\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'#8B949E\\' stroke-width=\\'2\\' stroke-linecap=\\'round\\' stroke-linejoin=\\'round\\'><rect x=\\'9\\' y=\\'9\\' width=\\'13\\' height=\\'13\\' rx=\\'2\\' ry=\\'2\\'></rect><path d=\\'M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1\\'></path></svg>', 2000);"
                    style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; cursor: pointer; padding: 6px; display: flex; align-items: center; justify-content: center; transition: 0.2s;" 
                    title="Copy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8B949E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
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
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 20px;'>
            <div style='background: linear-gradient(135deg, #2962FF, #00E5FF); padding: 8px; border-radius: 10px;'>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>
            </div>
            <div>
                <h2 style='margin: 0; font-size: 20px; line-height: 1.2;'>TradeDesk <span style='color: #2962FF;'>Pro</span></h2>
                <p style='margin: 0; color: #8B949E; font-size: 11px; letter-spacing: 1px;'>TERMINAL</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='color: #8B949E; font-size: 12px; font-weight: 600; margin-bottom: 5px;'>TÀI SẢN</p>", unsafe_allow_html=True)
    selected_asset = st.selectbox("Asset", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    st.markdown("<p style='color: #8B949E; font-size: 12px; font-weight: 600; margin-bottom: 5px; margin-top: 15px;'>KHUNG THỜI GIAN</p>", unsafe_allow_html=True)
    timeframe = st.selectbox("TF", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval_map = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}
    interval = interval_map[timeframe]
    
    if st.button("🔄 Đồng bộ dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    
    st.markdown("<p style='color: #8B949E; font-size: 12px; font-weight: 600; margin-bottom: 5px;'>HỆ THỐNG PHÂN TÍCH</p>", unsafe_allow_html=True)
    menu_selection = st.radio(
        "Menu",
        [
            "📊 Biểu Đồ Kỹ Thuật",
            "🎯 Kế Hoạch Giao Dịch",
            "🧠 Cấu Trúc Thị Trường (SMC)",
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
st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;'>
        <div>
            <h1 style='margin: 0; font-size: 28px; color: white;'>{selected_asset.split(' - ')[1]}</h1>
            <p style='margin: 0; color: #8B949E; font-family: "JetBrains Mono", monospace;'>{ticker} • {timeframe}</p>
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
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI", "MACD"))
    
    fig.add_trace(go.Candlestick(x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Giá", increasing_line_color="#00E676", decreasing_line_color="#FF1744"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA 20", line=dict(color="#2962FF", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA 50", line=dict(color="#E040FB", width=1.5)), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#00E5FF")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#FF1744", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#00E676", row=2, col=1)
    
    fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="Histogram", marker_color=["#00E676" if v >= 0 else "#FF1744" for v in df["MACD_hist"]]), row=3, col=1)
    
    # Làm trong suốt nền biểu đồ để hòa vào giao diện
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
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", side="right")
    
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "🎯 Kế Hoạch Giao Dịch":
    st.subheader("🎯 Thiết Lập Vị Thế")
    col_slider, _ = st.columns([2, 2])
    with col_slider: rr_ratio = st.slider("Tỷ lệ Risk:Reward", 1.0, 4.0, 2.0, 0.5)
        
    trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
    if trade_plan:
        direction_color = "#00E676" if trade_plan['direction'] == "LONG" else "#FF1744"
        st.markdown(f"<h3 style='color: {direction_color}; margin-top: 20px;'>Hướng: {trade_plan['direction']}</h3>", unsafe_allow_html=True)
        
        col_entry, col_sl, col_tp = st.columns(3)
        with col_entry: premium_copyable_metric("Entry", format_vn_price(trade_plan['entry']), "Vào lệnh", is_positive=None)
        with col_sl: premium_copyable_metric("Stop-Loss", format_vn_price(trade_plan['sl']), "Cắt lỗ", is_positive=False)
        with col_tp: premium_copyable_metric("Take-Profit", format_vn_price(trade_plan['tp']), "Chốt lời", is_positive=True)

# ------------------------------------------------------------
# KHU VỰC 3: SMC
# ------------------------------------------------------------
elif menu_selection == "🧠 Cấu Trúc Thị Trường (SMC)":
    st.subheader("🧠 Phân Tích Cấu Trúc (SMC)")
    st.info("Hệ thống đang phân tích dòng tiền thông minh...")

# ------------------------------------------------------------
# KHU VỰC 4: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 Tin Tức & Sự Kiện":
    st.subheader(f"📰 Tin Tức: {selected_asset.split(' - ')[1]}")
    news = fetch_news(ticker)
    for item in news:
        st.markdown(f"""
            <div style='background: rgba(22, 27, 34, 0.6); backdrop-filter: blur(10px); padding: 15px; border-radius: 10px; border-left: 4px solid #2962FF; margin-bottom: 12px;'>
                <div style='color: #FFFFFF; font-weight: 600; font-size: 16px; margin-bottom: 8px;'>
                    <a href='{item['link']}' target='_blank' style='color: #58A6FF; text-decoration: none;'>{item['title']}</a>
                </div>
                <div style='color: #8B949E; font-size: 12px; display: flex; align-items: center; gap: 5px;'>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    {item['published']}
                </div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 5: NHẬT KÝ GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "📓 Nhật Ký Giao Dịch":
    st.subheader("📓 Nhật Ký Giao Dịch")
    
    col_form, col_history = st.columns([1, 2])
    
    with col_form:
        with st.container():
            with st.form("journal_form", clear_on_submit=True):
                st.markdown("<p style='font-weight:600; color:#E6EDF3;'>➕ Ghi Lệnh Mới</p>", unsafe_allow_html=True)
                trade_date = st.date_input("Ngày", datetime.today())
                asset_name = st.text_input("Tài sản", value=selected_asset.split(' - ')[1])
                direction = st.selectbox("Hướng", ["LONG", "SHORT"])
                result = st.selectbox("Kết quả", ["WIN", "LOSS", "HÒA"])
                pnl_val = st.number_input("PnL (% hoặc $)", value=0.0, step=0.1)
                reason = st.text_area("Lý do", placeholder="Ghi chú kỷ luật...")
                
                submitted = st.form_submit_button("💾 Lưu Lệnh")
                if submitted:
                    add_trade(str(trade_date), asset_name.upper(), direction, result, reason, pnl_val)
                    st.rerun()
                    
            # Backup tools
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>", unsafe_allow_html=True)
            journal_df = get_trades()
            if not journal_df.empty:
                csv = journal_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Tải file Backup", data=csv, file_name="journal.csv", mime="text/csv")

    with col_history:
        if journal_df.empty:
            st.info("Chưa có dữ liệu.")
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
                    if val == 'WIN': return 'color: #00E676; font-weight: bold;'
                    elif val == 'LOSS': return 'color: #FF1744; font-weight: bold;'
                    return ''
                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #00E676;'
                        elif val < 0: return 'color: #FF1744;'
                    except: pass
                    return ''

                styled_df = filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style \
                    .map(color_result, subset=['result']) \
                    .map(color_pnl, subset=['pnl'])
                
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
