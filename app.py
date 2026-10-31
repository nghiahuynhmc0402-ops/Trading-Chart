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
# 1. CẤU HÌNH GIAO DIỆN & CSS (ARCHITECTURAL BLUEPRINT)
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro | Bản Vẽ Kỹ Thuật",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Architects+Daughter&family=JetBrains+Mono:wght@400;700&family=Roboto+Mono:wght@400;500;700&display=swap');
    
    /* Nền tảng chính (Cyanotype Blue + Grid) */
    .stApp { 
        background-color: #003366;
        background-image: 
            linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
        background-size: 20px 20px;
        color: rgba(255, 255, 255, 0.9) !important; 
        font-family: 'Roboto Mono', monospace;
    }
    
    /* Hiệu ứng Fade In Up (Pure CSS thay cho JS) */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(15px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Tự động áp dụng hiệu ứng cho các khối */
    .title-block, div[data-testid="column"], .smc-card, .news-card-item {
        animation: fadeInUp 0.6s cubic-bezier(0.25, 0.8, 0.25, 1) forwards;
    }

    /* Đảm bảo vùng biểu đồ không chặn thao tác vuốt cảm ứng */
    .stPlotlyChart {
        touch-action: pan-y pinch-zoom !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { 
        background-color: rgba(0, 51, 102, 0.95) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(5px);
    }
    
    /* Menu Điều Hướng (Radio) - Wireframe style */
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 8px !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label { 
        padding: 10px 15px !important; 
        border-radius: 0px !important; 
        cursor: pointer !important; 
        width: 100% !important;
        background-color: transparent !important;
        border: 1px solid transparent;
        border-bottom: 1px dashed rgba(255, 255, 255, 0.3);
        color: rgba(255, 255, 255, 0.6) !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { 
        color: #00FFFF !important; 
        border-bottom: 1px solid #00FFFF;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] { 
        color: #FFFFFF !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.8);
        border-bottom: 1px solid rgba(255, 255, 255, 0.8);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    
    /* Inputs / Selectbox */
    .stSelectbox div[data-baseweb="select"], .stTextInput input, .stNumberInput input, .stTextArea textarea { 
        background-color: transparent !important; 
        border: 1px solid rgba(255, 255, 255, 0.5) !important; 
        border-radius: 0px !important; 
        color: #FFFFFF !important;
        font-family: 'Roboto Mono', monospace !important;
    }
    .stSelectbox div[data-baseweb="select"]:focus-within, .stTextInput input:focus { 
        border-color: #00FFFF !important; 
        box-shadow: 0 0 5px rgba(0, 255, 255, 0.3) !important;
    }
    
    /* Nút bấm (Technical Stamp + Hover) */
    .stButton>button { 
        width: 100%; 
        border-radius: 0px !important; 
        background: transparent !important;
        color: #FFFFFF !important; 
        border: 1px solid #FFFFFF !important; 
        font-family: 'Roboto Mono', monospace !important;
        text-transform: uppercase;
        padding: 8px 12px; 
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    .stButton>button:hover { 
        background: rgba(255, 255, 255, 0.1) !important;
        box-shadow: 2px 2px 0px #00FFFF;
        transform: translate(-1px, -1px);
    }
    
    /* Dataframe */
    [data-testid="stDataFrame"] { 
        border-radius: 0px !important; 
        border: 1px solid rgba(255, 255, 255, 0.3) !important; 
    }
    
    /* Custom Classes */
    .title-block {
        border: 1px solid #FFFFFF;
        padding: 15px 20px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        background: rgba(255, 255, 255, 0.05);
        margin-bottom: 25px;
    }
    .title-block h1 { margin: 0; font-size: 24px; color: #FFFFFF !important; }
    .title-block p { margin: 0; font-size: 12px; color: rgba(255,255,255,0.7); }
    
    .redline {
        font-family: 'Architects Daughter', cursive;
        color: #FF3333;
        font-size: 16px;
        transform: rotate(-2deg);
        display: inline-block;
    }
    
    .drafting-label {
        color: #00FFFF;
        font-size: 11px;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 5px;
        display: block;
        font-weight: bold;
    }
    
    .smc-card {
        border: 1px solid rgba(255, 255, 255, 0.4);
        background: rgba(0, 51, 102, 0.6);
        padding: 15px;
        min-height: 150px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .smc-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0, 255, 255, 0.2);
    }
    .smc-title {
        color: #00FFFF;
        font-weight: bold;
        font-size: 14px;
        border-bottom: 1px dashed rgba(0, 255, 255, 0.3);
        padding-bottom: 8px;
        margin-bottom: 12px;
        text-transform: uppercase;
    }
    .smc-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 13px;
    }
    .smc-val { color: #E2E8F0; font-weight: bold; font-family: 'JetBrains Mono', monospace;}
    .val-green { color: #00FFFF; }
    .val-red { color: #FF3333; }
    
    .news-card-item {
        border-left: 3px solid #00FFFF;
        padding-left: 15px;
        margin-bottom: 20px;
    }
    
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Cursor Crosshair (Tọa độ X/Y) - Giữ lại hiệu ứng này
components.html("""
    <script>
    const crosshair = document.createElement('div');
    crosshair.style.position = 'fixed';
    crosshair.style.pointerEvents = 'none';
    crosshair.style.zIndex = '999999';
    crosshair.innerHTML = '<svg width="50" height="50" viewBox="0 0 50 50"><line x1="25" y1="0" x2="25" y2="50" stroke="#00FFFF" stroke-width="1" stroke-dasharray="4,4"/><line x1="0" y1="25" x2="50" y2="25" stroke="#00FFFF" stroke-width="1" stroke-dasharray="4,4"/><circle cx="25" cy="25" r="3" fill="none" stroke="#FF3333" stroke-width="1.5"/></svg>';
    document.body.appendChild(crosshair);
    const label = document.createElement('div');
    label.style.position = 'fixed';
    label.style.pointerEvents = 'none';
    label.style.zIndex = '999999';
    label.style.color = '#00FFFF';
    label.style.fontFamily = 'JetBrains Mono, monospace';
    label.style.fontSize = '10px';
    label.style.background = 'rgba(0,51,102,0.9)';
    label.style.padding = '2px 4px';
    label.style.border = '1px solid #00FFFF';
    document.body.appendChild(label);
    document.addEventListener('mousemove', (e) => {
        crosshair.style.left = (e.clientX - 25) + 'px';
        crosshair.style.top = (e.clientY - 25) + 'px';
        label.style.left = (e.clientX + 20) + 'px';
        label.style.top = (e.clientY + 20) + 'px';
        label.innerText = `X:${e.clientX} Y:${e.clientY}`;
    });
    </script>
""", height=0, width=0)

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
        return pd.read_sql_query("SELECT * FROM journal ORDER BY date DESC", conn)
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
        return pd.read_sql_query(f"SELECT * FROM bot_journal WHERE asset='{asset}' ORDER BY id DESC", conn)

# ============================================================
# 3. UI COMPONENTS & FORMAT
# ============================================================
def format_vn_price(value) -> str:
    if pd.isna(value) or value is None: return "N/A"
    try: return f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except: return str(value)

def blueprint_metric(label, value_str, delta_text=None, is_positive=None):
    border_color = "rgba(255,255,255,0.8)"
    text_color = "#00FFFF"
    delta_color = "rgba(255,255,255,0.7)"
    
    if is_positive is not None:
        text_color = "#00FFFF" if is_positive else "#FF3333"
        delta_color = "#00FFFF" if is_positive else "#FF3333"
        
    delta_html = ""
    if delta_text:
        if is_positive is None:
            delta_color = "#00FFFF" if ("+" in str(delta_text) or "MUA" in str(delta_text)) else ("#FF3333" if ("-" in str(delta_text) or "BÁN" in str(delta_text)) else "rgba(255,255,255,0.7)")
        delta_html = f"<div style='color: {delta_color}; font-size: 12px; font-weight: bold; margin-top: 5px; border-top: 1px dashed rgba(255,255,255,0.3); padding-top: 5px;'>[{delta_text}]</div>"
        
    html_code = f"""
    <div style="
        background-color: transparent;
        padding: 15px;
        border: 1px solid {border_color};
        font-family: 'Roboto Mono', monospace;
        position: relative;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    ">
        <div style="position: absolute; top: -5px; left: -5px; color: {border_color}; font-size: 14px;">+</div>
        <div style="position: absolute; top: -5px; right: -5px; color: {border_color}; font-size: 14px;">+</div>
        <div style="position: absolute; bottom: -5px; left: -5px; color: {border_color}; font-size: 14px;">+</div>
        <div style="position: absolute; bottom: -5px; right: -5px; color: {border_color}; font-size: 14px;">+</div>
        
        <div style="position: absolute; top: -10px; left: 10px; background: #003366; padding: 0 4px; color: rgba(255,255,255,0.6); font-size: 10px;">DIM: 240 x 110</div>
        
        <div style="color: rgba(255,255,255,0.8); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;">{label}</div>
        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
            <span style="color: {text_color}; font-size: 22px; font-weight: bold;">{value_str}</span>
            <button onclick="navigator.clipboard.writeText('{value_str}'); this.innerText='[OK]'; setTimeout(() => this.innerText='[CPY]', 2000);"
                    style="background: transparent; border: 1px solid rgba(255,255,255,0.5); cursor: pointer; font-size: 10px; color: #FFFFFF; padding: 2px 6px; font-family: 'Roboto Mono', monospace;" 
                    title="Copy giá trị">
                [CPY]
            </button>
        </div>
        {delta_html}
    </div>
    """
    components.html(html_code, height=120)

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

@st.cache_data(ttl=300, show_spinner="⏳ ĐANG KẾT NỐI DỮ LIỆU...")
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
# 5. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
        <div style='text-align: left; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 15px; margin-bottom: 20px;'>
            <div style='color: #00FFFF; font-size: 10px; letter-spacing: 2px; margin-bottom: 5px;'>HỆ THỐNG</div>
            <h2 style='margin: 0; font-size: 20px; line-height: 1; color: #FFF;'>TRADEDESK<br><span style='color: #00FFFF;'>PRO</span></h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<span class='drafting-label'>CẤU HÌNH / TÀI SẢN</span>", unsafe_allow_html=True)
    selected_asset = st.selectbox("Asset", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    st.markdown("<span class='drafting-label' style='margin-top: 15px;'>CẤU HÌNH / KHUNG THỜI GIAN</span>", unsafe_allow_html=True)
    timeframe = st.selectbox("TF", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}[timeframe]
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    if st.button("CẬP NHẬT DỮ LIỆU", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("<hr style='border-color: rgba(255,255,255,0.2); margin: 20px 0;'>", unsafe_allow_html=True)
    
    st.markdown("<span class='drafting-label'>CHỨC NĂNG</span>", unsafe_allow_html=True)
    menu_selection = st.radio(
        "Menu",
        [
            "📐 BIỂU ĐỒ KỸ THUẬT",
            "🎯 KẾ HOẠCH GIAO DỊCH",
            "🧠 PHÂN TÍCH SMC",
            "📰 TIN TỨC",
            "📓 NHẬT KÝ GIAO DỊCH"
        ],
        label_visibility="collapsed"
    )

# ============================================================
# 6. MAIN AREA
# ============================================================
df = load_data(ticker, interval)

if df is None or len(df) < 50:
    st.error(f"❌ LỖI: KHÔNG CÓ DỮ LIỆU CHO {selected_asset}.")
    st.stop()

with st.spinner("⚙️ ĐANG TÍNH TOÁN CHỈ BÁO..."):
    df = compute_indicators(df)
    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_close
    change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

run_bot_engine(df, ticker, timeframe)

# TITLE BLOCK
st.markdown(f"""
    <div class='title-block'>
        <div>
            <p style='color: #00FFFF; font-weight: bold; letter-spacing: 2px;'>DỰ ÁN:</p>
            <h1>{selected_asset.split(' - ')[1]}</h1>
            <p style='font-size: 11px; margin-top: 5px; color: rgba(255,255,255,0.6);'>Mã: {ticker} | Khung: {timeframe} | Ngày: {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
        <div style='text-align: right;'>
            <p class='redline'>Trạng thái: Đang phân tích</p>
        </div>
    </div>
""", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: blueprint_metric("GIÁ HIỆN TẠI", format_vn_price(last_close), f"{change_pct:+.2f}%", is_positive=(change_pct >= 0))
with kpi2: blueprint_metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}", "QUÁ MUA" if df['RSI'].iloc[-1]>70 else ("QUÁ BÁN" if df['RSI'].iloc[-1]<30 else "TRUNG TÍNH"), is_positive=(df['RSI'].iloc[-1]<70))
with kpi3: blueprint_metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}", "XU HƯỚNG MẠNH" if df['ADX'].iloc[-1]>25 else "ĐI NGANG", is_positive=None)
with kpi4: blueprint_metric("ATR (14)", format_vn_price(df['ATR'].iloc[-1]), "ĐỘ BIẾN ĐỘNG", is_positive=None)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 1: BIỂU ĐỒ
# ------------------------------------------------------------
if menu_selection == "📐 BIỂU ĐỒ KỸ THUẬT":
    chart_df = df.tail(300).copy()
    
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI (14)", "MACD (12, 26, 9)"))
    
    fig.add_trace(go.Candlestick(
        x=chart_df["Time"], open=chart_df["Open"], high=chart_df["High"], low=chart_df["Low"], close=chart_df["Close"], name="PRICE", 
        increasing_line_color="#FFFFFF", decreasing_line_color="#FF3333",
        increasing_fillcolor="rgba(255,255,255,0.2)", decreasing_fillcolor="rgba(255,51,51,0.2)"
    ), row=1, col=1)
    
    active_trade = get_active_bot_trade(ticker)
    if active_trade is not None:
        fig.add_hline(y=active_trade['entry_price'], line_dash="solid", line_color="#00FFFF", line_width=1, annotation_text="VÀO LỆNH", row=1, col=1)
        fig.add_hline(y=active_trade['sl'], line_dash="dash", line_color="#FF3333", line_width=1, annotation_text="CẮT LỖ", row=1, col=1)
        fig.add_hline(y=active_trade['tp'], line_dash="dash", line_color="#FFFFFF", line_width=1, annotation_text="CHỐT LỜI", row=1, col=1)

    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["EMA20"], name="EMA 20", line=dict(color="#00FFFF", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["EMA50"], name="EMA 50", line=dict(color="rgba(255,255,255,0.4)", width=1.5, dash='dot')), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["RSI"], name="RSI", line=dict(color="#FFFFFF")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF3333", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00FFFF", row=2, col=1)
    
    fig.add_trace(go.Bar(x=chart_df["Time"], y=chart_df["MACD_hist"], name="MACD_HIST", marker_color=["#FFFFFF" if v >= 0 else "#FF3333" for v in chart_df["MACD_hist"]]), row=3, col=1)
    
    fig.update_layout(
        template="plotly_dark", 
        height=750, 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)", 
        hovermode="x", 
        showlegend=False, 
        margin=dict(l=10, r=50, t=30, b=10), 
        dragmode="pan",
        font=dict(family="Roboto Mono, monospace", color="#FFFFFF", size=11),
        uirevision='constant'
    )
    
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)", rangeslider_visible=False, gridwidth=1)
    fig.update_xaxes(
        rangeslider=dict(visible=True, bgcolor="#002244", bordercolor="rgba(255,255,255,0.3)", borderwidth=1), 
        row=3, col=1
    )
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1D", step="day", stepmode="backward"),
                dict(count=7, label="1W", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(step="all", label="TẤT CẢ")
            ]),
            bgcolor="#003366", activecolor="#00FFFF", font=dict(color="#FFFFFF")
        ), row=1, col=1
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)", side="right", gridwidth=1)
    
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})
    st.caption("💡 **Mẹo di động:** Dùng 2 ngón tay để phóng to/thu nhỏ. Dùng 1 ngón tay để kéo biểu đồ. Hoặc dùng thanh trượt ở dưới cùng.")

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH & BOT
# ------------------------------------------------------------
elif menu_selection == "🎯 KẾ HOẠCH GIAO DỊCH":
    st.markdown("<span class='drafting-label'>PHẦN 1: KẾ HOẠCH GIAO DỊCH THỦ CÔNG</span>", unsafe_allow_html=True)
    
    col_slider, _ = st.columns([1, 2])
    with col_slider: rr_ratio = st.slider("Tỷ lệ R:R (Lợi nhuận : Rủi ro)", 1.0, 4.0, 2.0, 0.5)
        
    trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
    if trade_plan:
        direction_color = "#00FFFF" if trade_plan['direction'] == "LONG" else "#FF3333"
        direction_vn = "MUA (LONG)" if trade_plan['direction'] == "LONG" else "BÁN (SHORT)"
        st.markdown(f"<h3 style='color: {direction_color}; margin-top: 10px;'>TÍN HIỆU ĐỀ XUẤT: {direction_vn}</h3>", unsafe_allow_html=True)
        
        col_entry, col_sl, col_tp = st.columns(3)
        with col_entry: blueprint_metric("GIÁ VÀO LỆNH", format_vn_price(trade_plan['entry']), "THỰC THI", is_positive=None)
        with col_sl: blueprint_metric("CẮT LỖ (SL)", format_vn_price(trade_plan['sl']), "BẢO VỆ VỐN", is_positive=False)
        with col_tp: blueprint_metric("CHỐT LỜI (TP)", format_vn_price(trade_plan['tp']), "MỤC TIÊU", is_positive=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.2); margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<span class='drafting-label'>PHẦN 2: NHẬT KÝ BOT TỰ ĐỘNG</span>", unsafe_allow_html=True)
    
    col_bot_btn, _ = st.columns([1, 3])
    with col_bot_btn:
        if st.button("CẬP NHẬT BOT", key="reload_bot_btn"):
            with st.spinner("⏳ ĐANG QUÉT TÍN HIỆU..."):
                st.cache_data.clear() 
                st.rerun()            
    
    active_bot = get_active_bot_trade(ticker)
    bot_df = get_bot_history(ticker)
    
    if active_bot is not None:
        dir_vn = "MUA" if active_bot['direction'] == "LONG" else "BÁN"
        st.markdown(f"""
            <div style='border: 1px dashed #00FFFF; padding: 15px; margin-bottom: 20px; background: rgba(0,255,255,0.05);'>
                <div style='color: #00FFFF; font-weight: bold; margin-bottom: 5px;'>[!] BOT ĐANG GIỮ LỆNH: {dir_vn}</div>
                <div style='color: #FFFFFF; font-size: 13px;'>Vào lệnh: {format_vn_price(active_bot['entry_price'])} | 
                SL: <span style='color:#FF3333'>{format_vn_price(active_bot['sl'])}</span> | 
                TP: <span style='color:#00FFFF'>{format_vn_price(active_bot['tp'])}</span></div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("> BOT ĐANG ĐỨNG NGOÀI: CHỜ TÍN HIỆU ĐỒNG QUY VÀ THỜI GIAN COOLDOWN.")

    if not bot_df.empty:
        closed_trades = bot_df[bot_df['status'] != 'ACTIVE']
        total_closed = len(closed_trades)
        wins = len(closed_trades[closed_trades['status'] == 'WIN'])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("TỔNG LỆNH ĐÃ ĐÓNG", total_closed)
        c2.metric("TỶ LỆ THẮNG", f"{win_rate:.1f}%")
        c3.metric("LỆNH CẮT SỚM", len(closed_trades[closed_trades['status'] == 'CUT_EARLY']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        display_df = bot_df.copy()
        display_df['open_time'] = pd.to_datetime(display_df['open_time']).dt.strftime('%d/%m/%Y %H:%M')
        display_df['close_time'] = pd.to_datetime(display_df['close_time']).dt.strftime('%d/%m/%Y %H:%M').fillna('-')
        
        display_df['direction'] = display_df['direction'].replace({'LONG': 'MUA', 'SHORT': 'BÁN'})
        display_df['status'] = display_df['status'].replace({'WIN': 'THẮNG', 'LOSS': 'THUA', 'CUT_EARLY': 'CẮT SỚM', 'ACTIVE': 'ĐANG MỞ'})
        
        for col in ['entry_price', 'exit_price', 'sl', 'tp']:
            display_df[col] = display_df[col].apply(lambda x: format_vn_price(x) if pd.notna(x) else '-')
            
        def color_bot_status(val):
            if val == 'THẮNG': return 'color: #00FFFF; font-weight: bold;'
            if val == 'THUA': return 'color: #FF3333; font-weight: bold;'
            if val == 'CẮT SỚM': return 'color: #FFFFFF; font-weight: bold;'
            return ''

        st.dataframe(display_df[['open_time', 'close_time', 'direction', 'entry_price', 'exit_price', 'sl', 'tp', 'status', 'reason']].style.map(color_bot_status, subset=['status']), hide_index=True, use_container_width=True)

# ------------------------------------------------------------
# KHU VỰC 3: PHÂN TÍCH SMC
# ------------------------------------------------------------
elif menu_selection == "🧠 PHÂN TÍCH SMC":
    st.markdown("<span class='drafting-label'>PHẦN 3: PHÂN TÍCH CẤU TRÚC THỊ TRƯỜNG (SMC)</span>", unsafe_allow_html=True)
    
    if not HAS_SMC:
        st.warning("Thư viện `pyvsmc` chưa được cài đặt. Vui lòng kiểm tra lại requirements.txt.")
    else:
        with st.spinner("🔎 ĐANG QUÉT CẤU TRÚC DÒNG TIỀN..."):
            try:
                high_arr, low_arr, close_arr, open_arr = df["High"].values, df["Low"].values, df["Close"].values, df["Open"].values
                
                fvg = smc.detect_fvg(high_arr, low_arr, close=close_arr, compute_mitigation=True)
                obs = smc.detect_order_blocks(open_arr, high_arr, low_arr, close_arr, lookback=5, zone_mode="body")
                structure = smc.detect_structure(high_arr, low_arr, close_arr, window_size=2, break_mode="close")
                
                trend_val = structure.trend[-1] if len(structure.trend) > 0 else 0
                trend_text = "TĂNG (UPTREND)" if trend_val == 1 else ("GIẢM (DOWNTREND)" if trend_val == -1 else "ĐI NGANG (SIDEWAY)")
                trend_color = "val-green" if trend_val == 1 else ("val-red" if trend_val == -1 else "")
                
                bos_bull = structure.bos_bullish[-1] if isinstance(structure.bos_bullish, np.ndarray) else structure.bos_bullish
                bos_bear = structure.bos_bearish[-1] if isinstance(structure.bos_bearish, np.ndarray) else structure.bos_bearish
                
                choch_val = 0
                if hasattr(structure, 'choch'):
                    choch_val = structure.choch[-1] if isinstance(structure.choch, np.ndarray) else structure.choch
                elif hasattr(structure, 'choch_bullish'):
                    c_bull = structure.choch_bullish[-1] if isinstance(structure.choch_bullish, np.ndarray) else False
                    c_bear = structure.choch_bearish[-1] if isinstance(structure.choch_bearish, np.ndarray) else False
                    choch_val = 1 if c_bull else (-1 if c_bear else 0)
                
                col_fvg, col_obs, col_struct = st.columns(3)
                
                with col_fvg:
                    st.markdown(f"""
                        <div class='smc-card'>
                            <div class='smc-title'>Fair Value Gaps (FVG)</div>
                            <div class='smc-row'><span>FVG Tăng:</span> <span class='smc-val val-green'>{len(fvg.bullish)}</span></div>
                            <div class='smc-row'><span>FVG Giảm:</span> <span class='smc-val val-red'>{len(fvg.bearish)}</span></div>
                            <div class='smc-row'><span>Đã lấp đầy:</span> <span class='smc-val'>{len(fvg.mitigated_50)}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col_obs:
                    st.markdown(f"""
                        <div class='smc-card'>
                            <div class='smc-title'>Order Blocks (OB)</div>
                            <div class='smc-row'><span>OB Cầu (Demand):</span> <span class='smc-val val-green'>{len(obs.bullish_ob)}</span></div>
                            <div class='smc-row'><span>OB Cung (Supply):</span> <span class='smc-val val-red'>{len(obs.bearish_ob)}</span></div>
                            <div class='smc-row'><span>OB Bị phá vỡ:</span> <span class='smc-val'>{len(obs.is_breaker)}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col_struct:
                    st.markdown(f"""
                        <div class='smc-card'>
                            <div class='smc-title'>Cấu Trúc Giá</div>
                            <div class='smc-row'><span>Xu hướng:</span> <span class='smc-val {trend_color}'>{trend_text}</span></div>
                            <div class='smc-row'><span>BOS Tăng:</span> <span class='smc-val val-green'>{'CÓ' if bos_bull else 'KHÔNG'}</span></div>
                            <div class='smc-row'><span>BOS Giảm:</span> <span class='smc-val val-red'>{'CÓ' if bos_bear else 'KHÔNG'}</span></div>
                            <div class='smc-row'><span>Đảo chiều (CHOCH):</span> <span class='smc-val'>{'CÓ' if choch_val != 0 else 'KHÔNG'}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"Lỗi phân tích SMC: {e}")

# ------------------------------------------------------------
# KHU VỰC 4: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 TIN TỨC":
    st.markdown("<span class='drafting-label'>PHẦN 4: BẢNG TIN THỊ TRƯỜNG</span>", unsafe_allow_html=True)
    news = fetch_news(ticker)
    for item in news:
        st.markdown(f"""
            <div class='news-card-item'>
                <div style='margin-bottom: 5px;'>
                    <a href='{item['link']}' target='_blank' style='color: #E2E8F0; text-decoration: underline; font-weight: bold;'>[XEM THÊM]</a>
                    <span style='color: #E2E8F0;'>{item['title']}</span>
                </div>
                <div style='color: #00FFFF; font-size: 11px;'>THỜI GIAN: {item['published']}</div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 5: NHẬT KÝ GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "📓 NHẬT KÝ GIAO DỊCH":
    st.markdown("<span class='drafting-label'>PHẦN 5: NHẬT KÝ GIAO DỊCH THỦ CÔNG</span>", unsafe_allow_html=True)
    col_form, col_history = st.columns([1, 2], gap="large")
    
    with col_form:
        st.markdown("<div style='border: 1px solid rgba(255,255,255,0.4); padding: 20px; background: rgba(0,51,102,0.5);'>", unsafe_allow_html=True)
        with st.form("journal_form", clear_on_submit=True):
            st.markdown("<p style='color: #00FFFF; font-weight: bold; margin-bottom: 15px;'>+--- GHI NHẬN LỆNH MỚI ---+</p>", unsafe_allow_html=True)
            trade_date = st.date_input("NGÀY")
            asset_name = st.text_input("TÀI SẢN", value=selected_asset.split(' - ')[1])
            direction = st.selectbox("HƯỚNG", ["LONG", "SHORT"])
            result = st.selectbox("KẾT QUẢ", ["THẮNG", "THUA", "HÒA"])
            pnl_val = st.number_input("LỢI NHUẬN / LỖ", value=0.0, step=0.1)
            reason = st.text_area("LÝ DO", placeholder="Nhập ghi chú...")
            
            if st.form_submit_button("LƯU DỮ LIỆU", use_container_width=True):
                add_trade(str(trade_date), asset_name.upper(), direction, result, reason, pnl_val)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
                
        journal_df = get_trades()
        if not journal_df.empty:
            csv = journal_df.to_csv(index=False).encode('utf-8')
            st.download_button("XUẤT FILE CSV", data=csv, file_name="nhat_ky_giao_dich.csv", mime="text/csv", use_container_width=True)

    with col_history:
        if journal_df.empty:
            st.info("> CHƯA CÓ DỮ LIỆU GIAO DỊCH.")
        else:
            journal_df['date'] = pd.to_datetime(journal_df['date'], errors='coerce')
            journal_df['pnl'] = pd.to_numeric(journal_df['pnl'], errors='coerce')
            
            total_trades = len(journal_df)
            win_rate = (len(journal_df[journal_df['result'] == 'THẮNG']) / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = journal_df['pnl'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("TỔNG SỐ LỆNH", total_trades)
            c2.metric("TỶ LỆ THẮNG", f"{win_rate:.1f}%")
            c3.metric("TỔNG PNL", f"{total_pnl:+.2f}", delta_color="normal" if total_pnl >=0 else "inverse")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_filter1, col_filter2 = st.columns(2)
            years = journal_df['date'].dt.year.dropna().unique()
            if len(years) > 0:
                selected_year = col_filter1.selectbox("NĂM", sorted(years, reverse=True))
                months = journal_df[journal_df['date'].dt.year == selected_year]['date'].dt.month.dropna().unique()
                selected_month = col_filter2.selectbox("THÁNG", sorted(months, reverse=True))
                
                filtered_df = journal_df[(journal_df['date'].dt.year == selected_year) & (journal_df['date'].dt.month == selected_month)].copy()
                filtered_df['date'] = filtered_df['date'].dt.strftime('%d/%m/%Y')
                
                def color_result(val):
                    if val == 'THẮNG': return 'color: #00FFFF; font-weight: bold;'
                    elif val == 'THUA': return 'color: #FF3333; font-weight: bold;'
                    return 'color: rgba(255,255,255,0.6);'
                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #00FFFF;'
                        elif val < 0: return 'color: #FF3333;'
                    except: pass
                    return 'color: rgba(255,255,255,0.6);'

                st.dataframe(filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style.map(color_result, subset=['result']).map(color_pnl, subset=['pnl']), hide_index=True, use_container_width=True)
