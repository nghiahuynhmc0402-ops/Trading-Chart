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
# 1. CẤU HÌNH GIAO DIỆN & CSS (MODERN DARK GLASSMORPHISM)
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Nền tảng chính (Deep Dark) */
    .stApp { 
        background-color: #09090b;
        color: #f4f4f5 !important; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar (Dark Glass) */
    [data-testid="stSidebar"] { 
        background-color: #18181b !important; 
        border-right: 1px solid #27272a;
        transition: all 0.3s ease;
    }
    
    /* Làm đẹp khu vực Search/Input */
    .stSelectbox div[data-baseweb="select"], .stTextInput input, .stNumberInput input, .stTextArea textarea { 
        background-color: #27272a !important; 
        border: 1px solid #3f3f46 !important; 
        border-radius: 8px !important; 
        color: #f4f4f5 !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease;
    }
    .stSelectbox div[data-baseweb="select"]:hover, .stTextInput input:hover { 
        border-color: #52525b !important; 
    }
    .stSelectbox div[data-baseweb="select"]:focus-within, .stTextInput input:focus { 
        border-color: #8b5cf6 !important; 
        box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2) !important;
    }
    
    /* Menu Điều Hướng (Radio) - Hiệu ứng Purple Glow */
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 4px !important; }
    
    div[data-testid="stRadio"] > div[role="radiogroup"] > label { 
        padding: 12px 16px !important; 
        border-radius: 8px !important; 
        cursor: pointer !important; 
        width: 100% !important;
        background-color: transparent !important;
        border: 1px solid transparent;
        color: #a1a1aa !important;
        transition: all 0.2s ease;
        margin-bottom: 2px;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { 
        background-color: #27272a !important;
        color: #f4f4f5 !important;
    }
    
    /* Trạng thái Active (Giống ảnh: Nền tím mờ, vạch tím bên trái) */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] { 
        background: linear-gradient(90deg, rgba(139, 92, 246, 0.15) 0%, rgba(139, 92, 246, 0) 100%) !important;
        border-left: 3px solid #8b5cf6 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 4px 8px 8px 4px !important;
        box-shadow: inset 20px 0 20px -20px rgba(139, 92, 246, 0.5);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p { 
        color: #ffffff !important; 
    }
    
    /* Ẩn vòng tròn Radio mặc định */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    
    /* Chữ trong Menu */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p { 
        font-size: 14px !important; 
        font-weight: 500 !important; 
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Nút bấm (Purple Gradient) */
    .stButton>button { 
        width: 100%; 
        border-radius: 8px !important; 
        background: #8b5cf6 !important;
        color: #ffffff !important; 
        border: none !important; 
        font-family: 'Inter', sans-serif !important;
        font-weight: 600;
        padding: 10px; 
        transition: all 0.3s ease;
    }
    .stButton>button:hover { 
        background: #7c3aed !important;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
        transform: translateY(-1px);
    }
    
    /* Dataframe */
    [data-testid="stDataFrame"] { 
        border-radius: 12px !important; 
        border: 1px solid #27272a !important; 
        background-color: #18181b !important;
    }
    
    /* Tiêu đề */
    h1, h2, h3 { color: #ffffff !important; font-family: 'Inter', sans-serif !important; font-weight: 700 !important; letter-spacing: -0.5px; }
    
    /* CSS cho các thành phần Custom */
    .sidebar-header {
        padding: 10px 0 20px 0;
        border-bottom: 1px solid #27272a;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .sidebar-logo {
        width: 32px; height: 32px;
        background: #ffffff;
        border-radius: 50%;
        display: flex; justify-content: center; align-items: center;
        color: #000;
        font-weight: bold; font-size: 18px;
    }
    .sidebar-title {
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
    }
    .sidebar-subtitle {
        font-size: 11px;
        color: #71717a;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 2px;
    }
    .menu-label {
        color: #71717a;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
        margin-top: 10px;
        padding-left: 10px;
    }
    .pro-card {
        background: #27272a;
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
        border: 1px solid #3f3f46;
    }
    .pro-card h4 { margin: 0 0 5px 0; font-size: 14px; color: #fff; }
    .pro-card p { margin: 0; font-size: 12px; color: #a1a1aa; }
    
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 2. KHAI BÁO BIẾN & DATABASE
# ============================================================
POPULAR_ASSETS = {
    "🔥 Hàng Hóa": {"Vàng (XAUUSD)": "GC=F", "Bạc (XAGUSD)": "SI=F", "Dầu WTI": "CL=F"},
    "₿ Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD"},
    "💵 Forex": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"},
    "🏦 Chỉ Số & CK Mỹ": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "Apple (AAPL)": "AAPL", "Tesla (TSLA)": "TSLA"}
}
flat_assets = {f"{cat} - {name}": tick for cat, assets in POPULAR_ASSETS.items() for name, tick in assets.items()}

DB_FILE = "trading_journal.db"
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, asset TEXT, direction TEXT, result TEXT, reason TEXT, pnl REAL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS bot_journal (id INTEGER PRIMARY KEY AUTOINCREMENT, open_time TEXT, close_time TEXT, asset TEXT, direction TEXT, entry_price REAL, exit_price REAL, sl REAL, tp REAL, status TEXT, reason TEXT)''')

init_db()

def add_trade(date, asset, direction, result, reason, pnl):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO journal (date, asset, direction, result, reason, pnl) VALUES (?, ?, ?, ?, ?, ?)", (date, asset, direction, result, reason, pnl))

def get_trades():
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT * FROM journal ORDER BY date DESC", conn)
    return df

def get_active_bot_trade(asset):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(f"SELECT * FROM bot_journal WHERE asset='{asset}' AND status='ACTIVE' ORDER BY id DESC LIMIT 1", conn)
    return df.iloc[0] if not df.empty else None

def get_last_closed_bot_trade(asset):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(f"SELECT * FROM bot_journal WHERE asset='{asset}' AND status!='ACTIVE' ORDER BY id DESC LIMIT 1", conn)
    return df.iloc[0] if not df.empty else None

def add_bot_trade(open_time, asset, direction, entry, sl, tp):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO bot_journal (open_time, asset, direction, entry_price, sl, tp, status) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')", (open_time, asset, direction, entry, sl, tp))

def close_bot_trade(trade_id, close_time, exit_price, status, reason):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE bot_journal SET close_time=?, exit_price=?, status=?, reason=? WHERE id=?", (close_time, exit_price, status, reason, trade_id))

def get_bot_history(asset):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(f"SELECT * FROM bot_journal WHERE asset='{asset}' ORDER BY id DESC", conn)
    return df

# ============================================================
# 3. UI COMPONENTS & FORMAT (GLASSMORPHISM CARDS)
# ============================================================
def format_vn_price(value) -> str:
    if pd.isna(value) or value is None: return "N/A"
    try: return f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except: return str(value)

def modern_metric(label, value_str, delta_text=None, is_positive=None):
    """Thẻ KPI phong cách Modern Dark Glassmorphism"""
    border_color = "#27272a"
    text_color = "#ffffff"
    delta_color = "#a1a1aa"
    glow_color = "rgba(255,255,255,0.05)"
    
    if is_positive is not None:
        text_color = "#10b981" if is_positive else "#ef4444"
        delta_color = "#10b981" if is_positive else "#ef4444"
        border_color = "rgba(16, 185, 129, 0.3)" if is_positive else "rgba(239, 68, 68, 0.3)"
        glow_color = "rgba(16, 185, 129, 0.1)" if is_positive else "rgba(239, 68, 68, 0.1)"
        
    delta_html = ""
    if delta_text:
        if is_positive is None:
            delta_color = "#10b981" if ("+" in str(delta_text) or "MUA" in str(delta_text)) else ("#ef4444" if ("-" in str(delta_text) or "BÁN" in str(delta_text)) else "#a1a1aa")
        delta_html = f"<div style='color: {delta_color}; font-size: 12px; font-weight: 600; margin-top: 8px; display: flex; align-items: center; gap: 4px;'>{delta_text}</div>"
        
    html_code = f"""
    <div style="
        background: #18181b;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid {border_color};
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.02);
        font-family: 'Inter', sans-serif;
        position: relative;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.2s;
    ">
        <div style="color: #71717a; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">{label}</div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: {text_color}; font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 700; line-height: 1;">{value_str}</span>
            <button onclick="navigator.clipboard.writeText('{value_str}'); this.innerHTML='<svg width=\\'16\\' height=\\'16\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'#10b981\\' stroke-width=\\'2\\'><polyline points=\\'20 6 9 17 4 12\\'></polyline></svg>'; setTimeout(() => this.innerHTML='<svg width=\\'16\\' height=\\'16\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'#71717a\\' stroke-width=\\'2\\'><rect x=\\'9\\' y=\\'9\\' width=\\'13\\' height=\\'13\\' rx=\\'2\\' ry=\\'2\\'></rect><path d=\\'M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1\\'></path></svg>', 2000);"
                    style="background: #27272a; border: 1px solid #3f3f46; border-radius: 6px; cursor: pointer; padding: 6px; display: flex; align-items: center; justify-content: center; transition: 0.2s;"
                    onmouseover="this.style.background='#3f3f46'" onmouseout="this.style.background='#27272a'" title="Copy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#71717a" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            </button>
        </div>
        {delta_html}
    </div>
    """
    components.html(html_code, height=125)

# ============================================================
# 4. LOGIC BOT & TÍNH TOÁN
# ============================================================
def run_bot_engine(df, ticker, timeframe):
    latest = df.iloc[-1]
    current_time = str(latest['Time'])
    
    active_trade = get_active_bot_trade(ticker)
    if active_trade is not None:
        if active_trade['direction'] == 'LONG':
            if latest['Low'] <= active_trade['sl']: close_bot_trade(active_trade['id'], current_time, active_trade['sl'], 'LOSS', 'Chạm Cắt Lỗ (SL)')
            elif latest['High'] >= active_trade['tp']: close_bot_trade(active_trade['id'], current_time, active_trade['tp'], 'WIN', 'Chạm Chốt Lời (TP)')
            elif latest['EMA20'] < latest['EMA50']: close_bot_trade(active_trade['id'], current_time, latest['Close'], 'CUT_EARLY', 'Cắt sớm do đảo chiều EMA')
        elif active_trade['direction'] == 'SHORT':
            if latest['High'] >= active_trade['sl']: close_bot_trade(active_trade['id'], current_time, active_trade['sl'], 'LOSS', 'Chạm Cắt Lỗ (SL)')
            elif latest['Low'] <= active_trade['tp']: close_bot_trade(active_trade['id'], current_time, active_trade['tp'], 'WIN', 'Chạm Chốt Lời (TP)')
            elif latest['EMA20'] > latest['EMA50']: close_bot_trade(active_trade['id'], current_time, latest['Close'], 'CUT_EARLY', 'Cắt sớm do đảo chiều EMA')
        return

    last_closed = get_last_closed_bot_trade(ticker)
    if last_closed is not None:
        last_close_time = pd.to_datetime(last_closed['close_time'])
        cooldown = timedelta(hours=4) if "Giờ" not in timeframe else timedelta(hours=12)
        if "Ngày" in timeframe or "Tuần" in timeframe: cooldown = timedelta(days=3)
        if (latest['Time'] - last_close_time) < cooldown: return

    entry, atr = latest['Close'], latest['ATR']
    if (latest['EMA20'] > latest['EMA50'] and 55 < latest['RSI'] < 75 and latest['MACD_hist'] > 0 and latest['ADX'] > 20):
        add_bot_trade(current_time, ticker, 'LONG', entry, latest['Low'] - atr, entry + (entry - (latest['Low'] - atr)) * 2.0)
    elif (latest['EMA20'] < latest['EMA50'] and 25 < latest['RSI'] < 45 and latest['MACD_hist'] < 0 and latest['ADX'] > 20):
        add_bot_trade(current_time, ticker, 'SHORT', entry, latest['High'] + atr, entry - ((latest['High'] + atr) - entry) * 2.0)

@st.cache_data(ttl=300, show_spinner="⏳ ĐANG TẢI DỮ LIỆU...")
def load_data(ticker: str, interval: str):
    period = "1mo" if interval in ["1m", "5m", "15m", "60m"] else "2y"
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        time_col = "Datetime" if "Datetime" in df.columns else "Date"
        df = df.rename(columns={time_col: "Time"})
        df["Time"] = pd.to_datetime(df["Time"])
        return df.dropna(subset=["Close"])
    except: return None

@st.cache_data(ttl=600, show_spinner="📰 ĐANG TẢI TIN TỨC...")
def fetch_news(ticker_name: str):
    feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker_name.replace(' ', '+')}&region=US&lang=en-US")
    return [{"title": e.title, "link": e.link, "published": e.get("published", "N/A")} for e in feed.entries[:5]]

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["EMA20"] = EMAIndicator(close=df["Close"], window=20).ema_indicator()
    df["EMA50"] = EMAIndicator(close=df["Close"], window=50).ema_indicator()
    df["RSI"] = RSIIndicator(close=df["Close"], window=14).rsi()
    macd = MACD(close=df["Close"])
    df["MACD_hist"] = macd.macd_diff()
    df["ATR"] = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=14).average_true_range()
    df["ADX"] = ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=14).adx()
    return df

def calculate_trade_levels(df: pd.DataFrame, risk_reward: float = 2.0) -> dict:
    if len(df) < 20: return None
    last, atr = df.iloc[-1], df.iloc[-1]["ATR"]
    recent_df = df.tail(20)
    r_high, r_low = recent_df["High"].max(), recent_df["Low"].min()
    
    if last["EMA20"] > last["EMA50"]:
        entry, sl, direction = last["Close"], r_low - (atr * 0.5), "LONG"
        tp = entry + (entry - sl) * risk_reward
    else:
        entry, sl, direction = last["Close"], r_high + (atr * 0.5), "SHORT"
        tp = entry - (sl - entry) * risk_reward
    return {"direction": direction, "entry": entry, "sl": sl, "tp": tp}

# ============================================================
# 5. SIDEBAR (CUSTOM UI)
# ============================================================
with st.sidebar:
    # Header
    st.markdown("""
        <div class='sidebar-header'>
            <div class='sidebar-logo'>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>
            </div>
            <div>
                <h2 class='sidebar-title'>TradeDesk Pro</h2>
                <div class='sidebar-subtitle'>Terminal UI</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Search / Asset Selector (Styled like search bar)
    st.markdown("<p style='color: #71717a; font-size: 12px; margin-bottom: 5px;'>Tìm kiếm / Chọn tài sản</p>", unsafe_allow_html=True)
    selected_asset = st.selectbox("Asset", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    # Timeframe
    st.markdown("<p style='color: #71717a; font-size: 12px; margin-bottom: 5px;'>Khung thời gian</p>", unsafe_allow_html=True)
    timeframe = st.selectbox("TF", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}[timeframe]
    
    if st.button("🔄 Cập nhật dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("<hr style='border-color: #27272a; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # Menu Navigation
    st.markdown("<div class='menu-label'>Menu</div>", unsafe_allow_html=True)
    menu_selection = st.radio(
        "Menu",
        [
            "🏠 Tổng quan",
            "🎯 Kế hoạch giao dịch",
            "🧠 Phân tích SMC",
            "📰 Tin tức & Sự kiện",
            "📓 Nhật ký giao dịch"
        ],
        label_visibility="collapsed"
    )
    
    # Pro Card / Footer
    st.markdown("""
        <div style='margin-top: 30px;'>
            <div class='pro-card'>
                <h4>Nâng cấp Pro</h4>
                <p>Mở khóa tính năng Bot tự động và dữ liệu Realtime.</p>
            </div>
            <div style='display: flex; align-items: center; gap: 8px; color: #52525b; font-size: 12px; margin-top: 15px;'>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Tải dữ liệu nhanh hơn
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================
# 6. MAIN AREA
# ============================================================
df = load_data(ticker, interval)

if df is None or len(df) < 50:
    st.error(f"❌ Không có dữ liệu cho {selected_asset}.")
    st.stop()

with st.spinner("⚙️ Đang tính toán..."):
    df = compute_indicators(df)
    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_close
    change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

run_bot_engine(df, ticker, timeframe)

# HEADER
st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 30px;'>
        <div>
            <h1 style='margin: 0; font-size: 28px; color: #ffffff;'>{selected_asset.split(' - ')[1]}</h1>
            <p style='margin: 0; color: #71717a; font-size: 14px; font-weight: 500;'>{ticker} • {timeframe}</p>
        </div>
        <div style='background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); padding: 6px 12px; border-radius: 20px; display: flex; align-items: center; gap: 8px;'>
            <div style='width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981;'></div>
            <span style='color: #10b981; font-size: 13px; font-weight: 600;'>Thị trường đang mở</span>
        </div>
    </div>
""", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: modern_metric("Giá hiện tại", format_vn_price(last_close), f"{change_pct:+.2f}%", is_positive=(change_pct >= 0))
with kpi2: modern_metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}", "QUÁ MUA" if df['RSI'].iloc[-1]>70 else ("QUÁ BÁN" if df['RSI'].iloc[-1]<30 else "TRUNG TÍNH"), is_positive=(df['RSI'].iloc[-1]<70))
with kpi3: modern_metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}", "XU HƯỚNG MẠNH" if df['ADX'].iloc[-1]>25 else "ĐI NGANG", is_positive=None)
with kpi4: modern_metric("ATR (14)", format_vn_price(df['ATR'].iloc[-1]), "ĐỘ BIẾN ĐỘNG", is_positive=None)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 1: TỔNG QUAN (BIỂU ĐỒ)
# ------------------------------------------------------------
if menu_selection == "🏠 Tổng quan":
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI (14)", "MACD (12, 26, 9)"))
    
    fig.add_trace(go.Candlestick(
        x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="PRICE", 
        increasing_line_color="#10b981", decreasing_line_color="#ef4444",
        increasing_fillcolor="#10b981", decreasing_fillcolor="#ef4444"
    ), row=1, col=1)
    
    active_trade = get_active_bot_trade(ticker)
    if active_trade is not None:
        fig.add_hline(y=active_trade['entry_price'], line_dash="solid", line_color="#8b5cf6", line_width=1.5, annotation_text="ENTRY", row=1, col=1)
        fig.add_hline(y=active_trade['sl'], line_dash="dash", line_color="#ef4444", line_width=1, annotation_text="SL", row=1, col=1)
        fig.add_hline(y=active_trade['tp'], line_dash="dash", line_color="#10b981", line_width=1, annotation_text="TP", row=1, col=1)

    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA 20", line=dict(color="#8b5cf6", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA 50", line=dict(color="#52525b", width=1.5, dash='dot')), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#a1a1aa", width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=2, col=1)
    
    fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="MACD", marker_color=["#10b981" if v >= 0 else "#ef4444" for v in df["MACD_hist"]]), row=3, col=1)
    
    fig.update_layout(
        template="plotly_dark", height=700, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
        hovermode="x unified", showlegend=False, margin=dict(l=10, r=50, t=30, b=10), dragmode="pan",
        font=dict(family="Inter, sans-serif", color="#a1a1aa", size=12)
    )
    fig.update_xaxes(showgrid=True, gridcolor="#27272a", rangeslider_visible=False, gridwidth=1)
    fig.update_yaxes(showgrid=True, gridcolor="#27272a", side="right", gridwidth=1)
    
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH & BOT
# ------------------------------------------------------------
elif menu_selection == "🎯 Kế hoạch giao dịch":
    st.subheader("Kế hoạch giao dịch thủ công")
    
    col_slider, _ = st.columns([1, 2])
    with col_slider: rr_ratio = st.slider("Tỷ lệ R:R", 1.0, 4.0, 2.0, 0.5)
        
    trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
    if trade_plan:
        direction_color = "#10b981" if trade_plan['direction'] == "LONG" else "#ef4444"
        direction_vn = "MUA (LONG)" if trade_plan['direction'] == "LONG" else "BÁN (SHORT)"
        st.markdown(f"<h3 style='color: {direction_color}; margin-top: 10px;'>Tín hiệu: {direction_vn}</h3>", unsafe_allow_html=True)
        
        col_entry, col_sl, col_tp = st.columns(3)
        with col_entry: modern_metric("Giá vào lệnh", format_vn_price(trade_plan['entry']), "THỰC THI", is_positive=None)
        with col_sl: modern_metric("Cắt lỗ (SL)", format_vn_price(trade_plan['sl']), "BẢO VỆ VỐN", is_positive=False)
        with col_tp: modern_metric("Chốt lời (TP)", format_vn_price(trade_plan['tp']), "MỤC TIÊU", is_positive=True)

    st.divider()
    st.subheader("Nhật ký Bot tự động")
    
    col_bot_btn, _ = st.columns([1, 3])
    with col_bot_btn:
        if st.button("🔄 Cập nhật Bot", key="reload_bot_btn"):
            with st.spinner("⏳ Đang quét tín hiệu..."):
                st.cache_data.clear() 
                st.rerun()            
    
    active_bot = get_active_bot_trade(ticker)
    bot_df = get_bot_history(ticker)
    
    if active_bot is not None:
        dir_vn = "MUA" if active_bot['direction'] == "LONG" else "BÁN"
        st.markdown(f"""
            <div style='background: rgba(139, 92, 246, 0.1); border: 1px solid #8b5cf6; border-radius: 8px; padding: 15px; margin-bottom: 20px;'>
                <div style='color: #8b5cf6; font-weight: 600; margin-bottom: 5px;'>BOT ĐANG GIỮ LỆNH: {dir_vn}</div>
                <div style='color: #e4e4e7; font-size: 14px;'>Vào lệnh: {format_vn_price(active_bot['entry_price'])} | 
                SL: <span style='color:#ef4444'>{format_vn_price(active_bot['sl'])}</span> | 
                TP: <span style='color:#10b981'>{format_vn_price(active_bot['tp'])}</span></div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Bot đang đứng ngoài chờ tín hiệu.")

    if not bot_df.empty:
        closed_trades = bot_df[bot_df['status'] != 'ACTIVE']
        total_closed = len(closed_trades)
        wins = len(closed_trades[closed_trades['status'] == 'WIN'])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng lệnh đã đóng", total_closed)
        c2.metric("Tỷ lệ thắng", f"{win_rate:.1f}%")
        c3.metric("Lệnh cắt sớm", len(closed_trades[closed_trades['status'] == 'CUT_EARLY']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        display_df = bot_df.copy()
        display_df['open_time'] = pd.to_datetime(display_df['open_time']).dt.strftime('%d/%m/%Y %H:%M')
        display_df['close_time'] = pd.to_datetime(display_df['close_time']).dt.strftime('%d/%m/%Y %H:%M').fillna('-')
        
        display_df['direction'] = display_df['direction'].replace({'LONG': 'MUA', 'SHORT': 'BÁN'})
        display_df['status'] = display_df['status'].replace({'WIN': 'THẮNG', 'LOSS': 'THUA', 'CUT_EARLY': 'CẮT SỚM', 'ACTIVE': 'ĐANG MỞ'})
        
        for col in ['entry_price', 'exit_price', 'sl', 'tp']:
            display_df[col] = display_df[col].apply(lambda x: format_vn_price(x) if pd.notna(x) else '-')
            
        def color_bot_status(val):
            if val == 'THẮNG': return 'color: #10b981; font-weight: bold;'
            if val == 'THUA': return 'color: #ef4444; font-weight: bold;'
            if val == 'CẮT SỚM': return 'color: #f59e0b; font-weight: bold;'
            return ''

        st.dataframe(display_df[['open_time', 'close_time', 'direction', 'entry_price', 'exit_price', 'sl', 'tp', 'status', 'reason']].style.map(color_bot_status, subset=['status']), hide_index=True, use_container_width=True)

# ------------------------------------------------------------
# KHU VỰC 3: PHÂN TÍCH SMC
# ------------------------------------------------------------
elif menu_selection == "🧠 Phân tích SMC":
    st.subheader("Phân tích Cấu trúc Thị trường (SMC)")
    
    if not HAS_SMC:
        st.warning("Thư viện `pyvsmc` chưa được cài đặt.")
    else:
        with st.spinner("🔎 Đang quét cấu trúc..."):
            try:
                high_arr, low_arr, close_arr, open_arr = df["High"].values, df["Low"].values, df["Close"].values, df["Open"].values
                
                fvg = smc.detect_fvg(high_arr, low_arr, close=close_arr, compute_mitigation=True)
                obs = smc.detect_order_blocks(open_arr, high_arr, low_arr, close_arr, lookback=5, zone_mode="body")
                structure = smc.detect_structure(high_arr, low_arr, close_arr, window_size=2, break_mode="close")
                
                trend_val = structure.trend[-1] if len(structure.trend) > 0 else 0
                trend_text = "TĂNG" if trend_val == 1 else ("GIẢM" if trend_val == -1 else "ĐI NGANG")
                trend_color = "#10b981" if trend_val == 1 else ("#ef4444" if trend_val == -1 else "#a1a1aa")
                
                bos_bull = structure.bos_bullish[-1] if isinstance(structure.bos_bullish, np.ndarray) else structure.bos_bullish
                bos_bear = structure.bos_bearish[-1] if isinstance(structure.bos_bearish, np.ndarray) else structure.bos_bearish
                
                choch_val = 0
                if hasattr(structure, 'choch'):
                    choch_val = structure.choch[-1] if isinstance(structure.choch, np.ndarray) else structure.choch
                
                col_fvg, col_obs, col_struct = st.columns(3)
                
                with col_fvg:
                    st.markdown(f"""
                        <div style='background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px;'>
                            <h4 style='margin-top: 0; color: #ffffff; font-size: 16px;'>Fair Value Gaps</h4>
                            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #a1a1aa;'>FVG Tăng:</span> <span style='color: #10b981; font-weight: bold;'>{len(fvg.bullish)}</span></div>
                            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #a1a1aa;'>FVG Giảm:</span> <span style='color: #ef4444; font-weight: bold;'>{len(fvg.bearish)}</span></div>
                            <div style='display: flex; justify-content: space-between;'><span style='color: #a1a1aa;'>Đã lấp đầy:</span> <span style='color: #ffffff;'>{len(fvg.mitigated_50)}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col_obs:
                    st.markdown(f"""
                        <div style='background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px;'>
                            <h4 style='margin-top: 0; color: #ffffff; font-size: 16px;'>Order Blocks</h4>
                            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #a1a1aa;'>OB Cầu:</span> <span style='color: #10b981; font-weight: bold;'>{len(obs.bullish_ob)}</span></div>
                            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #a1a1aa;'>OB Cung:</span> <span style='color: #ef4444; font-weight: bold;'>{len(obs.bearish_ob)}</span></div>
                            <div style='display: flex; justify-content: space-between;'><span style='color: #a1a1aa;'>OB Phá vỡ:</span> <span style='color: #ffffff;'>{len(obs.is_breaker)}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col_struct:
                    st.markdown(f"""
                        <div style='background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px;'>
                            <h4 style='margin-top: 0; color: #ffffff; font-size: 16px;'>Cấu Trúc Giá</h4>
                            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #a1a1aa;'>Xu hướng:</span> <span style='color: {trend_color}; font-weight: bold;'>{trend_text}</span></div>
                            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #a1a1aa;'>BOS Tăng:</span> <span style='color: #10b981;'>{'CÓ' if bos_bull else 'KHÔNG'}</span></div>
                            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #a1a1aa;'>BOS Giảm:</span> <span style='color: #ef4444;'>{'CÓ' if bos_bear else 'KHÔNG'}</span></div>
                            <div style='display: flex; justify-content: space-between;'><span style='color: #a1a1aa;'>CHOCH:</span> <span style='color: #ffffff;'>{'CÓ' if choch_val != 0 else 'KHÔNG'}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"Lỗi phân tích SMC: {e}")

# ------------------------------------------------------------
# KHU VỰC 4: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 Tin tức & Sự kiện":
    st.subheader(f"Tin tức: {selected_asset.split(' - ')[1]}")
    news = fetch_news(ticker)
    for item in news:
        st.markdown(f"""
            <div style='background: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 15px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 8px;'>
                <a href='{item['link']}' target='_blank' style='color: #8b5cf6; text-decoration: none; font-weight: 600; font-size: 15px;' onmouseover="this.style.color='#a78bfa'" onmouseout="this.style.color='#8b5cf6'">{item['title']}</a>
                <div style='color: #71717a; font-size: 12px; display: flex; align-items: center; gap: 5px;'>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    {item['published']}
                </div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 5: NHẬT KÝ GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "📓 Nhật ký giao dịch":
    st.subheader("Nhật ký giao dịch thủ công")
    col_form, col_history = st.columns([1, 2], gap="large")
    
    with col_form:
        st.markdown("<div style='background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px;'>", unsafe_allow_html=True)
        with st.form("journal_form", clear_on_submit=True):
            st.markdown("<p style='color: #ffffff; font-weight: 600; margin-bottom: 15px;'>➕ Ghi nhận lệnh mới</p>", unsafe_allow_html=True)
            trade_date = st.date_input("Ngày")
            asset_name = st.text_input("Tài sản", value=selected_asset.split(' - ')[1])
            direction = st.selectbox("Hướng", ["LONG", "SHORT"])
            result = st.selectbox("Kết quả", ["THẮNG", "THUA", "HÒA"])
            pnl_val = st.number_input("PnL", value=0.0, step=0.1)
            reason = st.text_area("Lý do", placeholder="Nhập ghi chú...")
            
            if st.form_submit_button("Lưu dữ liệu", use_container_width=True):
                add_trade(str(trade_date), asset_name.upper(), direction, result, reason, pnl_val)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
                
        journal_df = get_trades()
        if not journal_df.empty:
            csv = journal_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Xuất file CSV", data=csv, file_name="nhat_ky.csv", mime="text/csv", use_container_width=True)

    with col_history:
        if journal_df.empty:
            st.info("Chưa có dữ liệu giao dịch.")
        else:
            journal_df['date'] = pd.to_datetime(journal_df['date'], errors='coerce')
            journal_df['pnl'] = pd.to_numeric(journal_df['pnl'], errors='coerce')
            
            total_trades = len(journal_df)
            win_rate = (len(journal_df[journal_df['result'] == 'THẮNG']) / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = journal_df['pnl'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng số lệnh", total_trades)
            c2.metric("Tỷ lệ thắng", f"{win_rate:.1f}%")
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
                    if val == 'THẮNG': return 'color: #10b981; font-weight: bold;'
                    elif val == 'THUA': return 'color: #ef4444; font-weight: bold;'
                    return 'color: #a1a1aa;'
                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #10b981;'
                        elif val < 0: return 'color: #ef4444;'
                    except: pass
                    return 'color: #a1a1aa;'

                st.dataframe(filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style.map(color_result, subset=['result']).map(color_pnl, subset=['pnl']), hide_index=True, use_container_width=True)
