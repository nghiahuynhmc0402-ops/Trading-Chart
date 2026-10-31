import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
from datetime import datetime, timedelta

# Thư viện chỉ báo kỹ thuật
from ta.trend import EMAIndicator, SMAIndicator, MACD, ADXIndicator, IchimokuIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

# Thư viện Smart Money Concepts (SMC)
try:
    import pyvsmc as smc
    HAS_SMC = True
except ImportError:
    HAS_SMC = False

# ============================================================
# 1. CẤU HÌNH GIAO DIỆN & CSS (DEEPSEEK / CHATGPT STYLE)
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #131722 !important; color: #d1d4dc !important; }
    [data-testid="stSidebar"] { background-color: #202123 !important; border-right: 1px solid #2d2d2d; }
    
    /* CSS CHO MENU RADIO BÊN TRÁI */
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 12px !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 15px 20px !important; background-color: #2a2e39 !important; border: 1px solid #363a45 !important;
        border-radius: 10px !important; cursor: pointer !important; transition: all 0.3s ease !important;
        width: 100% !important; display: flex !important; align-items: center !important; margin-bottom: 0px !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { background-color: #3c404d !important; border-color: #2962ff !important; transform: translateY(-2px); }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] { background-color: #1e3a8a !important; border-color: #2962ff !important; box-shadow: 0 4px 6px rgba(41, 98, 255, 0.2); }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p { font-size: 16px !important; font-weight: 600 !important; color: #ffffff !important; }
    
    /* Các CSS khác */
    .stSelectbox div[data-baseweb="select"] { background-color: #2a2e39; border: 1px solid #363a45; border-radius: 8px; }
    .stSelectbox div[data-baseweb="select"] * { color: #ffffff !important; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #2962ff; color: white; border: none; font-weight: bold; padding: 10px; }
    .stButton>button:hover { background-color: #1e53e5; }
    
    div[data-testid="metric-container"] { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2a2e39; }
    div[data-testid="stMetricValue"] { color: #ffffff; font-size: 24px; font-weight: bold; }
    
    .news-card { background-color: #1e222d; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #2962ff; }
    .news-title { color: #ffffff; font-weight: bold; font-size: 16px; }
    .news-meta { color: #787b86; font-size: 12px; }
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CÁC HÀM TIỆN ÍCH (BAO GỒM NÚT COPY TỪNG GIÁ)
# ============================================================
def format_vn_price(value) -> str:
    """Chuyển 77151.83 thành 77.151,83"""
    if pd.isna(value) or value is None:
        return "N/A"
    try:
        us_format = f"{value:,.2f}"
        vn_format = us_format.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        return vn_format
    except:
        return str(value)

def copyable_metric(label, value_str, delta_text=None):
    """Tạo thẻ hiển thị giá trị có kèm nút Copy ở bên cạnh (dùng HTML/JS)."""
    # Xử lý màu sắc cho delta (nếu có)
    delta_html = ""
    if delta_text:
        delta_color = "#26a69a" if "+" in delta_text or "LONG" in delta_text else "#ef5350"
        delta_html = f"<div style='color: {delta_color}; font-size: 14px;'>{delta_text}</div>"
        
    html_code = f"""
    <div style="background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2a2e39; font-family: sans-serif; min-height: 100px;">
        <div style="color: #787b86; font-size: 14px; margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{label}</div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #ffffff; font-size: 24px; font-weight: bold; word-break: break-all;">{value_str}</span>
            <button onclick="navigator.clipboard.writeText('{value_str}'); this.innerText='✅'; setTimeout(() => this.innerText='📋', 2000);"
                    style="background: none; border: none; cursor: pointer; font-size: 20px; padding: 0; margin-left: 5px; transition: 0.2s;" 
                    title="Copy giá trị">
                📋
            </button>
        </div>
        {delta_html}
    </div>
    """
    # Render component với chiều cao cố định để vừa vặn
    components.html(html_code, height=110)

def get_trade_rationale(df, trade_plan):
    """Phân tích các chỉ báo để đưa ra lý do vào lệnh."""
    last = df.iloc[-1]
    reasons = []
    
    if trade_plan['direction'] == "LONG":
        reasons.append("🟢 **Xu hướng tăng (Uptrend):** EMA20 cắt lên trên EMA50, cho thấy động lực tăng giá trong ngắn hạn.")
    else:
        reasons.append("🔴 **Xu hướng giảm (Downtrend):** EMA20 cắt xuống dưới EMA50, cho thấy áp lực bán chiếm ưu thế.")

    rsi_val = last['RSI']
    if rsi_val > 70: reasons.append(f"⚠️ **RSI quá mua ({rsi_val:.1f}):** Cảnh báo khả năng điều chỉnh giảm.")
    elif rsi_val < 30: reasons.append(f"⚠️ **RSI quá bán ({rsi_val:.1f}):** Cảnh báo khả năng bật tăng trở lại.")
    elif 45 <= rsi_val <= 55: reasons.append(f"⚪ **RSI trung tính ({rsi_val:.1f}):** Thị trường tích lũy, chưa có động lượng rõ.")
    elif rsi_val > 50: reasons.append(f"📈 **RSI tích cực ({rsi_val:.1f}):** Động lượng mua chiếm ưu thế.")
    else: reasons.append(f"📉 **RSI tiêu cực ({rsi_val:.1f}):** Động lượng bán chiếm ưu thế.")

    if last['MACD_hist'] > 0 and last['MACD'] > last['MACD_signal']:
        reasons.append("📊 **MACD (Tăng):** Histogram dương và MACD > Signal, xác nhận tín hiệu mua.")
    elif last['MACD_hist'] < 0 and last['MACD'] < last['MACD_signal']:
        reasons.append("📊 **MACD (Giảm):** Histogram âm và MACD < Signal, xác nhận tín hiệu bán.")

    close = last['Close']
    if close > last['BB_upper']: reasons.append("🚀 **Bứt phá Bollinger Bands:** Giá vượt dải trên, bùng nổ biến động.")
    elif close < last['BB_lower']: reasons.append("🩸 **Phá vỡ Bollinger Bands:** Giá dưới dải dưới, áp lực bán tháo mạnh.")
        
    adx_val = last['ADX']
    if adx_val > 25: reasons.append(f"💪 **ADX mạnh ({adx_val:.1f}):** Xu hướng rất vững chắc, xác suất tiếp diễn cao.")
    else: reasons.append(f"😴 **ADX yếu ({adx_val:.1f}):** Thị trường có thể đi ngang, tín hiệu dễ bị nhiễu.")

    return reasons

# ============================================================
# 3. TỪ ĐIỂN TÀI SẢN
# ============================================================
POPULAR_ASSETS = {
    "🔥 Hàng Hóa": {"Vàng (XAUUSD)": "GC=F", "Bạc (XAGUSD)": "SI=F", "Dầu WTI": "CL=F"},
    "₿ Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD"},
    "💵 Forex": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"},
    "🏦 Chỉ Số & CK Mỹ": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "Apple (AAPL)": "AAPL", "Tesla (TSLA)": "TSLA"}
}
flat_assets = {f"{cat} - {name}": tick for cat, assets in POPULAR_ASSETS.items() for name, tick in assets.items()}

# ============================================================
# 4. HÀM XỬ LÝ DỮ LIỆU
# ============================================================
@st.cache_data(ttl=300, show_spinner="⏳ Đang tải dữ liệu thị trường...")
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
    except:
        return None

@st.cache_data(ttl=600, show_spinner="📰 Đang tải tin tức...")
def fetch_news(ticker_name: str):
    search_query = ticker_name.replace(" ", "+")
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={search_query}&region=US&lang=en-US"
    feed = feedparser.parse(url)
    news_items = []
    for entry in feed.entries[:5]:
        news_items.append({"title": entry.title, "link": entry.link, "published": entry.get("published", "N/A")})
    return news_items

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
    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()
    bb = BollingerBands(close=close, window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
    df["ATR"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    adx = ADXIndicator(high=high, low=low, close=close, window=14)
    df["ADX"] = adx.adx()
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
        entry = last["Close"]
        sl = recent_low - (atr * 0.5)
        tp = entry + (entry - sl) * risk_reward
        direction = "LONG"
    else:
        entry = last["Close"]
        sl = recent_high + (atr * 0.5)
        tp = entry - (sl - entry) * risk_reward
        direction = "SHORT"
        
    return {
        "direction": direction, "entry": entry, "sl": sl, "tp": tp,
        "risk_reward": risk_reward, "atr": atr, "recent_high": recent_high, "recent_low": recent_low
    }

# ============================================================
# 5. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white; margin-bottom: 0;'>TradeDesk Pro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #787b86; font-size: 12px;'>Terminal for Professionals</p>", unsafe_allow_html=True)
    st.divider()
    
    st.markdown("**Tài sản giao dịch**")
    selected_asset = st.selectbox("Chọn mã:", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    st.markdown("**Khung thời gian**")
    timeframe = st.selectbox("Chọn nến:", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval_map = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}
    interval = interval_map[timeframe]
    
    if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    
    st.markdown("**Tính năng phân tích**")
    menu_selection = st.radio(
        "Menu",
        [
            "📊 Biểu Đồ Kỹ Thuật",
            "🎯 Kế Hoạch Giao Dịch",
            "🧠 Cấu Trúc Thị Trường (SMC)",
            "📰 Tin Tức & Sự Kiện"
        ],
        label_visibility="collapsed"
    )

# ============================================================
# 6. XỬ LÝ DỮ LIỆU CHÍNH
# ============================================================
df = load_data(ticker, interval)

if df is None or len(df) < 50:
    st.error(f"❌ Không lấy được dữ liệu cho **{selected_asset}**. Hãy thử khung thời gian khác hoặc mã khác.")
    st.stop()

with st.spinner("⚙️ Đang tính toán các chỉ báo..."):
    df = compute_indicators(df)
    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_close
    change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

# ============================================================
# 7. MAIN AREA
# ============================================================
st.markdown(f"### {selected_asset} ({timeframe})")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    copyable_metric("Giá hiện tại", format_vn_price(last_close), f"{change_pct:+.2f}%")
with kpi2:
    rsi_text = "Quá mua" if df['RSI'].iloc[-1]>70 else ("Quá bán" if df['RSI'].iloc[-1]<30 else "Trung tính")
    copyable_metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}", rsi_text)
with kpi3:
    adx_text = "Xu hướng mạnh" if df['ADX'].iloc[-1]>25 else "Đi ngang"
    copyable_metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}", adx_text)
with kpi4:
    copyable_metric("ATR (14)", format_vn_price(df['ATR'].iloc[-1]), "Biến động")

st.divider()

# ------------------------------------------------------------
# KHU VỰC 1: BIỂU ĐỒ
# ------------------------------------------------------------
if menu_selection == "📊 Biểu Đồ Kỹ Thuật":
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("", "RSI (14)", "MACD", "Stochastic (14,3)")
    )

    fig.add_trace(go.Candlestick(x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Giá", increasing_line_color="#26a69a", decreasing_line_color="#ef5350"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["BB_upper"], name="BB Upper", line=dict(color="rgba(255,165,0,0.4)", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["BB_lower"], name="BB Lower", line=dict(color="rgba(255,165,0,0.4)", width=1), fill="tonexty", fillcolor="rgba(255,165,0,0.05)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA 20", line=dict(color="#2196f3", width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA 50", line=dict(color="#9c27b0", width=1.2)), row=1, col=1)

    fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#e91e63", width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef5350", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#26a69a", row=2, col=1)

    fig.add_trace(go.Scatter(x=df["Time"], y=df["MACD"], name="MACD", line=dict(color="#ff9800", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["MACD_signal"], name="Signal", line=dict(color="#f44336", width=1.5)), row=3, col=1)
    fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="Histogram", marker_color=["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"]]), row=3, col=1)

    fig.add_trace(go.Scatter(x=df["Time"], y=df["Stoch_K"], name="%K", line=dict(color="#00bcd4", width=1.2)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Stoch_D"], name="%D", line=dict(color="#ff5722", width=1.2)), row=4, col=1)
    fig.add_hline(y=80, line_dash="dot", line_color="#ef5350", row=4, col=1)
    fig.add_hline(y=20, line_dash="dot", line_color="#26a69a", row=4, col=1)

    fig.update_layout(template="plotly_dark", height=750, paper_bgcolor="#131722", plot_bgcolor="#131722", hovermode="x unified", showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), margin=dict(l=10, r=50, t=30, b=10), dragmode="pan")
    fig.update_xaxes(showgrid=True, gridcolor="#2a2e39", rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="#2a2e39", side="right")

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "🎯 Kế Hoạch Giao Dịch":
    st.subheader("🎯 Thiết Lập Lệnh (Entry - SL - TP)")
    
    col_slider, col_empty = st.columns([2, 2])
    with col_slider:
        rr_ratio = st.slider("Tỷ lệ Risk:Reward", 1.0, 4.0, 2.0, 0.5)
        
    trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
    
    if trade_plan:
        direction_color = "#26a69a" if trade_plan['direction'] == "LONG" else "#ef5350"
        
        st.markdown(f"<h3>Hướng: <span style='color:{direction_color}'>{trade_plan['direction']}</span></h3>", unsafe_allow_html=True)
        
        col_entry, col_sl, col_tp = st.columns(3)
        
        # SỬ DỤNG HÀM COPYABLE_METRIC ĐỂ CÓ NÚT COPY RIÊNG TỪNG GIÁ
        with col_entry:
            copyable_metric("Giá Entry (Market)", format_vn_price(trade_plan['entry']), trade_plan['direction'])
        with col_sl:
            copyable_metric("Stop-Loss (SL)", format_vn_price(trade_plan['sl']))
        with col_tp:
            copyable_metric("Take-Profit (TP)", format_vn_price(trade_plan['tp']))
        
        st.info(f"**Chi tiết:** Swing High 20 nến: {format_vn_price(trade_plan['recent_high'])} | Swing Low 20 nến: {format_vn_price(trade_plan['recent_low'])} | ATR(14): {format_vn_price(trade_plan['atr'])}")
        
        st.divider()
        st.markdown("### 🧐 Phân Tích Yếu Tố Vào Lệnh")
        st.markdown("Dưới đây là các tín hiệu kỹ thuật hệ thống ghi nhận được để đưa ra quyết định này:")
        
        reasons = get_trade_rationale(df, trade_plan)
        for reason in reasons:
            st.markdown(f"- {reason}")
            
        st.warning("⚠️ Lưu ý: Phân tích chỉ mang tính chất tham khảo. Hãy kết hợp với phân tích đa khung thời gian (Top-down) và quản lý vốn chặt chẽ.")

# ------------------------------------------------------------
# KHU VỰC 3: SMC
# ------------------------------------------------------------
elif menu_selection == "🧠 Cấu Trúc Thị Trường (SMC)":
    st.subheader("🧠 Phân Tích Dòng Tiền Thông Minh (SMC)")
    
    if not HAS_SMC:
        st.warning("Thư viện `pyvsmc` chưa được cài đặt. Vui lòng thêm vào requirements.txt.")
    else:
        with st.spinner("🔎 Đang quét cấu trúc thị trường..."):
            try:
                high_arr, low_arr, close_arr, open_arr = df["High"].values, df["Low"].values, df["Close"].values, df["Open"].values
                fvg = smc.detect_fvg(high_arr, low_arr, close=close_arr, compute_mitigation=True)
                obs = smc.detect_order_blocks(open_arr, high_arr, low_arr, close_arr, lookback=5, zone_mode="body")
                structure = smc.detect_structure(high_arr, low_arr, close_arr, window_size=2, break_mode="close")
                
                trend_val = structure.trend[-1] if len(structure.trend) > 0 else 0
                trend_text = "Tăng (Uptrend)" if trend_val == 1 else ("Giảm (Downtrend)" if trend_val == -1 else "Đi ngang")
                trend_color = "#26a69a" if trend_val == 1 else ("#ef5350" if trend_val == -1 else "#787b86")
                
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
                    st.markdown("### 🟩 Fair Value Gaps")
                    st.write(f"- FVG Tăng: **{len(fvg.bullish)}**")
                    st.write(f"- FVG Giảm: **{len(fvg.bearish)}**")
                    st.write(f"- Đã lấp đầy: **{len(fvg.mitigated_50)}**")
                    
                with col_obs:
                    st.markdown("### 🟦 Order Blocks")
                    st.write(f"- OB Tăng (Demand): **{len(obs.bullish_ob)}**")
                    st.write(f"- OB Giảm (Supply): **{len(obs.bearish_ob)}**")
                    st.write(f"- OB Phá vỡ: **{len(obs.is_breaker)}**")
                    
                with col_struct:
                    st.markdown("### 📈 Cấu Trúc Giá")
                    st.markdown(f"- Xu hướng: <span style='color:{trend_color}; font-weight:bold;'>{trend_text}</span>", unsafe_allow_html=True)
                    st.write(f"- BOS Tăng gần nhất: **{'Có' if bos_bull else 'Không'}**")
                    st.write(f"- BOS Giảm gần nhất: **{'Có' if bos_bear else 'Không'}**")
                    st.write(f"- CHOCH (Đảo chiều): **{'Có' if choch_val != 0 else 'Không'}**")
                    
            except Exception as e:
                st.error(f"Lỗi phân tích SMC: {e}")

# ------------------------------------------------------------
# KHU VỰC 4: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 Tin Tức & Sự Kiện":
    st.subheader(f"📰 Tin Tức: {selected_asset.split(' - ')[1]}")
    news = fetch_news(ticker)
    
    if not news:
        st.info("Không có tin tức mới nhất cho tài sản này.")
    else:
        for item in news:
            st.markdown(f"""
                <div class="news-card">
                    <div class="news-title"><a href="{item['link']}" target="_blank" style="color: #64b5f6; text-decoration: none;">{item['title']}</a></div>
                    <div class="news-meta">🕒 {item['published']}</div>
                </div>
            """, unsafe_allow_html=True)
