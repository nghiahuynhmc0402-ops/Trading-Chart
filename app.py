import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.trend import EMAIndicator, SMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

# ============================================================
# 1. CẤU HÌNH GIAO DIỆN & CSS (TRADINGVIEW STYLE)
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed" # Ẩn sidebar để màn hình rộng hơn cho biểu đồ
)

# CSS can thiệp sâu để làm đẹp giao diện Streamlit
st.markdown("""
    <style>
    /* Nền tối toàn trang */
    .stApp { background-color: #131722 !important; color: #d1d4dc !important; }
    [data-testid="stSidebar"] { background-color: #1e222d !important; border-right: 1px solid #2a2e39; }
    
    /* Làm đẹp Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; background-color: #1e222d; padding: 10px 20px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { height: 40px; white-space: pre-wrap; background-color: transparent; border-radius: 4px; color: #787b86; font-weight: bold; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; background-color: #2a2e39 !important; }
    
    /* Nút bấm và Selectbox */
    .stSelectbox div[data-baseweb="select"] { background-color: #2a2e39; border: 1px solid #363a45; border-radius: 8px; }
    .stSelectbox div[data-baseweb="select"] * { color: #ffffff !important; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #2962ff; color: white; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #1e53e5; }
    
    /* Thẻ Metric */
    div[data-testid="stMetricValue"] { color: #ffffff; font-size: 24px; font-weight: bold; }
    div[data-testid="stMetricDelta"] { font-size: 16px; }
    div[data-testid="metric-container"] { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2a2e39; }
    
    /* Ẩn footer mặc định */
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 2. TỪ ĐIỂN TÀI SẢN (CÓ GỢI Ý)
# ============================================================
POPULAR_ASSETS = {
    "🔥 Hàng Hóa (Commodities)": {
        "Vàng (XAUUSD)": "GC=F",
        "Bạc (XAGUSD)": "SI=F",
        "Dầu Thô WTI (USOIL)": "CL=F",
        "Khí Tự Nhiên": "NG=F",
    },
    "₿ Tiền Điện Tử (Crypto)": {
        "Bitcoin (BTC)": "BTC-USD",
        "Ethereum (ETH)": "ETH-USD",
        "Solana (SOL)": "SOL-USD",
        "Binance Coin (BNB)": "BNB-USD",
        "Ripple (XRP)": "XRP-USD",
    },
    "💵 Ngoại Hối (Forex)": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X",
    },
    "🏦 Chỉ Số & Chứng Khoán Mỹ": {
        "S&P 500 (SPX)": "^GSPC",
        "Nasdaq 100": "^IXIC",
        "Dow Jones (DJI)": "^DJI",
        "Apple (AAPL)": "AAPL",
        "Tesla (TSLA)": "TSLA",
        "Nvidia (NVDA)": "NVDA",
    }
}

# Làm phẳng danh sách để đưa vào Selectbox
flat_assets = {}
for category, assets in POPULAR_ASSETS.items():
    for name, ticker in assets.items():
        flat_assets[f"{category} - {name}"] = ticker

# ============================================================
# 3. HÀM XỬ LÝ DỮ LIỆU
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
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

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close, high, low = df["Close"], df["High"], df["Low"]
    
    df["EMA20"] = EMAIndicator(close=close, window=20).ema_indicator()
    df["EMA50"] = EMAIndicator(close=close, window=50).ema_indicator()
    df["RSI"] = RSIIndicator(close=close, window=14).rsi()
    
    macd = MACD(close=close)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()
    
    bb = BollingerBands(close=close, window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
    
    df["ATR"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    
    adx = ADXIndicator(high=high, low=low, close=close, window=14)
    df["ADX"] = adx.adx()
    
    return df

def get_confluence(df):
    last = df.iloc[-1]
    trend = (1 if last["EMA20"] > last["EMA50"] else -1) + (1 if last["Close"] > last["SMA200"] else -1) if "SMA200" in df else 0
    momentum = (1 if last["RSI"] > 55 else -1 if last["RSI"] < 45 else 0) + (1 if last["MACD_hist"] > 0 else -1)
    total = trend + momentum
    
    if total >= 3: return "MUA MẠNH", "#26a69a"
    if total > 0: return "MUA", "#81c784"
    if total <= -3: return "BÁN MẠNH", "#ef5350"
    if total < 0: return "BÁN", "#e57373"
    return "TRUNG LẬP", "#787b86"

# ============================================================
# 4. HEADER & TÙY CHỌN (ĐƯA RA NGOÀI MÀN HÌNH CHÍNH)
# ============================================================
st.markdown("<h1 style='text-align: center; color: #ffffff; margin-bottom: 0;'>TradeDesk Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #787b86;'>Hệ thống phân tích đa khung thời gian & Điểm đồng quy</p>", unsafe_allow_html=True)

# Thanh công cụ phía trên (Thay thế Sidebar)
with st.container():
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        selected_asset = st.selectbox("🔍 Tìm kiếm & Chọn tài sản:", list(flat_assets.keys()), index=0)
        ticker = flat_assets[selected_asset]
    with col2:
        timeframe = st.selectbox("⏱️ Khung thời gian:", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4)
        interval_map = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}
        interval = interval_map[timeframe]
    with col3:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Tải lại dữ liệu"):
            st.cache_data.clear()
    with col4:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.info("Dữ liệu: YF")

# ============================================================
# 5. XỬ LÝ & HIỂN THỊ
# ============================================================
df = load_data(ticker, interval)

if df is None or len(df) < 20:
    st.error(f"❌ Không lấy được dữ liệu cho **{selected_asset}**. Hãy thử khung thời gian khác hoặc mã khác.")
    st.stop()

df = compute_indicators(df)
signal_text, signal_color = get_confluence(df)
last_close = df["Close"].iloc[-1]
prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_close
change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

# Hiển thị KPI
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(label=f"Giá {selected_asset.split(' - ')[1]}", value=f"{last_close:,.2f}", delta=f"{change_pct:+.2f}%")
kpi2.metric(label="RSI (14)", value=f"{df['RSI'].iloc[-1]:.1f}", delta="Quá mua" if df['RSI'].iloc[-1]>70 else ("Quá bán" if df['RSI'].iloc[-1]<30 else "Trung tính"), delta_color="inverse")
kpi3.metric(label="ADX (14)", value=f"{df['ADX'].iloc[-1]:.1f}", delta="Xu hướng mạnh" if df['ADX'].iloc[-1]>25 else "Đi ngang", delta_color="off")
kpi4.metric(label="Tín hiệu tổng hợp", value=signal_text, delta="Điểm: " + str(sum([1 if df['EMA20'].iloc[-1]>df['EMA50'].iloc[-1] else -1])), delta_color="normal")

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# 6. BIỂU ĐỒ (FIX LỖI ZOOM & KHOẢNG TRẮNG)
# ============================================================
# Tạo 3 hàng, thu hẹp khoảng trắng (vertical_spacing = 0.02)
fig = make_subplots(
    rows=3, cols=1, shared_xaxes=True,
    vertical_spacing=0.03, 
    row_heights=[0.65, 0.15, 0.20], # Giá chiếm 65%, RSI 15%, MACD 20%
)

# --- HÀNG 1: GIÁ (NẾN) ---
fig.add_trace(go.Candlestick(
    x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
    name="Giá", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350"
), row=1, col=1)

fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA 20", line=dict(color="#2196f3", width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA 50", line=dict(color="#9c27b0", width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Time"], y=df["BB_upper"], name="BB Upper", line=dict(color="rgba(255,165,0,0.3)", width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Time"], y=df["BB_lower"], name="BB Lower", line=dict(color="rgba(255,165,0,0.3)", width=1), fill="tonexty", fillcolor="rgba(255,165,0,0.05)"), row=1, col=1)

# --- HÀNG 2: RSI ---
fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#e91e63", width=1.5)), row=2, col=1)
fig.add_hline(y=70, line_dash="dot", line_color="#ef5350", row=2, col=1)
fig.add_hline(y=30, line_dash="dot", line_color="#26a69a", row=2, col=1)

# --- HÀNG 3: MACD ---
fig.add_trace(go.Scatter(x=df["Time"], y=df["MACD"], name="MACD", line=dict(color="#ff9800", width=1.5)), row=3, col=1)
fig.add_trace(go.Scatter(x=df["Time"], y=df["MACD_signal"], name="Signal", line=dict(color="#f44336", width=1.5)), row=3, col=1)
macd_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"]]
fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="Histogram", marker_color=macd_colors), row=3, col=1)

# --- TÙY CHỈNH LAYOUT CHO ĐẸP VÀ DỄ ZOOM ---
fig.update_layout(
    template="plotly_dark",
    height=700,
    paper_bgcolor="#131722",
    plot_bgcolor="#131722",
    hovermode="x unified",
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    margin=dict(l=10, r=50, t=30, b=10), # Thu hẹp lề
    dragmode="pan", # Mặc định là kéo thả (Pan) thay vì zoom khung
)

# Tắt thanh trượt (Range Slider) ở hàng 1 và 2, chỉ giữ ở hàng 3 (hoặc tắt hết để dùng thanh công cụ)
fig.update_xaxes(showgrid=True, gridcolor="#2a2e39", rangeslider_visible=False)
fig.update_yaxes(showgrid=True, gridcolor="#2a2e39", side="right") # Đưa trục Y sang phải giống TradingView

# Nút chọn nhanh thời gian (1D, 1W, 1M) ở góc trên
fig.update_xaxes(
    rangeselector=dict(
        buttons=list([
            dict(count=1, label="1D", step="day", stepmode="backward"),
            dict(count=7, label="1W", step="day", stepmode="backward"),
            dict(count=1, label="1M", step="month", stepmode="backward"),
            dict(step="all", label="TẤT CẢ")
        ]),
        bgcolor="#1e222d", activecolor="#2962ff", font=dict(color="#d1d4dc")
    ),
    row=1, col=1
)

# Render biểu đồ (Bật scrollZoom để lăn chuột là zoom, bật thanh công cụ)
chart_config = {
    'scrollZoom': True, # Lăn chuột để zoom
    'displayModeBar': True, # Hiển thị thanh công cụ (Zoom box, Pan, Reset)
    'displaylogo': False,
    'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d'] # Ẩn các nút thừa
}
st.plotly_chart(fig, use_container_width=True, config=chart_config)

# Hướng dẫn sử dụng
st.caption("💡 **Mẹo:** Lăn chuột để Zoom In/Out. Giữ chuột trái để kéo biểu đồ. Sử dụng thanh công cụ góc phải trên cùng biểu đồ để chọn chế độ.")
