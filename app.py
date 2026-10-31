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
# 1. CẤU HÌNH GIAO DIỆN & CSS (QUANTUM GLASS - NGHIA_TRADING)
# ============================================================
st.set_page_config(
    page_title="Nghia_Trading | Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp { 
        background-color: #050505;
        background-image: radial-gradient(circle at 15% 50%, rgba(99, 102, 241, 0.05), transparent 25%), radial-gradient(circle at 85% 30%, rgba(16, 185, 129, 0.05), transparent 25%);
        color: #e4e4e7 !important; 
        font-family: 'Inter', sans-serif;
    }
    
    .stPlotlyChart { touch-action: pan-y pinch-zoom !important; }

    [data-testid="stSidebar"] { 
        background: rgba(9, 9, 11, 0.6) !important; 
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Menu */
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 6px !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label { 
        padding: 12px 16px !important; border-radius: 10px !important; cursor: pointer !important; 
        width: 100% !important; background-color: transparent !important; border: 1px solid transparent;
        color: #71717a !important; transition: all 0.2s ease; margin-bottom: 2px;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { background-color: rgba(255, 255, 255, 0.03) !important; color: #e4e4e7 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] { 
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.15) 0%, rgba(99, 102, 241, 0) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.2); border-left: 3px solid #6366f1 !important;
        color: #ffffff !important; font-weight: 600 !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p { font-size: 14px !important; font-weight: 500 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
    
    /* Inputs */
    .stSelectbox div[data-baseweb="select"], .stTextInput input, .stNumberInput input, .stTextArea textarea { 
        background-color: rgba(255, 255, 255, 0.03) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; 
        border-radius: 8px !important; color: #e4e4e7 !important; font-family: 'Inter', sans-serif !important; transition: all 0.2s ease;
    }
    .stSelectbox div[data-baseweb="select"]:hover, .stTextInput input:hover { border-color: rgba(255, 255, 255, 0.2) !important; }
    .stSelectbox div[data-baseweb="select"]:focus-within, .stTextInput input:focus { 
        border-color: #6366f1 !important; box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }
    
    /* Buttons */
    .stButton>button { 
        width: 100%; border-radius: 8px !important; background: #6366f1 !important; color: #ffffff !important; 
        border: none !important; font-family: 'Inter', sans-serif !important; font-weight: 600; padding: 10px; transition: all 0.3s ease;
    }
    .stButton>button:hover { background: #4f46e5 !important; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4); transform: translateY(-1px); }
    
    /* Dataframe */
    [data-testid="stDataFrame"] { border-radius: 12px !important; border: 1px solid rgba(255, 255, 255, 0.05) !important; background-color: rgba(255, 255, 255, 0.02) !important; }
    
    /* Titles & Headers */
    h1, h2, h3 { color: #ffffff !important; font-family: 'Inter', sans-serif !important; font-weight: 700 !important; letter-spacing: -0.5px; }
    .sidebar-header { padding: 10px 0 20px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 20px; display: flex; align-items: center; gap: 12px; }
    .sidebar-logo { width: 36px; height: 36px; background: linear-gradient(135deg, #6366f1, #a855f7); border-radius: 10px; display: flex; justify-content: center; align-items: center; color: #fff; box-shadow: 0 0 15px rgba(99, 102, 241, 0.4); }
    .sidebar-title { font-size: 18px; font-weight: 700; color: #ffffff; margin: 0; }
    .sidebar-subtitle { font-size: 11px; color: #71717a; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
    .menu-label { color: #71717a; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; margin-top: 10px; padding-left: 10px; }
    
    /* Cards */
    .glass-card { background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px; transition: transform 0.2s ease, box-shadow 0.2s ease; }
    .glass-card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3); }
    .card-title { color: #ffffff; font-weight: 600; font-size: 15px; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px; }
    .row-item { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; color: #a1a1aa; }
    .val-data { color: #e4e4e7; font-weight: 600; font-family: 'JetBrains Mono', monospace;}
    .val-up { color: #10b981; }
    .val-down { color: #f43f5e; }
    .pro-card { background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1)); border-radius: 12px; padding: 15px; margin-top: 20px; border: 1px solid rgba(99, 102, 241, 0.2); }
    .pro-card h4 { margin: 0 0 5px 0; font-size: 14px; color: #fff; }
    .pro-card p { margin: 0; font-size: 12px; color: #a1a1aa; }
    .copyright { text-align: center; color: #52525b; font-size: 11px; margin-top: 30px; padding-top: 15px; border-top: 1px dashed rgba(255,255,255,0.05); }
    
    /* Hide Streamlit's default empty container spacing */
    div[data-testid="stVerticalBlock"] > div:has(> div.element-container:only-child > .stMarkdown:empty) { display: none; }
    
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
# 3. UI COMPONENTS & LOGIC
# ============================================================
def format_vn_price(value) -> str:
    if pd.isna(value) or value is None: return "N/A"
    try: return f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except: return str(value)

def quantum_metric(label, value_str, delta_text=None, is_positive=None):
    border_color = "rgba(255,255,255,0.05)"
    text_color = "#ffffff"
    delta_color = "#a1a1aa"
    glow = "rgba(255,255,255,0.02)"
    
    if is_positive is not None:
        text_color = "#10b981" if is_positive else "#f43f5e"
        delta_color = "#10b981" if is_positive else "#f43f5e"
        border_color = "rgba(16, 185, 129, 0.2)" if is_positive else "rgba(244, 63, 94, 0.2)"
        glow = "rgba(16, 185, 129, 0.05)" if is_positive else "rgba(244, 63, 94, 0.05)"
        
    delta_html = ""
    if delta_text:
        if is_positive is None:
            delta_color = "#10b981" if ("+" in str(delta_text) or "MUA" in str(delta_text)) else ("#f43f5e" if ("-" in str(delta_text) or "BÁN" in str(delta_text)) else "#a1a1aa")
        delta_html = f"<div style='color: {delta_color}; font-size: 13px; font-weight: 600; margin-top: 8px; display: flex; align-items: center; gap: 4px;'>{delta_text}</div>"
        
    html_code = f"""
    <div style="background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%); backdrop-filter: blur(10px); padding: 18px 20px; border-radius: 12px; border: 1px solid {border_color}; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255,255,255,0.05); font-family: 'Inter', sans-serif; position: relative; min-height: 105px; display: flex; flex-direction: column; justify-content: center;">
        <div style="color: #71717a; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">{label}</div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: {text_color}; font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 700; line-height: 1; text-shadow: 0 0 10px {glow};">{value_str}</span>
            <button onclick="navigator.clipboard.writeText('{value_str}'); this.innerHTML='<svg width=\\'16\\' height=\\'16\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'#10b981\\' stroke-width=\\'2\\'><polyline points=\\'20 6 9 17 4 12\\'></polyline></svg>'; setTimeout(() => this.innerHTML='<svg width=\\'16\\' height=\\'16\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'#71717a\\' stroke-width=\\'2\\'><rect x=\\'9\\' y=\\'9\\' width=\\'13\\' height=\\'13\\' rx=\\'2\\' ry=\\'2\\'></rect><path d=\\'M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1\\'></path></svg>', 2000);" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; cursor: pointer; padding: 6px; display: flex; align-items: center; justify-content: center; transition: 0.2s;" title="Copy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#71717a" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            </button>
        </div>
        {delta_html}
    </div>
    """
    components.html(html_code, height=120)

def get_trade_diagnosis(df, trade_plan):
    """Hàm chuẩn đoán chất lượng lệnh (Trade Quality Score) và lý do"""
    last = df.iloc[-1]
    score = 0
    reasons = []
    
    # 1. Xu hướng (30đ)
    if trade_plan['direction'] == "LONG":
        if last['EMA20'] > last['EMA50']:
            score += 30
            reasons.append("🟢 **Xu hướng:** EMA20 > EMA50 (Uptrend).")
        else:
            reasons.append("🔴 **Xu hướng:** EMA20 < EMA50 (Ngược xu hướng).")
    else:
        if last['EMA20'] < last['EMA50']:
            score += 30
            reasons.append("🟢 **Xu hướng:** EMA20 < EMA50 (Downtrend).")
        else:
            reasons.append("🔴 **Xu hướng:** EMA20 > EMA50 (Ngược xu hướng).")

    # 2. Động lượng (20đ)
    if trade_plan['direction'] == "LONG":
        if 40 < last['RSI'] < 70: score += 10; reasons.append("🟢 **RSI:** Nằm trong vùng an toàn (40-70).")
        if last['MACD_hist'] > 0: score += 10; reasons.append("🟢 **MACD:** Histogram dương (Động lượng tăng).")
    else:
        if 30 < last['RSI'] < 60: score += 10; reasons.append("🟢 **RSI:** Nằm trong vùng an toàn (30-60).")
        if last['MACD_hist'] < 0: score += 10; reasons.append("🟢 **MACD:** Histogram âm (Động lượng giảm).")

    # 3. Sức mạnh xu hướng (20đ)
    if last['ADX'] > 25:
        score += 20
        reasons.append(f"🟢 **ADX ({last['ADX']:.1f}):** Xu hướng mạnh, đáng tin cậy.")
    elif last['ADX'] > 20:
        score += 10
        reasons.append(f"🟡 **ADX ({last['ADX']:.1f}):** Xu hướng hình thành.")
    else:
        reasons.append(f"🔴 **ADX ({last['ADX']:.1f}):** Thị trường đi ngang, dễ nhiễu.")

    # 4. Vị trí so với Bollinger Bands (15đ)
    if trade_plan['direction'] == "LONG" and last['Close'] < last['BB_lower']: 
        score += 15; reasons.append("🟢 **Bollinger:** Giá chạm dải dưới (Quá bán).")
    elif trade_plan['direction'] == "SHORT" and last['Close'] > last['BB_upper']: 
        score += 15; reasons.append("🟢 **Bollinger:** Giá chạm dải trên (Quá mua).")
    else:
        reasons.append("⚪ **Bollinger:** Giá đang ở giữa dải (Chưa tối ưu).")

    # 5. Đa khung thời gian (15đ) - Sẽ tính ở ngoài hàm này nếu cần, tạm thời để 15đ cố định nếu ADX mạnh
    if last['ADX'] > 25: score += 15 
    
    # Đánh giá
    if score >= 80: quality = "XUẤT SẮC (A+)"
    elif score >= 60: quality = "TỐT (B)"
    elif score >= 40: quality = "TRUNG BÌNH (C)"
    else: quality = "RỦI RO CAO (D)"
    
    return score, quality, reasons

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

@st.cache_data(ttl=300, show_spinner="⏳ ĐANG TẢI DỮ LIỆU CHÍNH...")
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

@st.cache_data(ttl=600, show_spinner="🌐 ĐANG QUÉT ĐA KHUNG THỜI GIAN...")
def load_mtf_data(ticker: str):
    mtf_trends = {}
    intervals = {"15m": "15 Phút", "60m": "1 Giờ", "1d": "1 Ngày"}
    for interval, name in intervals.items():
        try:
            df = yf.download(ticker, period="1mo", interval=interval, progress=False, auto_adjust=True)
            if not df.empty and len(df) > 50:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df["EMA20"] = EMAIndicator(close=df["Close"], window=20).ema_indicator()
                df["EMA50"] = EMAIndicator(close=df["Close"], window=50).ema_indicator()
                last = df.iloc[-1]
                mtf_trends[name] = "TĂNG" if last["EMA20"] > last["EMA50"] else "GIẢM"
            else:
                mtf_trends[name] = "N/A"
        except:
            mtf_trends[name] = "N/A"
    return mtf_trends

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
    bb = BollingerBands(close=df["Close"], window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
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
    return {"direction": direction, "entry": entry, "sl": sl, "tp": tp, "atr": atr}

def calculate_fibonacci(df: pd.DataFrame) -> dict:
    if len(df) < 100: return None
    recent_df = df.tail(100)
    swing_high = recent_df["High"].max()
    swing_low = recent_df["Low"].min()
    diff = swing_high - swing_low
    return {
        "Swing High": swing_high, "Swing Low": swing_low,
        "Fib 0.236": swing_high - (diff * 0.236), "Fib 0.382": swing_high - (diff * 0.382),
        "Fib 0.500": swing_high - (diff * 0.500), "Fib 0.618": swing_high - (diff * 0.618),
        "Fib 0.786": swing_high - (diff * 0.786)
    }

# ============================================================
# 4. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
        <div class='sidebar-header'>
            <div class='sidebar-logo'>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>
            </div>
            <div>
                <h2 class='sidebar-title'>Nghia_Trading</h2>
                <div class='sidebar-subtitle'>Terminal UI</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='color: #71717a; font-size: 12px; margin-bottom: 5px; font-weight: 500;'>Tài sản giao dịch</p>", unsafe_allow_html=True)
    selected_asset = st.selectbox("Asset", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #71717a; font-size: 12px; margin-bottom: 5px; font-weight: 500;'>Khung thời gian (Biểu đồ)</p>", unsafe_allow_html=True)
    timeframe = st.selectbox("TF", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}[timeframe]
    
    if st.button("🔄 Cập nhật dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 20px 0;'>", unsafe_allow_html=True)
    st.markdown("<div class='menu-label'>Menu</div>", unsafe_allow_html=True)
    menu_selection = st.radio("Menu", ["📊 Biểu đồ", "🎯 Kế hoạch giao dịch", "🧠 Phân tích SMC", "🌐 Đa Khung Thời Gian", "📏 Fibonacci", "📰 Tin tức", "📓 Nhật ký"], label_visibility="collapsed")
    
    st.markdown("""
        <div style='margin-top: 20px;'>
            <div class='pro-card'>
                <h4>Nghia_Trading Pro</h4>
                <p>Mở khóa tính năng Bot AI và dữ liệu Realtime.</p>
            </div>
            <div class='copyright'>
                © 2024 Nghia_Trading.<br>All rights reserved.
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================
# 5. MAIN AREA
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
    <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px;'>
        <div>
            <h1 style='margin: 0; font-size: 28px; color: #ffffff;'>{selected_asset.split(' - ')[1]}</h1>
            <p style='margin: 0; color: #71717a; font-size: 14px; font-weight: 500;'>{ticker} • {timeframe}</p>
        </div>
        <div style='background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); padding: 6px 12px; border-radius: 20px; display: flex; align-items: center; gap: 8px;'>
            <div style='width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981;'></div>
            <span style='color: #10b981; font-size: 13px; font-weight: 600;'>Thị trường mở</span>
        </div>
    </div>
""", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: quantum_metric("GIÁ HIỆN TẠI", format_vn_price(last_close), f"{change_pct:+.2f}%", is_positive=(change_pct >= 0))
with kpi2: quantum_metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}", "QUÁ MUA" if df['RSI'].iloc[-1]>70 else ("QUÁ BÁN" if df['RSI'].iloc[-1]<30 else "TRUNG TÍNH"), is_positive=(df['RSI'].iloc[-1]<70))
with kpi3: quantum_metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}", "XU HƯỚNG MẠNH" if df['ADX'].iloc[-1]>25 else "ĐI NGANG", is_positive=None)
with kpi4: quantum_metric("ATR (14)", format_vn_price(df['ATR'].iloc[-1]), "ĐỘ BIẾN ĐỘNG", is_positive=None)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 1: BIỂU ĐỒ
# ------------------------------------------------------------
if menu_selection == "📊 Biểu đồ":
    chart_df = df.tail(300).copy()
    
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI (14)", "MACD (12, 26, 9)"))
    
    fig.add_trace(go.Candlestick(
        x=chart_df["Time"], open=chart_df["Open"], high=chart_df["High"], low=chart_df["Low"], close=chart_df["Close"], name="PRICE", 
        increasing_line_color="#10b981", decreasing_line_color="#f43f5e",
        increasing_fillcolor="#10b981", decreasing_fillcolor="#f43f5e"
    ), row=1, col=1)
    
    active_trade = get_active_bot_trade(ticker)
    if active_trade is not None:
        fig.add_hline(y=active_trade['entry_price'], line_dash="solid", line_color="#6366f1", line_width=1.5, annotation_text="ENTRY", row=1, col=1)
        fig.add_hline(y=active_trade['sl'], line_dash="dash", line_color="#f43f5e", line_width=1, annotation_text="SL", row=1, col=1)
        fig.add_hline(y=active_trade['tp'], line_dash="dash", line_color="#10b981", line_width=1, annotation_text="TP", row=1, col=1)

    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["EMA20"], name="EMA 20", line=dict(color="#6366f1", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["EMA50"], name="EMA 50", line=dict(color="#a1a1aa", width=1.5, dash='dot')), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["RSI"], name="RSI", line=dict(color="#a1a1aa", width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#f43f5e", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=2, col=1)
    
    fig.add_trace(go.Bar(x=chart_df["Time"], y=chart_df["MACD_hist"], name="MACD", marker_color=["#10b981" if v >= 0 else "#f43f5e" for v in chart_df["MACD_hist"]]), row=3, col=1)
    
    fig.update_layout(
        template="plotly_dark", height=700, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
        hovermode="x", showlegend=False, margin=dict(l=10, r=50, t=30, b=10), dragmode="pan",
        font=dict(family="Inter, sans-serif", color="#a1a1aa", size=12), uirevision='constant'
    )
    
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", gridwidth=1, rangeslider_visible=False)
    fig.update_xaxes(rangeslider=dict(visible=True, bgcolor="rgba(255,255,255,0.02)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1), row=3, col=1)
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1D", step="day", stepmode="backward"),
                dict(count=7, label="1W", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(step="all", label="TẤT CẢ")
            ]),
            bgcolor="rgba(255,255,255,0.05)", activecolor="#6366f1", font=dict(color="#a1a1aa")
        ), row=1, col=1
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", side="right", gridwidth=1)
    
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})
    st.caption("💡 **Mẹo di động:** Dùng 2 ngón tay để phóng to/thu nhỏ. Dùng 1 ngón tay để kéo biểu đồ. Hoặc dùng thanh trượt ở dưới cùng.")

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH & CHUẨN ĐOÁN
# ------------------------------------------------------------
elif menu_selection == "🎯 Kế hoạch giao dịch":
    st.subheader("Chuẩn đoán & Kế hoạch giao dịch")
    
    col_left, col_right = st.columns([1.5, 1], gap="large")
    
    # --- CỘT TRÁI: KẾ HOẠCH & CHUẨN ĐOÁN ---
    with col_left:
        rr_ratio = st.slider("Tỷ lệ R:R", 1.0, 4.0, 2.0, 0.5)
        trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
        
        if trade_plan:
            direction_color = "#10b981" if trade_plan['direction'] == "LONG" else "#f43f5e"
            direction_vn = "MUA (LONG)" if trade_plan['direction'] == "LONG" else "BÁN (SHORT)"
            
            # Chuẩn đoán chất lượng
            score, quality, reasons = get_trade_diagnosis(df, trade_plan)
            
            st.markdown(f"""
                <div style='background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; margin-bottom: 20px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;'>
                        <h3 style='margin: 0; color: {direction_color};'>Tín hiệu: {direction_vn}</h3>
                        <div style='background: rgba(99, 102, 241, 0.2); color: #a855f7; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 14px;'>
                            Điểm chất lượng: {score}/100 ({quality})
                        </div>
                    </div>
                    <div style='color: #a1a1aa; font-size: 13px; line-height: 1.6;'>
                        {"<br>".join(reasons)}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            col_entry, col_sl, col_tp = st.columns(3)
            with col_entry: quantum_metric("GIÁ VÀO LỆNH", format_vn_price(trade_plan['entry']), "THỰC THI", is_positive=None)
            with col_sl: quantum_metric("CẮT LỖ (SL)", format_vn_price(trade_plan['sl']), "BẢO VỆ VỐN", is_positive=False)
            with col_tp: quantum_metric("CHỐT LỜI (TP)", format_vn_price(trade_plan['tp']), "MỤC TIÊU", is_positive=True)
            
            # Kỳ vọng toán học
            be_wr = (1 / (1 + rr_ratio)) * 100
            st.markdown(f"""
                <div style='background: rgba(255,255,255,0.02); border: 1px dashed rgba(255,255,255,0.1); border-radius: 8px; padding: 15px; margin-top: 15px; font-size: 13px; color: #a1a1aa;'>
                    <strong>Toán học Giao dịch:</strong> Với tỷ lệ R:R = 1:{rr_ratio:.1f}, bạn cần tỷ lệ thắng (Win rate) tối thiểu là <strong>{be_wr:.1f}%</strong> để hòa vốn. Nếu lịch sử của bạn cao hơn mức này, chiến lược này có lãi.
                </div>
            """, unsafe_allow_html=True)

    # --- CỘT PHẢI: MÁY TÍNH VỊ THẾ ---
    with col_right:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>🧮 Máy Tính Vị Thế</div>", unsafe_allow_html=True)
        
        balance = st.number_input("Số dư tài khoản ($)", value=1000.0, step=100.0)
        risk_pct = st.number_input("Rủi ro mỗi lệnh (%)", value=1.0, step=0.5)
        
        if trade_plan:
            risk_amount = balance * (risk_pct / 100)
            sl_distance = abs(trade_plan['entry'] - trade_plan['sl'])
            
            if sl_distance > 0:
                position_size = risk_amount / sl_distance
                leverage = (position_size * trade_plan['entry']) / balance if balance > 0 else 0
                
                st.markdown(f"""
                    <div style='margin-top: 15px; padding-top: 15px; border-top: 1px dashed rgba(255,255,255,0.1);'>
                        <div class='row-item'><span>Tiền rủi ro tối đa:</span> <span class='val-data val-down'>${risk_amount:,.2f}</span></div>
                        <div class='row-item'><span>Khoảng cách SL:</span> <span class='val-data'>{format_vn_price(sl_distance)}</span></div>
                        <div class='row-item' style='margin-top: 10px;'><span style='color: #fff; font-weight: bold;'>Khối lượng (Size):</span> <span class='val-data val-up' style='font-size: 18px;'>{position_size:,.4f}</span></div>
                        <div class='row-item'><span>Đòn bẩy (Leverage) khuyến nghị:</span> <span class='val-data' style='color: #fbbf24;'>x{leverage:.1f}</span></div>
                    </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 30px 0;'>", unsafe_allow_html=True)
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
            <div style='background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 15px; margin-bottom: 20px;'>
                <div style='color: #a855f7; font-weight: 600; margin-bottom: 5px;'>BOT ĐANG GIỮ LỆNH: {dir_vn}</div>
                <div style='color: #e4e4e7; font-size: 14px;'>Vào lệnh: {format_vn_price(active_bot['entry_price'])} | 
                SL: <span style='color:#f43f5e'>{format_vn_price(active_bot['sl'])}</span> | 
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
            if val == 'THUA': return 'color: #f43f5e; font-weight: bold;'
            if val == 'CẮT SỚM': return 'color: #a1a1aa; font-weight: bold;'
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
                trend_color = "#10b981" if trend_val == 1 else ("#f43f5e" if trend_val == -1 else "#a1a1aa")
                
                bos_bull = structure.bos_bullish[-1] if isinstance(structure.bos_bullish, np.ndarray) else structure.bos_bullish
                bos_bear = structure.bos_bearish[-1] if isinstance(structure.bos_bearish, np.ndarray) else structure.bos_bearish
                choch_val = 0
                if hasattr(structure, 'choch'): choch_val = structure.choch[-1] if isinstance(structure.choch, np.ndarray) else structure.choch
                
                col_fvg, col_obs, col_struct = st.columns(3)
                with col_fvg:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='card-title'>📊 Fair Value Gaps</div>
                            <div class='row-item'><span>FVG Tăng:</span> <span class='val-data val-up'>{len(fvg.bullish)}</span></div>
                            <div class='row-item'><span>FVG Giảm:</span> <span class='val-data val-down'>{len(fvg.bearish)}</span></div>
                            <div class='row-item'><span>Đã lấp đầy:</span> <span class='val-data'>{len(fvg.mitigated_50)}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_obs:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='card-title'>📦 Order Blocks</div>
                            <div class='row-item'><span>OB Cầu:</span> <span class='val-data val-up'>{len(obs.bullish_ob)}</span></div>
                            <div class='row-item'><span>OB Cung:</span> <span class='val-data val-down'>{len(obs.bearish_ob)}</span></div>
                            <div class='row-item'><span>OB Phá vỡ:</span> <span class='val-data'>{len(obs.is_breaker)}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_struct:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='card-title'>📈 Cấu Trúc Giá</div>
                            <div class='row-item'><span>Xu hướng:</span> <span class='val-data' style='color: {trend_color};'>{trend_text}</span></div>
                            <div class='row-item'><span>BOS Tăng:</span> <span class='val-data val-up'>{'CÓ' if bos_bull else 'KHÔNG'}</span></div>
                            <div class='row-item'><span>BOS Giảm:</span> <span class='val-data val-down'>{'CÓ' if bos_bear else 'KHÔNG'}</span></div>
                            <div class='row-item'><span>CHOCH:</span> <span class='val-data'>{'CÓ' if choch_val != 0 else 'KHÔNG'}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Lỗi phân tích SMC: {e}")

# ------------------------------------------------------------
# KHU VỰC 4: ĐA KHUNG THỜI GIAN (MTF)
# ------------------------------------------------------------
elif menu_selection == "🌐 Đa Khung Thời Gian":
    st.subheader("Phân Tích Đa Khung Thời Gian (MTF)")
    st.markdown("<p style='color: #a1a1aa; font-size: 14px;'>Hệ thống tự động quét xu hướng dựa trên giao cắt EMA20 và EMA50 trên 3 khung thời gian. Khi cả 3 khung đồng thuận, xác suất thắng sẽ cao hơn.</p>", unsafe_allow_html=True)
    
    mtf_data = load_mtf_data(ticker)
    col1, col2, col3 = st.columns(3)
    
    def render_mtf_card(col, tf_name, trend_val):
        color = "#10b981" if trend_val == "TĂNG" else ("#f43f5e" if trend_val == "GIẢM" else "#a1a1aa")
        icon = "📈" if trend_val == "TĂNG" else ("📉" if trend_val == "GIẢM" else "➖")
        with col:
            st.markdown(f"""
                <div class='glass-card' style='text-align: center; border-top: 3px solid {color};'>
                    <div style='color: #71717a; font-size: 13px; font-weight: 600; letter-spacing: 1px; margin-bottom: 10px;'>{tf_name}</div>
                    <div style='font-size: 40px; margin-bottom: 10px;'>{icon}</div>
                    <div style='color: {color}; font-size: 20px; font-weight: 700;'>{trend_val}</div>
                </div>
            """, unsafe_allow_html=True)
            
    render_mtf_card(col1, "KHUNG 15 PHÚT", mtf_data.get("15 Phút", "N/A"))
    render_mtf_card(col2, "KHUNG 1 GIỜ", mtf_data.get("1 Giờ", "N/A"))
    render_mtf_card(col3, "KHUNG 1 NGÀY", mtf_data.get("1 Ngày", "N/A"))
    
    st.markdown("<br>", unsafe_allow_html=True)
    up_count = list(mtf_data.values()).count("TĂNG")
    down_count = list(mtf_data.values()).count("GIẢM")
    
    if up_count == 3: st.success("🔥 **ĐỒNG QUY TĂNG MẠNH:** Cả 3 khung thời gian đều đang trong xu hướng tăng. Ưu tiên tìm điểm MUA (LONG).")
    elif down_count == 3: st.error("🩸 **ĐỒNG QUY GIẢM MẠNH:** Cả 3 khung thời gian đều đang trong xu hướng giảm. Ưu tiên tìm điểm BÁN (SHORT).")
    else: st.warning("⚠️ **XUNG ĐỘT XU HƯỚNG:** Các khung thời gian chưa đồng nhất. Nên đứng ngoài chờ đợi tín hiệu rõ ràng hơn.")

# ------------------------------------------------------------
# KHU VỰC 5: FIBONACCI
# ------------------------------------------------------------
elif menu_selection == "📏 Fibonacci":
    st.subheader("Fibonacci Retracement (100 nến gần nhất)")
    fib_data = calculate_fibonacci(df)
    
    if fib_data:
        col_info, col_levels = st.columns([1, 2])
        with col_info:
            st.markdown(f"""
                <div class='glass-card'>
                    <div class='card-title'>📍 Điểm Neo (Swing)</div>
                    <div class='row-item'><span>Đỉnh (Swing High):</span> <span class='val-data val-down'>{format_vn_price(fib_data['Swing High'])}</span></div>
                    <div class='row-item'><span>Đáy (Swing Low):</span> <span class='val-data val-up'>{format_vn_price(fib_data['Swing Low'])}</span></div>
                </div>
            """, unsafe_allow_html=True)
        with col_levels:
            st.markdown(f"""
                <div class='glass-card'>
                    <div class='card-title'>📏 Các Mức Hỗ Trợ / Kháng Cự</div>
                    <div class='row-item'><span>Fib 0.236:</span> <span class='val-data'>{format_vn_price(fib_data['Fib 0.236'])}</span></div>
                    <div class='row-item'><span>Fib 0.382:</span> <span class='val-data'>{format_vn_price(fib_data['Fib 0.382'])}</span></div>
                    <div class='row-item'><span>Fib 0.500 (Vàng):</span> <span class='val-data' style='color: #fbbf24;'>{format_vn_price(fib_data['Fib 0.500'])}</span></div>
                    <div class='row-item'><span>Fib 0.618 (Vàng):</span> <span class='val-data' style='color: #fbbf24;'>{format_vn_price(fib_data['Fib 0.618'])}</span></div>
                    <div class='row-item'><span>Fib 0.786:</span> <span class='val-data'>{format_vn_price(fib_data['Fib 0.786'])}</span></div>
                </div>
            """, unsafe_allow_html=True)
        st.info("💡 **Mẹo:** Mức 0.5 và 0.618 (Golden Ratio) là những vùng phản ứng giá rất mạnh. Nếu giá hồi về đây và có tín hiệu đảo chiều, đó là điểm vào lệnh tuyệt vời.")
    else:
        st.warning("Không đủ dữ liệu để tính Fibonacci.")

# ------------------------------------------------------------
# KHU VỰC 6: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 Tin tức":
    st.subheader(f"Tin tức: {selected_asset.split(' - ')[1]}")
    news = fetch_news(ticker)
    for item in news:
        st.markdown(f"""
            <div class='glass-card' style='padding: 15px; margin-bottom: 15px; cursor: pointer;' onclick="window.open('{item['link']}', '_blank')">
                <div style='color: #6366f1; font-weight: 600; font-size: 15px; margin-bottom: 8px;'>{item['title']}</div>
                <div style='color: #71717a; font-size: 12px; display: flex; align-items: center; gap: 5px;'>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    {item['published']}
                </div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 7: NHẬT KÝ GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "📓 Nhật ký":
    st.subheader("Nhật ký giao dịch thủ công")
    col_form, col_history = st.columns([1, 2], gap="large")
    
    with col_form:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
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
                    elif val == 'THUA': return 'color: #f43f5e; font-weight: bold;'
                    return 'color: #a1a1aa;'
                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #10b981;'
                        elif val < 0: return 'color: #f43f5e;'
                    except: pass
                    return 'color: #a1a1aa;'

                st.dataframe(filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style.map(color_result, subset=['result']).map(color_pnl, subset=['pnl']), hide_index=True, use_container_width=True)
