import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Cấu hình giao diện trang web rộng
st.set_page_config(
    page_title="Biểu Đồ Kỹ Thuật Cá Nhân", layout="wide", page_icon="📈"
)

st.title("📈 Web Biểu Đồ & Tự Viết Chỉ Báo (Custom Indicators)")

# --- SIDEBAR: CÀI ĐẶT THÔNG SỐ ---
st.sidebar.header("⚙️ Cài đặt Biểu đồ")
ticker = st.sidebar.selectbox(
    "Chọn Tài sản:", ["GC=F", "BTC-USD", "EURUSD=X", "ETH-USD"], index=0
)
period = st.sidebar.selectbox(
    "Khung thời gian dữ liệu:", ["1mo", "3mo", "6mo", "1y", "2y"], index=2
)
interval = st.sidebar.selectbox("Khung nến (Interval):", ["1h", "1d"], index=1)

st.sidebar.subheader("🔧 Tùy chỉnh Chỉ báo tùy ý")
fast_ema = st.sidebar.slider("Chu kỳ Fast EMA", 5, 50, 9)
slow_ema = st.sidebar.slider("Chu kỳ Slow EMA", 10, 200, 21)


# --- TẢI DỮ LIỆU ---
@st.cache_data
def load_data(symbol, per, intr):
  df = yf.download(symbol, period=per, interval=intr)
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)
  return df


data = load_data(ticker, period, interval)

if data.empty:
  st.error(
      "Không thể tải dữ liệu. Vui lòng kiểm tra lại mã tài sản hoặc kết nối."
  )
else:
  # --- TÍNH TOÁN CHỈ BÁO ---
  data[f"EMA_{fast_ema}"] = data["Close"].ewm(span=fast_ema).mean()
  data[f"EMA_{slow_ema}"] = data["Close"].ewm(span=slow_ema).mean()

  # --- VẼ BIỂU ĐỒ BẰNG PLOTLY ---
  fig = go.Figure()

  # 1. Nến giá
  fig.add_trace(
      go.Candlestick(
          x=data.index,
          open=data["Open"],
          high=data["High"],
          low=data["Low"],
          close=data["Close"],
          name="Nến giá",
      )
  )

  # 2. Fast EMA
  fig.add_trace(
      go.Scatter(
          x=data.index,
          y=data[f"EMA_{fast_ema}"],
          line=dict(color="#00f2fe", width=1.5),
          name=f"EMA {fast_ema}",
      )
  )

  # 3. Slow EMA
  fig.add_trace(
      go.Scatter(
          x=data.index,
          y=data[f"EMA_{slow_ema}"],
          line=dict(color="#ff9900", width=1.5),
          name=f"EMA {slow_ema}",
      )
  )

  fig.update_layout(
      title=f"Biểu đồ kỹ thuật: {ticker}",
      yaxis_title="Giá (USD)",
      xaxis_rangeslider_visible=False,
      template="plotly_dark",
      height=650,
      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
  )

  st.plotly_chart(fig, use_container_width=True)

  with st.expander("📊 Xem dữ liệu nến thô"):
    st.dataframe(data.tail(20))
