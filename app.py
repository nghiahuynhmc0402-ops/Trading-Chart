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
# CẤU HÌNH TRANG
# ============================================================
st.set_page_config(
    page_title="TradeDesk Pro | Phân tích kỹ thuật chuyên nghiệp",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# HÀM TẢI DỮ LIỆU (CACHE)
# ============================================================
@st.cache_data(ttl=300, show_spinner="Đang tải dữ liệu thị trường...")
def load_data(symbol: str, period: str, interval: str) -> pd.DataFrame | None:
    """Tải dữ liệu OHLCV từ Yahoo Finance, chuẩn hóa cột."""
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty:
            return None
        # Xử lý MultiIndex columns (yfinance đôi khi trả về)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        # Chuẩn hóa tên cột
        rename_map = {
            "Date": "Date", "Datetime": "Date",
            "Open": "Open", "High": "High", "Low": "Low",
            "Close": "Close", "Volume": "Volume",
        }
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)
        if "Date" not in df.columns:
            df.rename(columns={df.columns[0]: "Date"}, inplace=True)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    except Exception:
        return None


# ============================================================
# TÍNH TOÁN CHỈ BÁO & TÍN HIỆU
# ============================================================
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tính toàn bộ chỉ báo cần thiết và trả về DataFrame đã bổ sung."""
    df = df.copy()
    close, high, low = df["Close"], df["High"], df["Low"]

    # --- Xu hướng ---
    df["EMA20"] = EMAIndicator(close=close, window=20).ema_indicator()
    df["EMA50"] = EMAIndicator(close=close, window=50).ema_indicator()
    df["SMA200"] = SMAIndicator(close=close, window=200).sma_indicator()

    # --- Động lượng ---
    df["RSI"] = RSIIndicator(close=close, window=14).rsi()

    macd = MACD(close=close)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()

    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    # --- Biến động & sức mạnh xu hướng ---
    bb = BollingerBands(close=close, window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_middle"] = bb.bollinger_mavg()
    df["BB_lower"] = bb.bollinger_lband()
    df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / df["BB_middle"]

    atr = AverageTrueRange(high=high, low=low, close=close, window=14)
    df["ATR"] = atr.average_true_range()

    adx = ADXIndicator(high=high, low=low, close=close, window=14)
    df["ADX"] = adx.adx()
    df["DI_plus"] = adx.adx_pos()
    df["DI_minus"] = adx.adx_neg()

    return df


def classify_market_regime(df: pd.DataFrame) -> str:
    """Phân loại chế độ thị trường dựa trên ADX và vị trí giá so với SMA200."""
    if df["ADX"].iloc[-1] >= 25:
        if df["Close"].iloc[-1] > df["SMA200"].iloc[-1]:
            return "Uptrend mạnh (ADX ≥ 25, giá trên SMA200)"
        else:
            return "Downtrend mạnh (ADX ≥ 25, giá dưới SMA200)"
    elif df["ADX"].iloc[-1] < 20:
        return "Sideway / không xu hướng rõ (ADX < 20)"
    else:
        return "Xu hướng yếu / đang chuyển tiếp (ADX 20–25)"


def confluence_score(df: pd.DataFrame) -> dict:
    """
    Tính điểm đồng quy từ 4 lớp: xu hướng, động lượng, biến động, sức mạnh.
    Điểm dương = nghiêng bullish, điểm âm = nghiêng bearish.
    Trả về dict gồm điểm từng lớp, tổng điểm, và nhãn tín hiệu.
    """
    last = df.iloc[-1]
    scores = {}

    # --- Lớp 1: Xu hướng (EMA20 vs EMA50, giá vs SMA200) ---
    trend = 0
    trend += 1 if last["EMA20"] > last["EMA50"] else -1
    trend += 1 if last["Close"] > last["SMA200"] else -1
    scores["Xu hướng"] = trend  # -2 .. +2

    # --- Lớp 2: Động lượng (RSI, MACD histogram, Stochastic) ---
    momentum = 0
    if last["RSI"] > 55:
        momentum += 1
    elif last["RSI"] < 45:
        momentum -= 1

    if last["MACD_hist"] > 0 and last["MACD"] > last["MACD_signal"]:
        momentum += 1
    elif last["MACD_hist"] < 0 and last["MACD"] < last["MACD_signal"]:
        momentum -= 1

    if last["Stoch_K"] > 50 and last["Stoch_K"] > last["Stoch_D"]:
        momentum += 1
    elif last["Stoch_K"] < 50 and last["Stoch_K"] < last["Stoch_D"]:
        momentum -= 1
    scores["Động lượng"] = momentum  # -3 .. +3

    # --- Lớp 3: Biến động (vị trí trong Bollinger Bands) ---
    volatility = 0
    if last["Close"] > last["BB_upper"]:
        volatility = 1   # breakout lên
    elif last["Close"] < last["BB_lower"]:
        volatility = -1  # breakdown xuống
    scores["Biến động"] = volatility  # -1 .. +1

    # --- Lớp 4: Sức mạnh xu hướng (DI+ vs DI-) ---
    strength = 0
    if last["DI_plus"] > last["DI_minus"]:
        strength = 1
    elif last["DI_minus"] > last["DI_plus"]:
        strength = -1
    scores["Sức mạnh"] = strength  # -1 .. +1

    total = sum(scores.values())  # khoảng -7 .. +7

    if total >= 4:
        label = "MUA MẠNH (Bullish confluence cao)"
    elif total >= 2:
        label = "NGHIÊNG MUA (Bullish nhẹ)"
    elif total <= -4:
        label = "BÁN MẠNH (Bearish confluence cao)"
    elif total <= -2:
        label = "NGHIÊNG BÁN (Bearish nhẹ)"
    else:
        label = "TRUNG LẬP / CHỜ TÍN HIỆU"

    return {"scores": scores, "total": total, "label": label}


def atr_risk_levels(df: pd.DataFrame, risk_multiplier: float = 1.5) -> dict:
    """Đề xuất stop-loss và take-profit dựa trên ATR và hướng tín hiệu."""
    last = df.iloc[-1]
    price = last["Close"]
    atr = last["ATR"]
    score = confluence_score(df)["total"]

    if score > 0:  # hướng mua
        stop_loss = price - risk_multiplier * atr
        take_profit = price + 2 * risk_multiplier * atr
        direction = "LONG"
    elif score < 0:  # hướng bán
        stop_loss = price + risk_multiplier * atr
        take_profit = price - 2 * risk_multiplier * atr
        direction = "SHORT"
    else:
        return {"direction": "NEUTRAL", "stop_loss": None, "take_profit": None}

    rr = abs(take_profit - price) / abs(price - stop_loss) if stop_loss != price else None
    return {
        "direction": direction,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_reward": rr,
    }


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("📈 TradeDesk Pro")
    st.caption("Phân tích kỹ thuật đa lớp & quản lý rủi ro")

    ticker = st.text_input("Mã cổ phiếu / Crypto", value="AAPL").upper().strip()
    period = st.selectbox(
        "Khung thời gian",
        ["3mo", "6mo", "1y", "2y", "5y"],
        index=2,
        format_func=lambda x: {"3mo": "3 tháng", "6mo": "6 tháng", "1y": "1 năm", "2y": "2 năm", "5y": "5 năm"}[x],
    )
    interval = st.selectbox(
        "Nến",
        ["1d", "1wk"],
        index=0,
        format_func=lambda x: {"1d": "Ngày", "1wk": "Tuần"}[x],
    )

    st.divider()
    st.subheader("Tham số quản lý rủi ro")
    risk_mult = st.slider("Hệ số ATR cho Stop-loss", 0.5, 3.0, 1.5, 0.1)

    st.divider()
    st.caption("Dữ liệu từ Yahoo Finance. Chỉ mang tính tham khảo, không phải lời khuyên đầu tư.")

# ============================================================
# TẢI & XỬ LÝ DỮ LIỆU
# ============================================================
if not ticker:
    st.info("Nhập mã cổ phiếu ở sidebar để bắt đầu.")
    st.stop()

raw = load_data(ticker, period, interval)

if raw is None or len(raw) < 50:
    st.error(f"Không lấy được dữ liệu cho **{ticker}** hoặc dữ liệu quá ngắn. Thử mã khác hoặc khung thời gian dài hơn.")
    st.stop()

df = compute_indicators(raw)
regime = classify_market_regime(df)
signal = confluence_score(df)
risk = atr_risk_levels(df, risk_mult)

# ============================================================
# PHẦN ĐẦU: TIÊU ĐỀ & KPI
# ============================================================
st.title(f"{ticker} — Bảng điều khiển phân tích")
st.caption(f"Dữ liệu: {df['Date'].iloc[0].date()} → {df['Date'].iloc[-1].date()}  |  Nến: {interval}  |  Chế độ: {regime}")

kpi_cols = st.columns(5)
last_close = df["Close"].iloc[-1]
prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_close
change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

kpi_cols[0].metric("Giá đóng cửa", f"{last_close:,.2f}", f"{change_pct:+.2f}%")
kpi_cols[1].metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}")
kpi_cols[2].metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}")
kpi_cols[3].metric("ATR (14)", f"{df['ATR'].iloc[-1]:,.2f}")
kpi_cols[4].metric("Điểm đồng quy", f"{signal['total']:+d}", signal["label"].split("(")[0].strip())

# ============================================================
# TABS CHÍNH
# ============================================================
tab_chart, tab_signal, tab_risk, tab_data = st.tabs(
    ["📊 Biểu đồ & Chỉ báo", "🎯 Tín hiệu & Đồng quy", "🛡️ Quản lý rủi ro", "📋 Dữ liệu thô"]
)

# ------------------------------------------------------------
# TAB 1: BIỂU ĐỒ
# ------------------------------------------------------------
with tab_chart:
    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.40, 0.15, 0.15, 0.15, 0.15],
        subplot_titles=("Giá & Bollinger Bands", "RSI (14)", "MACD", "Stochastic (14,3)", "ADX / DI"),
    )

    # --- Hàng 1: Nến + Bollinger + EMA ---
    fig.add_trace(
        go.Candlestick(
            x=df["Date"], open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"],
            name="Giá", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        ),
        row=1, col=1,
    )
    fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_upper"], name="BB Upper", line=dict(color="rgba(255,165,0,0.6)", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_lower"], name="BB Lower", line=dict(color="rgba(255,165,0,0.6)", width=1), fill="tonexty", fillcolor="rgba(255,165,0,0.05)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA20"], name="EMA20", line=dict(color="#2196f3", width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA50"], name="EMA50", line=dict(color="#9c27b0", width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA200"], name="SMA200", line=dict(color="#607d8b", width=1.2, dash="dot")), row=1, col=1)

    # --- Hàng 2: RSI ---
    fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI", line=dict(color="#e91e63", width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # --- Hàng 3: MACD ---
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD", line=dict(color="#ff9800", width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD_signal"], name="Signal", line=dict(color="#f44336", width=1.2)), row=3, col=1)
    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"]]
    fig.add_trace(go.Bar(x=df["Date"], y=df["MACD_hist"], name="Histogram", marker_color=colors, opacity=0.6), row=3, col=1)

    # --- Hàng 4: Stochastic ---
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Stoch_K"], name="%K", line=dict(color="#00bcd4", width=1.2)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Stoch_D"], name="%D", line=dict(color="#ff5722", width=1.2)), row=4, col=1)
    fig.add_hline(y=80, line_dash="dash", line_color="red", row=4, col=1)
    fig.add_hline(y=20, line_dash="dash", line_color="green", row=4, col=1)

    # --- Hàng 5: ADX & DI ---
    fig.add_trace(go.Scatter(x=df["Date"], y=df["ADX"], name="ADX", line=dict(color="#9c27b0", width=1.5)), row=5, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["DI_plus"], name="DI+", line=dict(color="#4caf50", width=1, dash="dot")), row=5, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["DI_minus"], name="DI-", line=dict(color="#f44336", width=1, dash="dot")), row=5, col=1)
    fig.add_hline(y=25, line_dash="dash", line_color="gray", row=5, col=1)

    fig.update_layout(
        height=1100,
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=20),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# TAB 2: TÍN HIỆU & ĐỒNG QUY
# ------------------------------------------------------------
with tab_signal:
    st.subheader("Điểm đồng quy đa lớp (Confluence Score)")
    st.caption(
        "Điểm được tổng hợp từ 4 lớp: Xu hướng, Động lượng, Biến động và Sức mạnh xu hướng. "
        "Điểm càng cao (dương) càng nghiêng về bullish; càng thấp (âm) càng bearish."
    )

    score_cols = st.columns(4)
    for i, (layer, sc) in enumerate(signal["scores"].items()):
        delta_text = "Bullish" if sc > 0 else ("Bearish" if sc < 0 else "Neutral")
        score_cols[i].metric(layer, f"{sc:+d}", delta_text)

    st.divider()

    total = signal["total"]
    if total >= 4:
        st.success(f"**{signal['label']}** — Tổng điểm: **{total:+d} / ±7**")
    elif total <= -4:
        st.error(f"**{signal['label']}** — Tổng điểm: **{total:+d} / ±7**")
    elif abs(total) >= 2:
        st.warning(f"**{signal['label']}** — Tổng điểm: **{total:+d} / ±7**")
    else:
        st.info(f"**{signal['label']}** — Tổng điểm: **{total:+d} / ±7**")

    # Giải thích chi tiết từng lớp
    with st.expander("🔍 Giải thích chi tiết từng lớp tín hiệu"):
        detail = pd.DataFrame(
            {
                "Lớp": list(signal["scores"].keys()),
                "Điểm": [f"{v:+d}" for v in signal["scores"].values()],
                "Ý nghĩa": [
                    "EMA20 vs EMA50 và vị trí giá so với SMA200.",
                    "RSI, MACD histogram, Stochastic %K vs %D.",
                    "Vị trí giá so với dải Bollinger (breakout/breakdown).",
                    "DI+ so với DI- (áp lực mua/bán trong xu hướng).",
                ],
            }
        )
        st.dataframe(detail, hide_index=True, use_container_width=True)

# ------------------------------------------------------------
# TAB 3: QUẢN LÝ RỦI RO
# ------------------------------------------------------------
with tab_risk:
    st.subheader("Đề xuất quản lý rủi ro dựa trên ATR")
    st.caption(
        f"Stop-loss và take-profit được tính từ ATR(14) hiện tại với hệ số rủi ro **{risk_mult:.1f}×**. "
        "Đây là khung tham khảo, cần điều chỉnh theo chiến lược cá nhân."
    )

    if risk["direction"] == "NEUTRAL":
        st.info("Tín hiệu đồng quy đang trung lập — chưa có đề xuất stop-loss/take-profit.")
    else:
        risk_cols = st.columns(4)
        risk_cols[0].metric("Hướng", risk["direction"])
        risk_cols[1].metric("Giá hiện tại", f"{last_close:,.2f}")
        risk_cols[2].metric("Stop-loss", f"{risk['stop_loss']:,.2f}")
        risk_cols[3].metric("Take-profit", f"{risk['take_profit']:,.2f}")

        if risk["risk_reward"]:
            st.metric("Tỷ lệ Risk / Reward ước tính", f"1 : {risk['risk_reward']:.2f}")

        st.info(
            "**Công thức:**  \n"
            f"- Stop-loss = Giá ± {risk_mult:.1f} × ATR  \n"
            f"- Take-profit = Giá ± 2 × {risk_mult:.1f} × ATR  \n"
            "- ATR càng lớn, khoảng dừng càng rộng để tránh bị quét bởi nhiễu."
        )

    st.divider()
    st.subheader("Thống kê biến động gần đây")
    vol_cols = st.columns(3)
    vol_cols[0].metric("ATR trung bình 20 phiên", f"{df['ATR'].tail(20).mean():,.2f}")
    vol_cols[1].metric("BB Width hiện tại", f"{df['BB_width'].iloc[-1]:.4f}")
    vol_cols[2].metric("BB Width trung bình 20 phiên", f"{df['BB_width'].tail(20).mean():.4f}")

# ------------------------------------------------------------
# TAB 4: DỮ LIỆU THÔ
# ------------------------------------------------------------
with tab_data:
    st.subheader("Dữ liệu chỉ báo (20 phiên gần nhất)")
    display_cols = [
        "Date", "Open", "High", "Low", "Close", "Volume",
        "RSI", "MACD", "MACD_signal", "MACD_hist",
        "Stoch_K", "Stoch_D", "ADX", "DI_plus", "DI_minus",
        "ATR", "BB_upper", "BB_middle", "BB_lower", "BB_width",
        "EMA20", "EMA50", "SMA200",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(
        df[display_cols].tail(20).style.format(
            {c: "{:.2f}" for c in display_cols if c not in ["Date", "Volume"]}
        ),
        hide_index=True,
        use_container_width=True,
    )

    csv = df[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Tải CSV đầy đủ chỉ báo",
        data=csv,
        file_name=f"{ticker}_indicators.csv",
        mime="text/csv",
    )
