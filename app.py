import streamlit as st
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

# CSS làm giao diện giống DeepSeek
st.markdown("""
    <style>
    /* Nền chính */
    .stApp { background-color: #131722 !important; color: #d1d4dc !important; }
    
    /* Sidebar (Menu trái) */
    [data-testid="stSidebar"] { 
        background-color: #202123 !important; 
        border-right: 1px solid #2d2d2d;
    }
    
    /* Làm đẹp Menu Radio trong Sidebar để giống nút bấm */
    div[role="radiogroup"] > label {
        padding: 10px 15px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.2s;
        margin-bottom: 5px;
        width: 100%;
    }
    div[role="radiogroup"] > label:hover {
        background-color: #2a2b32;
    }
    div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #343541 !important;
        border-left: 3px solid #2962ff;
    }
    /* Ẩn vòng tròn radio mặc định */
    div[role="radiogroup"] > label > div:first-child {
        display: none;
    }
    
    /* Input / Selectbox */
    .stSelectbox div[data-baseweb="select"] { background-color: #2a2e39; border: 1px solid #363a45; border-radius: 8px; }
    .stSelectbox div[data-baseweb="select"] * { color: #ffffff !important; }
    
    /* Nút bấm */
    .stButton>button { width: 100%; border-radius: 8px; background-color: #2962ff; color: white; border: none; font-weight: bold; padding: 10px; }
    .stButton>button:hover { background-color: #1e53e5; }
    
    /* Thẻ Metric */
    div[data-testid="metric-container"] { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2a2e39; }
    div[data-testid="stMetricValue"] { color: #ffffff; font-size: 24px; font-weight: bold; }
    
    /* Thẻ Tin tức */
    .news-card { background-color: #1e222d; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #2962ff; }
    .news-title { color: #ffffff; font-weight: bold; font-size: 16px; }
    .news-meta { color: #787b86; font-size: 12px; }
    
    /* Ẩn footer */
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 2. TỪ ĐIỂN TÀI SẢN
# ============================================================
POPULAR_ASSETS = {
    "🔥 Hàng Hóa": {"Vàng (XAUUSD)": "GC=F", "Bạc (XAGUSD)": "SI=F", "Dầu WTI": "CL=F"},
    "₿ Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD"},
    "💵 Forex": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"},
    "🏦 Chỉ Số & CK Mỹ": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "Apple (AAPL)": "AAPL", "Tesla (TSLA)": "TSLA"}
}
flat_assets = {f"{cat} - {name}": tick for cat, assets in POPULAR_ASSETS.items() for name, tick in assets.items()}

# ============================================================
# 3. HÀM XỬ LÝ DỮ LIỆU & TIN TỨC
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
# 4. SIDEBAR (GIAO DIỆN ĐIỀU HƯỚNG CHÍNH)
# ============================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white; margin-bottom: 0;'>TradeDesk Pro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #787b86; font-size: 12px;'>Terminal for Professionals</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # 1. Chọn tài sản
    st.markdown("**Tài sản giao dịch**")
    selected_asset = st.selectbox("Chọn mã:", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]
    
    # 2. Chọn khung thời gian
    st.markdown("**Khung thời gian**")
    timeframe = st.selectbox("Chọn nến:", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval_map = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}
    interval = interval_map[timeframe]
    
    # 3. Nút Reload
    if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    
    # 4. MENU ĐIỀU HƯỚNG TÍNH NĂNG
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
# 5. XỬ LÝ DỮ LIỆU CHÍNH
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
# 6. MAIN AREA (KHU VỰC HIỂN THỊ CHÍNH)
# ============================================================
# Header KPI (Luôn hiển thị trên cùng)
st.markdown(f"### {selected_asset} ({timeframe})")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(label="Giá hiện tại", value=f"{last_close:,.2f}", delta=f"{change_pct:+.2f}%")
kpi2.metric(label="RSI (14)", value=f"{df['RSI'].iloc[-1]:.1f}", delta="Quá mua" if df['RSI'].iloc[-1]>70 else ("Quá bán" if df['RSI'].iloc[-1]<30 else "Trung tính"), delta_color="inverse")
kpi3.metric(label="ADX (14)", value=f"{df['ADX'].iloc[-1]:.1f}", delta="Xu hướng mạnh" if df['ADX'].iloc[-1]>25 else "Đi ngang", delta_color="off")
kpi4.metric(label="ATR (14)", value=f"{df['ATR'].iloc[-1]:.2f}", delta="Biến động", delta_color="off")

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
        col_entry.metric("Giá Entry (Market)", f"{trade_plan['entry']:,.2f}")
        col_sl.metric("Stop-Loss (SL)", f"{trade_plan['sl']:,.2f}")
        col_tp.metric("Take-Profit (TP)", f"{trade_plan['tp']:,.2f}")
        
        st.info(f"**Chi tiết:** Swing High 20 nến: {trade_plan['recent_high']:,.2f} | Swing Low 20 nến: {trade_plan['recent_low']:,.2f} | ATR(14): {trade_plan['atr']:,.2f}")
        st.warning("⚠️ Kế hoạch tham khảo dựa trên phân tích kỹ thuật. Hãy quản lý vốn chặt chẽ.")

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
