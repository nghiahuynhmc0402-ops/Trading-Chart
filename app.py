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
    page_title="TradeDesk Pro | Blueprint",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Bản vẽ kỹ thuật
st.markdown("""
    <style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Architects+Daughter&family=Roboto+Mono:wght@400;700&display=swap');
    
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
    
    /* Typography */
    h1, h2, h3 { 
        color: #FFFFFF !important; 
        font-family: 'Roboto Mono', monospace !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] { 
        background-color: rgba(0, 51, 102, 0.9) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.5);
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
        color: rgba(255, 255, 255, 0.7) !important;
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
    .stSelectbox div[data-baseweb="select"]:focus, .stTextInput input:focus { 
        border-color: #00FFFF !important; 
        box-shadow: 0 0 5px rgba(0, 255, 255, 0.3) !important;
    }
    
    /* Nút bấm (Technical Stamp) */
    .stButton>button { 
        width: 100%; 
        border-radius: 0px !important; 
        background: transparent !important;
        color: #FFFFFF !important; 
        border: 1px solid #FFFFFF !important; 
        font-family: 'Roboto Mono', monospace !important;
        text-transform: uppercase;
        padding: 8px 12px; 
        transition: all 0.2s ease;
    }
    .stButton>button:hover { 
        background: rgba(255, 255, 255, 0.1) !important;
        box-shadow: 2px 2px 0px #00FFFF;
        transform: translate(-1px, -1px);
    }
    
    /* Dataframe */
    [data-testid="stDataFrame"] { 
        border-radius: 0px !important; 
        border: 1px solid rgba(255, 255, 255, 0.5) !important; 
    }
    
    /* Redline Note (Ghi chú sửa lỗi) */
    .redline {
        font-family: 'Architects Daughter', cursive;
        color: #FF3333;
        font-size: 16px;
        transform: rotate(-2deg);
        display: inline-block;
        margin: 10px 0;
    }
    
    /* Ẩn footer */
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Thêm Cursor Crosshair (Tâm ngắm tọa độ)
components.html("""
    <script>
    const crosshair = document.createElement('div');
    crosshair.style.position = 'fixed';
    crosshair.style.pointerEvents = 'none';
    crosshair.style.zIndex = '999999';
    crosshair.innerHTML = '<svg width="40" height="40" viewBox="0 0 40 40"><line x1="20" y1="0" x2="20" y2="40" stroke="#00FFFF" stroke-width="1" stroke-dasharray="2,2"/><line x1="0" y1="20" x2="40" y2="20" stroke="#00FFFF" stroke-width="1" stroke-dasharray="2,2"/><circle cx="20" cy="20" r="2" fill="#FF3333"/></svg>';
    document.body.appendChild(crosshair);
    const label = document.createElement('div');
    label.style.position = 'fixed';
    label.style.pointerEvents = 'none';
    label.style.zIndex = '999999';
    label.style.color = '#00FFFF';
    label.style.fontFamily = 'Roboto Mono, monospace';
    label.style.fontSize = '10px';
    label.style.background = 'rgba(0,51,102,0.8)';
    label.style.padding = '2px 4px';
    label.style.border = '1px solid #00FFFF';
    document.body.appendChild(label);
    document.addEventListener('mousemove', (e) => {
        crosshair.style.left = (e.clientX - 20) + 'px';
        crosshair.style.top = (e.clientY - 20) + 'px';
        label.style.left = (e.clientX + 15) + 'px';
        label.style.top = (e.clientY + 15) + 'px';
        label.innerText = `X:${e.clientX} Y:${e.clientY}`;
    });
    </script>
""", height=0, width=0)

# ============================================================
# 2. KHAI BÁO BIẾN TOÀN CỤC
# ============================================================
POPULAR_ASSETS = {
    "🔥 Hàng Hóa": {"Vàng (XAUUSD)": "GC=F", "Bạc (XAGUSD)": "SI=F", "Dầu WTI": "CL=F"},
    "₿ Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD"},
    "💵 Forex": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"},
    "🏦 Chỉ Số & CK Mỹ": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "Apple (AAPL)": "AAPL", "Tesla (TSLA)": "TSLA"}
}
flat_assets = {f"{cat} - {name}": tick for cat, assets in POPULAR_ASSETS.items() for name, tick in assets.items()}

# ============================================================
# 3. KHỞI TẠO DATABASE
# ============================================================
DB_FILE = "trading_journal.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, asset TEXT, direction TEXT, result TEXT, reason TEXT, pnl REAL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS bot_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            open_time TEXT, close_time TEXT, asset TEXT, direction TEXT, 
            entry_price REAL, exit_price REAL, sl REAL, tp REAL, 
            status TEXT, reason TEXT
        )''')

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
        conn.execute("INSERT INTO bot_journal (open_time, asset, direction, entry_price, sl, tp, status) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')", 
                     (open_time, asset, direction, entry, sl, tp))

def close_bot_trade(trade_id, close_time, exit_price, status, reason):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE bot_journal SET close_time=?, exit_price=?, status=?, reason=? WHERE id=?", 
                     (close_time, exit_price, status, reason, trade_id))

def get_bot_history(asset):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(f"SELECT * FROM bot_journal WHERE asset='{asset}' ORDER BY id DESC", conn)
    return df

# ============================================================
# 4. UI COMPONENTS & FORMAT (BLUEPRINT STYLE)
# ============================================================
def format_vn_price(value) -> str:
    if pd.isna(value) or value is None: return "N/A"
    try: return f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except: return str(value)

def blueprint_metric(label, value_str, delta_text=None, is_positive=None):
    """Tạo thẻ thông số dạng bản vẽ kỹ thuật với crosshairs."""
    border_color = "rgba(255,255,255,0.8)"
    text_color = "#00FFFF" # Cyan measurement
    delta_color = "rgba(255,255,255,0.7)"
    
    if is_positive is not None:
        text_color = "#00FFFF" if is_positive else "#FF3333"
        delta_color = "#00FFFF" if is_positive else "#FF3333"
        
    delta_html = ""
    if delta_text:
        if is_positive is None:
            delta_color = "#00FFFF" if ("+" in str(delta_text) or "LONG" in str(delta_text)) else ("#FF3333" if ("-" in str(delta_text) or "SHORT" in str(delta_text)) else "rgba(255,255,255,0.7)")
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
    ">
        <!-- Crosshairs (Dấu cộng 4 góc) -->
        <div style="position: absolute; top: -5px; left: -5px; color: {border_color}; font-size: 14px;">+</div>
        <div style="position: absolute; top: -5px; right: -5px; color: {border_color}; font-size: 14px;">+</div>
        <div style="position: absolute; bottom: -5px; left: -5px; color: {border_color}; font-size: 14px;">+</div>
        <div style="position: absolute; bottom: -5px; right: -5px; color: {border_color}; font-size: 14px;">+</div>
        
        <!-- Measurement Labels -->
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
# 5. LOGIC BOT GIAO DỊCH TỰ ĐỘNG
# ============================================================
def run_bot_engine(df, ticker, timeframe):
    latest = df.iloc[-1]
    current_time = str(latest['Time'])
    
    active_trade = get_active_bot_trade(ticker)
    if active_trade is not None:
        if active_trade['direction'] == 'LONG':
            if latest['Low'] <= active_trade['sl']:
                close_bot_trade(active_trade['id'], current_time, active_trade['sl'], 'LOSS', 'Chạm Stop-Loss (SL)')
            elif latest['High'] >= active_trade['tp']:
                close_bot_trade(active_trade['id'], current_time, active_trade['tp'], 'WIN', 'Chạm Take-Profit (TP)')
            elif latest['EMA20'] < latest['EMA50']:
                close_bot_trade(active_trade['id'], current_time, latest['Close'], 'CUT_EARLY', 'Cắt sớm: Tín hiệu đảo chiều (EMA)')
        elif active_trade['direction'] == 'SHORT':
            if latest['High'] >= active_trade['sl']:
                close_bot_trade(active_trade['id'], current_time, active_trade['sl'], 'LOSS', 'Chạm Stop-Loss (SL)')
            elif latest['Low'] <= active_trade['tp']:
                close_bot_trade(active_trade['id'], current_time, active_trade['tp'], 'WIN', 'Chạm Take-Profit (TP)')
            elif latest['EMA20'] > latest['EMA50']:
                close_bot_trade(active_trade['id'], current_time, latest['Close'], 'CUT_EARLY', 'Cắt sớm: Tín hiệu đảo chiều (EMA)')
        return

    last_closed = get_last_closed_bot_trade(ticker)
    if last_closed is not None:
        last_close_time = pd.to_datetime(last_closed['close_time'])
        cooldown = timedelta(hours=4)
        if "Ngày" in timeframe or "Tuần" in timeframe: cooldown = timedelta(days=3)
        elif "Giờ" in timeframe: cooldown = timedelta(hours=12)
        
        if (latest['Time'] - last_close_time) < cooldown:
            return

    entry = latest['Close']
    atr = latest['ATR']
    
    if (latest['EMA20'] > latest['EMA50'] and latest['RSI'] > 55 and latest['RSI'] < 75 and latest['MACD_hist'] > 0 and latest['ADX'] > 20):
        sl = latest['Low'] - (atr * 1.0)
        tp = entry + (entry - sl) * 2.0
        add_bot_trade(current_time, ticker, 'LONG', entry, sl, tp)
    elif (latest['EMA20'] < latest['EMA50'] and latest['RSI'] < 45 and latest['RSI'] > 25 and latest['MACD_hist'] < 0 and latest['ADX'] > 20):
        sl = latest['High'] + (atr * 1.0)
        tp = entry - (sl - entry) * 2.0
        add_bot_trade(current_time, ticker, 'SHORT', entry, sl, tp)

# ============================================================
# 6. HÀM LOAD DATA & TÍNH TOÁN
# ============================================================
@st.cache_data(ttl=300, show_spinner="⏳ PLOTTING DATA...")
def load_data(ticker: str, interval: str):
    period = "1y"
    if interval in ["1m", "5m", "15m", "60m"]: period = "1mo"
    elif interval in ["1d", "1wk"]: period = "2y"
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

@st.cache_data(ttl=600, show_spinner="📰 FETCHING NEWS...")
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
# 7. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <svg width="60" height="60" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <circle cx="50" cy="50" r="45" stroke="#FFFFFF" stroke-width="1" fill="none" stroke-dasharray="4 2"/>
                <line x1="50" y1="0" x2="50" y2="100" stroke="#00FFFF" stroke-width="1"/>
                <line x1="0" y1="50" x2="100" y2="50" stroke="#00FFFF" stroke-width="1"/>
                <rect x="25" y="25" width="50" height="50" stroke="#FFFFFF" stroke-width="2" fill="none"/>
                <circle cx="50" cy="50" r="5" fill="#FF3333"/>
            </svg>
            <h2 style='margin-top: 10px; font-size: 18px;'>TRADEDESK<br><span style='font-size: 12px; color: #00FFFF;'>BLUEPRINT v1.0</span></h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='border-top: 1px solid rgba(255,255,255,0.5); padding-top: 10px; margin-top: 10px;'>", unsafe_allow_html=True)
    st.markdown("<p style='color: #00FFFF; font-size: 11px; margin-bottom: 5px;'>VAR: ASSET_SELECT</p>", unsafe_allow_html=True)
    selected_asset = st.selectbox("Asset", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    st.markdown("<p style='color: #00FFFF; font-size: 11px; margin-bottom: 5px; margin-top: 15px;'>VAR: TIMEFRAME</p>", unsafe_allow_html=True)
    timeframe = st.selectbox("TF", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval_map = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}
    interval = interval_map[timeframe]
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    if st.button("UPDATE_DATA", width='stretch'):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("<div style='border-top: 1px dashed rgba(255,255,255,0.3); margin: 20px 0;'></div>", unsafe_allow_html=True)
    
    st.markdown("<p style='color: #00FFFF; font-size: 11px; margin-bottom: 5px;'>MODULE: NAVIGATION</p>", unsafe_allow_html=True)
    menu_selection = st.radio(
        "Menu",
        [
            "📐 BLUEPRINT_CHART",
            "🎯 STRUCTURAL_PLAN",
            "🧠 SMC_LOGIC",
            "📰 DATA_FEED",
            "📓 TRADE_LOG"
        ],
        label_visibility="collapsed"
    )

# ============================================================
# 8. MAIN AREA
# ============================================================
df = load_data(ticker, interval)

if df is None or len(df) < 50:
    st.error(f"❌ ERR: NO DATA FOR {selected_asset}.")
    st.stop()

with st.spinner("⚙️ CALCULATING INDICATORS..."):
    df = compute_indicators(df)
    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_close
    change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

# CHẠY BOT ENGINE TỰ ĐỘNG
run_bot_engine(df, ticker, timeframe)

# HEADER KPI
st.markdown(f"""
    <div style='margin-bottom: 30px; border-bottom: 1px solid #FFFFFF; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: flex-end;'>
        <div>
            <h1 style='margin: 0; font-size: 28px;'>[ PROJECT: {selected_asset.split(' - ')[1]} ]</h1>
            <p style='margin: 0; color: #00FFFF; font-size: 13px;'>ID: {ticker} | SCALE: {timeframe} | STATUS: DRAFTING</p>
        </div>
        <div style='text-align: right;'>
            <span class='redline'>* Auto-scaling grid to viewport</span>
        </div>
    </div>
""", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: blueprint_metric("MARKET_PRICE", format_vn_price(last_close), f"{change_pct:+.2f}%", is_positive=(change_pct >= 0))
with kpi2: blueprint_metric("RSI_14", f"{df['RSI'].iloc[-1]:.1f}", "OVERBOUGHT" if df['RSI'].iloc[-1]>70 else ("OVERSOLD" if df['RSI'].iloc[-1]<30 else "NEUTRAL"), is_positive=(df['RSI'].iloc[-1]<70))
with kpi3: blueprint_metric("ADX_14", f"{df['ADX'].iloc[-1]:.1f}", "STRONG_TREND" if df['ADX'].iloc[-1]>25 else "SIDEWAYS", is_positive=None)
with kpi4: blueprint_metric("ATR_14", format_vn_price(df['ATR'].iloc[-1]), "VOLATILITY", is_positive=None)

st.markdown("<br><br>", unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 1: BIỂU ĐỒ
# ------------------------------------------------------------
if menu_selection == "📐 BLUEPRINT_CHART":
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI_14", "MACD_12_26_9"))
    
    # Nến Blueprint: Trắng cho tăng, Đỏ cho giảm
    fig.add_trace(go.Candlestick(
        x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="PRICE", 
        increasing_line_color="#FFFFFF", decreasing_line_color="#FF3333",
        increasing_fillcolor="rgba(255,255,255,0.2)", decreasing_fillcolor="rgba(255,51,51,0.2)"
    ), row=1, col=1)
    
    active_trade = get_active_bot_trade(ticker)
    if active_trade is not None:
        fig.add_hline(y=active_trade['entry_price'], line_dash="solid", line_color="#00FFFF", line_width=1, annotation_text="ENTRY", row=1, col=1)
        fig.add_hline(y=active_trade['sl'], line_dash="dash", line_color="#FF3333", line_width=1, annotation_text="STOP_LOSS", row=1, col=1)
        fig.add_hline(y=active_trade['tp'], line_dash="dash", line_color="#FFFFFF", line_width=1, annotation_text="TAKE_PROFIT", row=1, col=1)

    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA_20", line=dict(color="#00FFFF", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA_50", line=dict(color="rgba(255,255,255,0.4)", width=1.5, dash='dot')), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#FFFFFF")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF3333", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00FFFF", row=2, col=1)
    
    fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="MACD_HIST", marker_color=["#FFFFFF" if v >= 0 else "#FF3333" for v in df["MACD_hist"]]), row=3, col=1)
    
    # Chart Theme (Blueprint)
    fig.update_layout(
        template="plotly_dark", 
        height=750, 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)", 
        hovermode="x unified", 
        showlegend=False, 
        margin=dict(l=10, r=50, t=30, b=10), 
        dragmode="pan",
        font=dict(family="Roboto Mono, monospace", color="#FFFFFF")
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,255,255,0.2)", rangeslider_visible=False, gridwidth=1, griddash='dot')
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,255,255,0.2)", side="right", gridwidth=1, griddash='dot')
    
    # Thêm ghi chú redline vào biểu đồ
    st.markdown("<span class='redline'>Note: Watch EMA cross at current support level.</span>", unsafe_allow_html=True)
    st.plotly_chart(fig, width='stretch', config={'scrollZoom': True, 'displayModeBar': False})

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH & LỊCH SỬ BOT
# ------------------------------------------------------------
elif menu_selection == "🎯 STRUCTURAL_PLAN":
    st.markdown("### [ MODULE: STRUCTURAL_PLAN ]")
    
    col_slider, _ = st.columns([1, 2])
    with col_slider: 
        rr_ratio = st.slider("Risk:Reward_Ratio", 1.0, 4.0, 2.0, 0.5)
        
    trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
    if trade_plan:
        direction_color = "#00FFFF" if trade_plan['direction'] == "LONG" else "#FF3333"
        
        st.markdown(f"""
            <div style='border: 1px solid {direction_color}; padding: 10px; margin-top: 10px; margin-bottom: 20px;'>
                <h3 style='color: {direction_color}; margin: 0;'>CALCULATED SIGNAL: {trade_plan['direction']}</h3>
            </div>
        """, unsafe_allow_html=True)
        
        col_entry, col_sl, col_tp = st.columns(3)
        with col_entry: blueprint_metric("ENTRY_PRICE", format_vn_price(trade_plan['entry']), "EXECUTE", is_positive=None)
        with col_sl: blueprint_metric("STOP_LOSS", format_vn_price(trade_plan['sl']), "PROTECT_CAPITAL", is_positive=False)
        with col_tp: blueprint_metric("TAKE_PROFIT", format_vn_price(trade_plan['tp']), "TARGET_PROFIT", is_positive=True)

    # --- PHẦN BOT TRADING HISTORY ---
    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    
    col_bot_title, col_bot_btn = st.columns([3, 1])
    with col_bot_title:
        st.markdown("### [ SYSTEM: AUTO_BOT_LOG ]")
    with col_bot_btn:
        if st.button("REFRESH_BOT", key="reload_bot_btn"):
            with st.spinner("⏳ SCANNING FOR NEW SIGNALS..."):
                st.cache_data.clear() 
                st.rerun()            
    
    active_bot = get_active_bot_trade(ticker)
    bot_df = get_bot_history(ticker)
    
    if not bot_df.empty:
        closed_trades = bot_df[bot_df['status'] != 'ACTIVE']
        total_closed = len(closed_trades)
        wins = len(closed_trades[closed_trades['status'] == 'WIN'])
        losses = len(closed_trades[closed_trades['status'] == 'LOSS'])
        cuts = len(closed_trades[closed_trades['status'] == 'CUT_EARLY'])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        col_stat1.metric("TOTAL_CLOSED", total_closed)
        col_stat2.metric("WIN_RATE", f"{win_rate:.1f}%")
        col_stat3.metric("WIN/LOSS", f"{wins}/{losses}")
        col_stat4.metric("EARLY_CUTS", cuts)
    else:
        st.info("> NO BOT TRADES FOUND IN DATABASE.")

    st.markdown("<br>", unsafe_allow_html=True)

    if active_bot is not None:
        st.markdown(f"""
            <div style='border: 1px dashed #00FFFF; padding: 10px; margin-bottom: 15px;'>
                <div style='color: #00FFFF; font-weight: bold; margin-bottom: 5px;'>[!] BOT ACTIVE: {active_bot['direction']}</div>
                <div style='color: #FFFFFF; font-size: 13px;'>ENTRY: {format_vn_price(active_bot['entry_price'])} | 
                SL: <span style='color:#FF3333'>{format_vn_price(active_bot['sl'])}</span> | 
                TP: <span style='color:#00FFFF'>{format_vn_price(active_bot['tp'])}</span></div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("> BOT IDLE: WAITING FOR STRICT CONFLUENCE & COOLDOWN.")

    if not bot_df.empty:
        display_df = bot_df.copy()
        display_df['open_time'] = pd.to_datetime(display_df['open_time']).dt.strftime('%d/%m/%Y %H:%M')
        display_df['close_time'] = pd.to_datetime(display_df['close_time']).dt.strftime('%d/%m/%Y %H:%M').fillna('-')
        
        for col in ['entry_price', 'exit_price', 'sl', 'tp']:
            display_df[col] = display_df[col].apply(lambda x: format_vn_price(x) if pd.notna(x) else '-')
            
        def color_bot_status(val):
            if val == 'WIN': return 'color: #00FFFF; font-weight: bold;'
            if val == 'LOSS': return 'color: #FF3333; font-weight: bold;'
            if val == 'CUT_EARLY': return 'color: #FFFFFF; font-weight: bold;' 
            if val == 'ACTIVE': return 'color: #00FFFF; text-decoration: underline;'
            return ''

        styled_bot_df = display_df[['open_time', 'close_time', 'direction', 'entry_price', 'exit_price', 'sl', 'tp', 'status', 'reason']].style \
            .map(color_bot_status, subset=['status'])
            
        st.dataframe(styled_bot_df, hide_index=True, width='stretch')
        
        st.markdown("""
        <div style='font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 10px;'>
            <strong>LOGIC:</strong> Executes on EMA/RSI/MACD confluence + ADX > 20. Auto-manages SL, TP, and Early Cuts on EMA cross. Implements cooldown period to prevent overtrading.
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 3: SMC
# ------------------------------------------------------------
elif menu_selection == "🧠 SMC_LOGIC":
    st.markdown("### [ MODULE: SMC_LOGIC ]")
    st.info("> ANALYZING SMART MONEY CONCEPTS... [PENDING IMPLEMENTATION]")

# ------------------------------------------------------------
# KHU VỰC 4: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 DATA_FEED":
    st.markdown(f"### [ MODULE: DATA_FEED // {selected_asset.split(' - ')[1]} ]")
    news = fetch_news(ticker)
    
    for item in news:
        st.markdown(f"""
            <div style='border-left: 2px solid #00FFFF; padding-left: 15px; margin-bottom: 20px;'>
                <div style='margin-bottom: 5px;'>
                    <a href='{item['link']}' target='_blank' style='color: #FFFFFF; text-decoration: underline; font-weight: bold;'>[READ_MORE]</a>
                    <span style='color: #FFFFFF;'>{item['title']}</span>
                </div>
                <div style='color: #00FFFF; font-size: 11px;'>TIMESTAMP: {item['published']}</div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 5: NHẬT KÝ GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "📓 TRADE_LOG":
    st.markdown("### [ MODULE: MANUAL_TRADE_LOG ]")
    
    col_form, col_history = st.columns([1, 2], gap="large")
    
    with col_form:
        st.markdown("<div style='border: 1px solid rgba(255,255,255,0.5); padding: 15px;'>", unsafe_allow_html=True)
        with st.form("journal_form", clear_on_submit=True):
            st.markdown("<p style='color: #00FFFF; font-weight: bold; margin-bottom: 15px;'>+--- INPUT NEW TRADE ---+</p>", unsafe_allow_html=True)
            trade_date = st.date_input("DATE", datetime.today())
            asset_name = st.text_input("ASSET", value=selected_asset.split(' - ')[1])
            direction = st.selectbox("DIRECTION", ["LONG", "SHORT"])
            result = st.selectbox("RESULT", ["WIN", "LOSS", "HÒA"])
            pnl_val = st.number_input("PnL", value=0.0, step=0.1)
            reason = st.text_area("REASON", placeholder="Nhập log lý do...")
            
            submitted = st.form_submit_button("COMMIT_TO_DB")
            if submitted:
                add_trade(str(trade_date), asset_name.upper(), direction, result, reason, pnl_val)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
                
        journal_df = get_trades()
        if not journal_df.empty:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            csv = journal_df.to_csv(index=False).encode('utf-8')
            st.download_button("export_csv", data=csv, file_name="journal.csv", mime="text/csv", width='stretch')

    with col_history:
        if journal_df.empty:
            st.info("> DATABASE EMPTY.")
        else:
            journal_df['date'] = pd.to_datetime(journal_df['date'], errors='coerce')
            journal_df['pnl'] = pd.to_numeric(journal_df['pnl'], errors='coerce')
            
            total_trades = len(journal_df)
            wins = len(journal_df[journal_df['result'] == 'WIN'])
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = journal_df['pnl'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("TOTAL_TRADES", total_trades)
            c2.metric("WIN_RATE", f"{win_rate:.1f}%")
            c3.metric("TOTAL_PNL", f"{total_pnl:+.2f}", delta_color="normal" if total_pnl >=0 else "inverse")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_filter1, col_filter2 = st.columns(2)
            years = journal_df['date'].dt.year.dropna().unique()
            if len(years) > 0:
                selected_year = col_filter1.selectbox("YEAR", sorted(years, reverse=True))
                months = journal_df[journal_df['date'].dt.year == selected_year]['date'].dt.month.dropna().unique()
                selected_month = col_filter2.selectbox("MONTH", sorted(months, reverse=True))
                
                filtered_df = journal_df[(journal_df['date'].dt.year == selected_year) & (journal_df['date'].dt.month == selected_month)].copy()
                filtered_df['date'] = filtered_df['date'].dt.strftime('%d/%m/%Y')
                
                def color_result(val):
                    if val == 'WIN': return 'color: #00FFFF; font-weight: bold;'
                    elif val == 'LOSS': return 'color: #FF3333; font-weight: bold;'
                    return 'color: rgba(255,255,255,0.6);'
                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #00FFFF;'
                        elif val < 0: return 'color: #FF3333;'
                    except: pass
                    return 'color: rgba(255,255,255,0.6);'

                styled_df = filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style \
                    .map(color_result, subset=['result']) \
                    .map(color_pnl, subset=['pnl'])
                
                st.dataframe(styled_df, hide_index=True, width='stretch')
