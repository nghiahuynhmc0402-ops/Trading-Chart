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
# 1. CẤU HÌNH GIAO DIỆN & CSS (TERMINAL CLI STYLE)
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro | Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Import Font chữ Monospace */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Nền tảng chính */
    .stApp { 
        background-color: #0a0a0a; 
        color: #33ff00 !important; 
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* Lớp phủ CRT Scanlines */
    .stApp::before {
        content: " ";
        display: block;
        position: absolute;
        top: 0; left: 0; bottom: 0; right: 0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        z-index: 9999;
        background-size: 100% 2px, 3px 100%;
        pointer-events: none;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] { 
        background-color: #0a0a0a !important; 
        border-right: 1px dashed #1f521f;
    }
    
    /* Menu Điều Hướng (Radio) - Dạng CLI Prompt */
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 5px !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label { 
        padding: 8px 12px !important; 
        border-radius: 0px !important; 
        cursor: pointer !important; 
        width: 100% !important;
        color: #1f521f !important;
        transition: all 0.1s ease;
        background-color: transparent !important;
        border: 1px solid transparent;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { 
        color: #33ff00 !important; 
        border: 1px dashed #1f521f;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] { 
        color: #33ff00 !important;
        text-shadow: 0 0 5px rgba(51, 255, 0, 0.5);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"]::before { 
        content: "> "; 
        color: #33ff00;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p { 
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px !important; 
    }
    
    /* Inputs / Selectbox */
    .stSelectbox div[data-baseweb="select"], .stTextInput input, .stNumberInput input, .stTextArea textarea { 
        background-color: #0a0a0a !important; 
        border: 1px solid #1f521f !important; 
        border-radius: 0px !important; 
        color: #33ff00 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    .stSelectbox div[data-baseweb="select"]:focus, .stTextInput input:focus { 
        border-color: #33ff00 !important; 
        box-shadow: none !important;
    }
    .stSelectbox svg { fill: #33ff00 !important; }
    
    /* Nút bấm (Buttons) */
    .stButton>button { 
        width: 100%; 
        border-radius: 0px !important; 
        background: transparent !important;
        color: #33ff00 !important; 
        border: 1px solid #1f521f !important; 
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700;
        padding: 8px 12px; 
        transition: all 0.2s ease;
    }
    .stButton>button::before { content: "[ "; }
    .stButton>button::after { content: " ]"; }
    .stButton>button:hover { 
        background: #33ff00 !important;
        color: #0a0a0a !important;
        box-shadow: 0 0 10px rgba(51, 255, 0, 0.5);
    }
    
    /* Typography */
    h1, h2, h3 { 
        color: #33ff00 !important; 
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase;
        text-shadow: 0 0 5px rgba(51, 255, 0, 0.5);
    }
    hr { border-color: #1f521f !important; border-style: dashed !important; }
    
    /* Table / Dataframe */
    [data-testid="stDataFrame"] { 
        border-radius: 0px !important; 
        border: 1px solid #1f521f !important; 
    }
    
    /* Ẩn footer và thanh công cụ */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

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
# 4. UI COMPONENTS & FORMAT (TERMINAL STYLE)
# ============================================================
def format_vn_price(value) -> str:
    if pd.isna(value) or value is None: return "N/A"
    try: return f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except: return str(value)

def terminal_metric(label, value_str, delta_text=None, is_positive=None):
    """Tạo thẻ hiển thị dạng cửa sổ Terminal CLI."""
    border_color = "#1f521f"
    text_color = "#33ff00"
    delta_color = "#1f521f"
    
    if is_positive is not None:
        border_color = "#33ff00" if is_positive else "#ff3333"
        text_color = "#33ff00" if is_positive else "#ff3333"
        delta_color = "#33ff00" if is_positive else "#ff3333"
        
    delta_html = ""
    if delta_text:
        if is_positive is None:
            delta_color = "#33ff00" if ("+" in str(delta_text) or "LONG" in str(delta_text)) else ("#ff3333" if ("-" in str(delta_text) or "SHORT" in str(delta_text)) else "#ffb000")
        delta_html = f"<div style='color: {delta_color}; font-size: 12px; font-weight: bold; margin-top: 5px;'>[{delta_text}]</div>"
        
    html_code = f"""
    <div style="
        background-color: #0a0a0a;
        padding: 12px;
        border: 1px dashed {border_color};
        font-family: 'JetBrains Mono', monospace;
        position: relative;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    ">
        <div style="color: #1f521f; font-size: 11px; margin-bottom: 5px;">+--- {label} ---+</div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: {text_color}; font-size: 20px; font-weight: bold; text-shadow: 0 0 5px rgba(51, 255, 0, 0.5);">{value_str}</span>
            <button onclick="navigator.clipboard.writeText('{value_str}'); this.innerText='[COPIED]'; setTimeout(() => this.innerText='[COPY]', 2000);"
                    style="background: transparent; border: none; cursor: pointer; font-size: 11px; color: #33ff00; padding: 0; font-family: 'JetBrains Mono', monospace;" 
                    title="Copy giá trị">
                [COPY]
            </button>
        </div>
        {delta_html}
    </div>
    """
    components.html(html_code, height=110)

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
@st.cache_data(ttl=300, show_spinner="⏳ CONNECTING TO DATA STREAM...")
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

@st.cache_data(ttl=600, show_spinner="📰 FETCHING NEWS DATA...")
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
    # ASCII Art Logo
    st.markdown("""
        <pre style='color: #33ff00; font-size: 10px; line-height: 1.2; margin-bottom: 20px; text-shadow: 0 0 5px rgba(51, 255, 0, 0.5);'>
  _______         _        _____            _    
 |__   __|       | |      |  __ \\          | |   
    | | _ __ __ _| |_ ___ | |  | | ___  ___| | __
    | || '__/ _` | __/ _ \\| |  | |/ _ \\/ __| |/ /
    | || | | (_| | ||  __/| |__| |  __/\\__ \\   < 
    |_||_|  \\__,_|\\__\\___||_____/ \\___||___/_|\\_\\
        </pre>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='color: #1f521f; font-size: 11px; font-family: monospace; margin-bottom: 5px;'>user@tradedesk:~$ <span style='color:#33ff00'>select_asset</span></p>", unsafe_allow_html=True)
    selected_asset = st.selectbox("Asset", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    st.markdown("<p style='color: #1f521f; font-size: 11px; font-family: monospace; margin-bottom: 5px; margin-top: 15px;'>user@tradedesk:~$ <span style='color:#33ff00'>set_timeframe</span></p>", unsafe_allow_html=True)
    timeframe = st.selectbox("TF", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval_map = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}
    interval = interval_map[timeframe]
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    if st.button("sync_data", width='stretch'):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("<p style='color: #1f521f;'>=========================================</p>", unsafe_allow_html=True)
    
    st.markdown("<p style='color: #1f521f; font-size: 11px; font-family: monospace; margin-bottom: 5px;'>user@tradedesk:~$ <span style='color:#33ff00'>run_module</span></p>", unsafe_allow_html=True)
    menu_selection = st.radio(
        "Menu",
        [
            "📊 CHART_VIEW",
            "🎯 TRADE_PLANNER",
            "🧠 SMC_ANALYSIS",
            "📰 NEWS_FEED",
            "📓 TRADE_JOURNAL"
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
    <div style='margin-bottom: 20px; border-bottom: 1px dashed #1f521f; padding-bottom: 10px;'>
        <h1 style='margin: 0; font-size: 22px;'>[ SYSTEM: {selected_asset.split(' - ')[1]} ]</h1>
        <p style='margin: 0; color: #1f521f; font-size: 13px;'>{ticker} // {timeframe} // STATUS: ONLINE</p>
    </div>
""", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: terminal_metric("MARKET_PRICE", format_vn_price(last_close), f"{change_pct:+.2f}%", is_positive=(change_pct >= 0))
with kpi2: terminal_metric("RSI_14", f"{df['RSI'].iloc[-1]:.1f}", "OVERBOUGHT" if df['RSI'].iloc[-1]>70 else ("OVERSOLD" if df['RSI'].iloc[-1]<30 else "NEUTRAL"), is_positive=(df['RSI'].iloc[-1]<70))
with kpi3: terminal_metric("ADX_14", f"{df['ADX'].iloc[-1]:.1f}", "STRONG_TREND" if df['ADX'].iloc[-1]>25 else "SIDEWAYS", is_positive=None)
with kpi4: terminal_metric("ATR_14", format_vn_price(df['ATR'].iloc[-1]), "VOLATILITY", is_positive=None)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 1: BIỂU ĐỒ
# ------------------------------------------------------------
if menu_selection == "📊 CHART_VIEW":
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI_14", "MACD_12_26_9"))
    
    # Nến Terminal: Xanh Neon và Đỏ Neon
    fig.add_trace(go.Candlestick(
        x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="PRICE", 
        increasing_line_color="#33ff00", decreasing_line_color="#ff3333",
        increasing_fillcolor="#33ff00", decreasing_fillcolor="#ff3333"
    ), row=1, col=1)
    
    active_trade = get_active_bot_trade(ticker)
    if active_trade is not None:
        fig.add_hline(y=active_trade['entry_price'], line_dash="solid", line_color="#33ff00", line_width=1, annotation_text="ENTRY", row=1, col=1)
        fig.add_hline(y=active_trade['sl'], line_dash="dash", line_color="#ff3333", line_width=1, annotation_text="STOP_LOSS", row=1, col=1)
        fig.add_hline(y=active_trade['tp'], line_dash="dash", line_color="#33ff00", line_width=1, annotation_text="TAKE_PROFIT", row=1, col=1)

    # Đường EMA dùng màu Hổ phách (Amber) và Xanh mờ để phân biệt
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA_20", line=dict(color="#ffb000", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA_50", line=dict(color="#1f521f", width=1.5)), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#33ff00")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff3333", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#33ff00", row=2, col=1)
    
    fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="MACD_HIST", marker_color=["#33ff00" if v >= 0 else "#ff3333" for v in df["MACD_hist"]]), row=3, col=1)
    
    # Chart Theme
    fig.update_layout(
        template="plotly_dark", 
        height=750, 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)", 
        hovermode="x unified", 
        showlegend=False, 
        margin=dict(l=10, r=50, t=30, b=10), 
        dragmode="pan",
        font=dict(family="JetBrains Mono, monospace", color="#33ff00")
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1f521f", rangeslider_visible=False, gridwidth=1, griddash='dot')
    fig.update_yaxes(showgrid=True, gridcolor="#1f521f", side="right", gridwidth=1, griddash='dot')
    
    st.plotly_chart(fig, width='stretch', config={'scrollZoom': True, 'displayModeBar': False})

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH & LỊCH SỬ BOT
# ------------------------------------------------------------
elif menu_selection == "🎯 TRADE_PLANNER":
    st.markdown("### [ MODULE: TRADE_PLANNER ]")
    
    col_slider, _ = st.columns([1, 2])
    with col_slider: 
        rr_ratio = st.slider("Risk:Reward_Ratio", 1.0, 4.0, 2.0, 0.5)
        
    trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
    if trade_plan:
        direction_color = "#33ff00" if trade_plan['direction'] == "LONG" else "#ff3333"
        
        st.markdown(f"""
            <div style='border: 1px solid {direction_color}; padding: 10px; margin-top: 10px; margin-bottom: 20px;'>
                <h3 style='color: {direction_color}; margin: 0;'>SIGNAL: {trade_plan['direction']}</h3>
            </div>
        """, unsafe_allow_html=True)
        
        col_entry, col_sl, col_tp = st.columns(3)
        with col_entry: terminal_metric("ENTRY_PRICE", format_vn_price(trade_plan['entry']), "EXECUTE", is_positive=None)
        with col_sl: terminal_metric("STOP_LOSS", format_vn_price(trade_plan['sl']), "PROTECT_CAPITAL", is_positive=False)
        with col_tp: terminal_metric("TAKE_PROFIT", format_vn_price(trade_plan['tp']), "TARGET_PROFIT", is_positive=True)

    # --- PHẦN BOT TRADING HISTORY ---
    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    col_bot_title, col_bot_btn = st.columns([3, 1])
    with col_bot_title:
        st.markdown("### [ BOT: TRADE_HISTORY ]")
    with col_bot_btn:
        if st.button("update_bot", key="reload_bot_btn"):
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
            <div style='border: 1px dashed #ffb000; padding: 10px; margin-bottom: 15px;'>
                <div style='color: #ffb000; font-weight: bold; margin-bottom: 5px;'>[!] BOT ACTIVE: {active_bot['direction']}</div>
                <div style='color: #33ff00; font-size: 13px;'>ENTRY: {format_vn_price(active_bot['entry_price'])} | 
                SL: <span style='color:#ff3333'>{format_vn_price(active_bot['sl'])}</span> | 
                TP: <span style='color:#33ff00'>{format_vn_price(active_bot['tp'])}</span></div>
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
            if val == 'WIN': return 'color: #33ff00; font-weight: bold;'
            if val == 'LOSS': return 'color: #ff3333; font-weight: bold;'
            if val == 'CUT_EARLY': return 'color: #ffb000; font-weight: bold;' 
            if val == 'ACTIVE': return 'color: #33ff00; text-decoration: underline;'
            return ''

        styled_bot_df = display_df[['open_time', 'close_time', 'direction', 'entry_price', 'exit_price', 'sl', 'tp', 'status', 'reason']].style \
            .map(color_bot_status, subset=['status'])
            
        st.dataframe(styled_bot_df, hide_index=True, width='stretch')
        
        st.markdown("""
        <div style='font-size: 11px; color: #1f521f; margin-top: 10px;'>
            <strong>LOGIC:</strong> Executes on EMA/RSI/MACD confluence + ADX > 20. Auto-manages SL, TP, and Early Cuts on EMA cross. Implements cooldown period to prevent overtrading.
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 3: SMC
# ------------------------------------------------------------
elif menu_selection == "🧠 SMC_ANALYSIS":
    st.markdown("### [ MODULE: SMC_ANALYSIS ]")
    st.info("> ANALYZING SMART MONEY CONCEPTS... [PENDING IMPLEMENTATION]")

# ------------------------------------------------------------
# KHU VỰC 4: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 NEWS_FEED":
    st.markdown(f"### [ MODULE: NEWS_FEED // {selected_asset.split(' - ')[1]} ]")
    news = fetch_news(ticker)
    
    for item in news:
        st.markdown(f"""
            <div style='border-left: 3px solid #33ff00; padding-left: 15px; margin-bottom: 15px;'>
                <div style='margin-bottom: 5px;'>
                    <a href='{item['link']}' target='_blank' style='color: #33ff00; text-decoration: none; font-weight: bold;'>[READ_MORE]</a>
                    <span style='color: #33ff00;'>{item['title']}</span>
                </div>
                <div style='color: #1f521f; font-size: 12px;'>TIMESTAMP: {item['published']}</div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 5: NHẬT KÝ GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "📓 TRADE_JOURNAL":
    st.markdown("### [ MODULE: MANUAL_TRADE_JOURNAL ]")
    
    col_form, col_history = st.columns([1, 2], gap="large")
    
    with col_form:
        st.markdown("<div style='border: 1px dashed #1f521f; padding: 15px;'>", unsafe_allow_html=True)
        with st.form("journal_form", clear_on_submit=True):
            st.markdown("<p style='color: #33ff00; font-weight: bold; margin-bottom: 15px;'>+--- INPUT NEW TRADE ---+</p>", unsafe_allow_html=True)
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
                    if val == 'WIN': return 'color: #33ff00; font-weight: bold;'
                    elif val == 'LOSS': return 'color: #ff3333; font-weight: bold;'
                    return 'color: #1f521f;'
                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #33ff00;'
                        elif val < 0: return 'color: #ff3333;'
                    except: pass
                    return 'color: #1f521f;'

                styled_df = filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style \
                    .map(color_result, subset=['result']) \
                    .map(color_pnl, subset=['pnl'])
                
                st.dataframe(styled_df, hide_index=True, width='stretch')
