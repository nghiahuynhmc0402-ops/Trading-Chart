import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from ta.trend import EMAIndicator, SMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

# ============================================================
# CẤU HÌNH GIAO DIỆN TRADINGVIEW (DARK THEME)
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro | TradingView Clone",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS tùy chỉnh để giống nền tảng trading chuyên nghiệp
st.markdown("""
    <style>
    .stApp { background-color: #131722; color: #d1d4dc; }
    .css-1d391kg { background-color: #1e222d; }
    .stTextInput>div>div>input { color: #d1d4dc; background-color: #2a2e39; }
    .stSelectbox>div>div>div { color: #d1d4dc; background-color: #2a2e39; }
    h1, h2, h3 { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# TỪ ĐIỂN ÁNH XẠ TÀI SẢN (ASSET MAPPING)
# ============================================================
ASSET_MAP = {
    # Hàng hóa (Commodities)
    "XAUUSD": "GC=F", "VÀNG": "GC=F", "GOLD": "GC=F",
    "XAGUSD": "SI=F", "BẠC": "SI=F", "SILVER": "SI=F",
    "WTI": "CL=F", "DẦU": "CL=F", "OIL": "CL=F",
    # Crypto
    "BTCUSD": "BTC-USD", "BTC": "BTC-USD",
    "ETHUSD": "ETH-USD", "ETH": "ETH-USD",
    "SOLUSD": "SOL-USD", "SOL": "SOL-USD",
    # Forex
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    # Chỉ số
    "SPX": "^GSPC", "US30": "^DJI", "NAS100": "^IXIC",
}

def get_yf_ticker(user_input: str) -> tuple:
    """Chuyển đổi mã người dùng nhập sang mã Yahoo Finance và nhận diện loại tài sản."""
    ticker = user_input.upper().strip()
    
    # 1. Kiểm tra trong từ điển ánh xạ trước
    if ticker in ASSET_MAP:
        return ASSET_MAP[ticker], "Hàng hóa/Forex/Crypto"
    
    # 2. Tự động nhận diện nếu người dùng nhập mã chưa có trong từ điển
    if ticker.endswith("=F"): return ticker, "Hàng hóa"
    if ticker.endswith("-USD"): return ticker, "Crypto"
    if ticker.endswith("=X"): return ticker, "Forex"
    if ticker.startswith("^"): return ticker, "Chỉ số"
    
    return ticker, "Cổ phiếu / Khác"

# ============================================================
# HÀM TẢI DỮ LIỆU ĐA KHUNG THỜI GIAN
# ============================================================
@st.cache_data(ttl=60, show_spinner="Đang tải dữ liệu từ thị trường...")
def load_data(ticker: str, interval: str):
    """Tự động tính toán khoảng thời gian (period) phù hợp với khung (interval)."""
    # Yahoo Finance giới hạn dữ liệu intraday (1m, 5m, 15m, 1h)
    period = "1y" 
    if interval in ["1m", "2m", "5m", "15m", "30m", "60m", "90m"]:
        period = "5d" if interval == "1m" else "1mo"
    elif interval in ["1d", "5d"]:
        period = "2y"
    elif interval in ["1wk", "1mo"]:
        period = "5y"

    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty:
            return None
        
        # Làm phẳng MultiIndex nếu có
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.reset_index(inplace=True)
        
        # Chuẩn hóa cột thời gian
        time_col = "Datetime" if "Datetime" in df.columns else "Date"
        df.rename(columns={time_col: "Time"}, inplace=True)
        df["Time"] = pd.to_datetime(df["Time"])
        
        # Loại bỏ các dòng NaN ở giá đóng cửa
        df = df.dropna(subset=["Close"])
        return df
    except Exception as e:
        return None

# ============================================================
# HÀM TÍNH TOÁN CHỈ BÁO
# ============================================================
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close, high, low = df["Close"], df["High"], df["Low"]

    # Xu hướng
    df["EMA20"] = EMAIndicator(close=close, window=20).ema_indicator()
    df["EMA50"] = EMAIndicator(close=close, window=50).ema_indicator()
    df["SMA200"] = SMAIndicator(close=close, window=200).sma_indicator()

    # Động lượng
    df["RSI"] = RSIIndicator(close=close, window=14).rsi()
    macd = MACD(close=close)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()
    
    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    # Biến động & Sức mạnh
    bb = BollingerBands(close=close, window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
    
    df["ATR"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    
    adx = ADXIndicator(high=high, low=low, close=close, window=14)
    df["ADX"] = adx.adx()
    df["DI_plus"] = adx.adx_pos()
    df["DI_minus"] = adx.adx_neg()

    return df

# ============================================================
# HÀM ĐIỂM ĐỒNG QUY (CONFLUENCE ENGINE)
# ============================================================
def get_confluence_score(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    scores = {}

    # 1. Xu hướng (-2 đến +2)
    trend = 0
    if not pd.isna(last["EMA20"]) and not pd.isna(last["EMA50"]):
        trend += 1 if last["EMA20"] > last["EMA50"] else -1
    if not pd.isna(last["SMA200"]):
        trend += 1 if last["Close"] > last["SMA200"] else -1
    scores["Xu hướng"] = trend

    # 2. Động lượng (-3 đến +3)
    momentum = 0
    if last["RSI"] > 55: momentum += 1
    elif last["RSI"] < 45: momentum -= 1

    if last["MACD_hist"] > 0 and last["MACD"] > last["MACD_signal"]: momentum += 1
    elif last["MACD_hist"] < 0 and last["MACD"] < last["MACD_signal"]: momentum -= 1

    if last["Stoch_K"] > 50 and last["Stoch_K"] > last["Stoch_D"]: momentum += 1
    elif last["Stoch_K"] < 50 and last["Stoch_K"] < last["Stoch_D"]: momentum -= 1
    scores["Động lượng"] = momentum

    # 3. Biến động (-1 đến +1)
    volatility = 0
    if last["Close"] > last["BB_upper"]: volatility = 1
    elif last["Close"] < last["BB_lower"]: volatility = -1
    scores["Biến động"] = volatility

    # 4. Sức mạnh (-1 đến +1)
    strength = 0
    if last["DI_plus"] > last["DI_minus"]: strength = 1
    elif last["DI_minus"] > last["DI_plus"]: strength = -1
    scores["Sức mạnh"] = strength

    total = sum(scores.values())

    if total >= 4: label, color = "MUA MẠNH", "green"
    elif total >= 2: label, color = "NGHIÊNG MUA", "lightgreen"
    elif total <= -4: label, color = "BÁN MẠNH", "red"
    elif total <= -2: label, color = "NGHIÊNG BÁN", "lightcoral"
    else: label, color = "TRUNG LẬP", "gray"

    return {"scores": scores, "total": total, "label": label, "color": color}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>📈 TradeDesk Pro</h2>", unsafe_allow_html=True)
    st.caption("TradingView Clone & Multi-Timeframe Analysis")
    st.divider()

    raw_ticker = st.text_input("Mã tài sản (VD: XAUUSD, BTCUSD, AAPL)", value="XAUUSD").upper().strip()
    ticker, asset_type = get_yf_ticker(raw_ticker)
    st.info(f"Đang phân tích: **{ticker}** ({asset_type})")

    # Đa khung thời gian
    timeframes = {
        "1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", 
        "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"
    }
    selected_tf_name = st.selectbox("Khung thời gian", list(timeframes.keys()), index=4)
    interval = timeframes[selected_tf_name]

    st.divider()
    st.subheader("Cài đặt Quản lý Rủi ro")
    risk_mult = st.slider("Hệ số ATR (Stop-loss)", 0.5, 3.0, 1.5, 0.1)
    
    st.divider()
    st.caption("Dữ liệu từ Yahoo Finance. Không phải lời khuyên đầu tư.")

# ============================================================
# XỬ LÝ DỮ LIỆU CHÍNH
# ============================================================
df = load_data(ticker, interval)

if df is None or len(df) < 20:
    st.error(f"❌ Không lấy được dữ liệu cho **{raw_ticker}** (Mã YF: {ticker}). Hãy thử mã khác hoặc khung thời gian dài hơn.")
    st.stop()

df = compute_indicators(df)
signal = get_confluence_score(df)
last_close = df["Close"].iloc[-1]
prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_close
change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

# ============================================================
# KHU VỰC HEADER (KPI)
# ============================================================
st.markdown(f"### {raw_ticker} ({ticker}) - {selected_tf_name}")
kpi_cols = st.columns(5)
kpi_cols[0].metric("Giá hiện tại", f"{last_close:,.2f}", f"{change_pct:+.2f}%")
kpi_cols[1].metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}")
kpi_cols[2].metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}")
kpi_cols[3].metric("ATR (14)", f"{df['ATR'].iloc[-1]:,.2f}")
kpi_cols[4].metric("Điểm đồng quy", f"{signal['total']:+d}", signal['label'])

# ============================================================
# TABS
# ============================================================
tab_chart, tab_signal, tab_risk = st.tabs(["📊 Biểu đồ (TradingView Style)", "🎯 Tín hiệu & Đồng quy", "🛡️ Quản lý rủi ro"])

# ------------------------------------------------------------
# TAB 1: BIỂU ĐỒ (GIAO DIỆN TRADINGVIEW)
# ------------------------------------------------------------
with tab_chart:
    # Tạo 3 hàng: Giá, RSI, MACD (giống layout TradingView)
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("", "RSI (14)", "MACD (12, 26, 9)")
    )

    # Hàng 1: Nến + EMA + Bollinger Bands
    fig.add_trace(go.Candlestick(
        x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Giá", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350"
    ), row=1, col=1)
    
    # Dải Bollinger (làm mờ)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["BB_upper"], name="BB Upper", line=dict(color="rgba(255,165,0,0.4)", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["BB_lower"], name="BB Lower", line=dict(color="rgba(255,165,0,0.4)", width=1), fill="tonexty", fillcolor="rgba(255,165,0,0.05)"), row=1, col=1)
    
    # EMA
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA 20", line=dict(color="#2196f3", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA 50", line=dict(color="#9c27b0", width=1.5)), row=1, col=1)

    # Hàng 2: RSI
    fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#e91e63", width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # Hàng 3: MACD
    fig.add_trace(go.Scatter(x=df["Time"], y=df["MACD"], name="MACD", line=dict(color="#ff9800", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["MACD_signal"], name="Signal", line=dict(color="#f44336", width=1.5)), row=3, col=1)
    macd_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"]]
    fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="Histogram", marker_color=macd_colors, opacity=0.6), row=3, col=1)

    # Cấu hình layout Dark Theme chuẩn TradingView
    fig.update_layout(
        template="plotly_dark",
        height=800,
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False, # Tắt slider mặc định của hàng 1
    )
    
    # Thêm thanh trượt (Range Slider) ở dưới cùng giống TradingView
    fig.update_xaxes(
        showgrid=True, gridcolor="rgba(128,128,128,0.1)",
        rangeslider=dict(visible=False), # Tắt ở tất cả các hàng
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1D", step="day", stepmode="backward"),
                dict(count=7, label="1W", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(step="all", label="ALL")
            ]),
            bgcolor="#2a2e39", activecolor="#2962ff", font=dict(color="#d1d4dc")
        ),
        row=1, col=1
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.1)")

    # Hiển thị biểu đồ (cho phép người dùng kéo thả, zoom)
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# ------------------------------------------------------------
# TAB 2: TÍN HIỆU
# ------------------------------------------------------------
with tab_signal:
    st.subheader("Phân tích Điểm đồng quy (Confluence)")
    st.caption("Điểm tổng hợp từ 4 lớp tín hiệu. Điểm càng cao càng Bullish, càng thấp càng Bearish.")
    
    score_cols = st.columns(4)
    for i, (layer, sc) in enumerate(signal["scores"].items()):
        color = "normal" if sc == 0 else ("inverse" if sc < 0 else "off")
        score_cols[i].metric(layer, f"{sc:+d}")
        
    st.divider()
    st.markdown(f"### Trạng thái: :{signal['color']}[{signal['label']}] (Tổng: {signal['total']:+d})")

    with st.expander("🔍 Xem chi tiết cách tính điểm"):
        detail_df = pd.DataFrame({
            "Lớp tín hiệu": list(signal["scores"].keys()),
            "Điểm": [f"{v:+d}" for v in signal["scores"].values()],
            "Logic": [
                "EMA20 vs EMA50 và Vị trí giá so với SMA200",
                "RSI, MACD Histogram, Stochastic %K vs %D",
                "Vị trí giá so với dải Bollinger Bands",
                "Sức mạnh xu hướng (DI+ vs DI-)"
            ]
        })
        st.dataframe(detail_df, hide_index=True, use_container_width=True)

# ------------------------------------------------------------
# TAB 3: QUẢN LÝ RỦI RO
# ------------------------------------------------------------
with tab_risk:
    st.subheader("Tính toán Stop-Loss & Take-Profit (Dựa trên ATR)")
    
    atr = df["ATR"].iloc[-1]
    score = signal["total"]
    
    if score > 0:
        direction, color = "LONG (MUA)", "green"
        sl, tp = last_close - (risk_mult * atr), last_close + (2 * risk_mult * atr)
    elif score < 0:
        direction, color = "SHORT (BÁN)", "red"
        sl, tp = last_close + (risk_mult * atr), last_close - (2 * risk_mult * atr)
    else:
        direction, color = "NEUTRAL (ĐỨNG NGOÀI)", "gray"
        sl, tp = None, None

    st.markdown(f"### Khuyến nghị: :{color}[{direction}]")
    
    if sl and tp:
        risk = abs(last_close - sl)
        reward = abs(tp - last_close)
        rr_ratio = reward / risk if risk > 0 else 0
        
        cols = st.columns(4)
        cols[0].metric("Giá vào lệnh", f"{last_close:,.2f}")
        cols[1].metric("Stop-Loss", f"{sl:,.2f}", f"{sl - last_close:+.2f}", delta_color="inverse")
        cols[2].metric("Take-Profit", f"{tp:,.2f}", f"{tp - last_close:+.2f}", delta_color="normal")
        cols[3].metric("Tỷ lệ R:R", f"1 : {rr_ratio:.2f}")
        
        st.info(f"**Công thức:**  \n- Stop-Loss = Giá ± {risk_mult} × ATR  \n- Take-Profit = Giá ± 2 × {risk_mult} × ATR")
    else:
        st.info("Hệ thống đang ở trạng thái trung lập, chưa có tín hiệu vào lệnh an toàn. Hãy kiên nhẫn chờ đợi.")