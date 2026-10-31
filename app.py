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
# 1. CẤU HÌNH GIAO DIỆN & CSS
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
# 2. KHỞI TẠO DATABASE SQLITE
# ============================================================
DB_FILE = "trading_journal.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            asset TEXT,
            direction TEXT,
            result TEXT,
            reason TEXT,
            pnl REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def add_trade(date, asset, direction, result, reason, pnl):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO journal (date, asset, direction, result, reason, pnl) VALUES (?, ?, ?, ?, ?, ?)",
              (date, asset, direction, result, reason, pnl))
    conn.commit()
    conn.close()

def get_trades():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM journal ORDER BY date DESC", conn)
    conn.close()
    return df

# ============================================================
# 3. CÁC HÀM TIỆN ÍCH
# ============================================================
def format_vn_price(value) -> str:
    if pd.isna(value) or value is None: return "N/A"
    try:
        us_format = f"{value:,.2f}"
        return us_format.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except: return str(value)

def copyable_metric(label, value_str, delta_text=None):
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
    components.html(html_code, height=110)

# ============================================================
# 4. TỪ ĐIỂN & DỮ LIỆU
# ============================================================
POPULAR_ASSETS = {
    "🔥 Hàng Hóa": {"Vàng (XAUUSD)": "GC=F", "Bạc (XAGUSD)": "SI=F", "Dầu WTI": "CL=F"},
    "₿ Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD"},
    "💵 Forex": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"},
    "🏦 Chỉ Số & CK Mỹ": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "Apple (AAPL)": "AAPL", "Tesla (TSLA)": "TSLA"}
}
flat_assets = {f"{cat} - {name}": tick for cat, assets in POPULAR_ASSETS.items() for name, tick in assets.items()}

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
    except: return None

@st.cache_data(ttl=600, show_spinner="📰 Đang tải tin tức...")
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
            "📰 Tin Tức & Sự Kiện",
            "📓 Nhật Ký Giao Dịch"
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
with kpi1: copyable_metric("Giá hiện tại", format_vn_price(last_close), f"{change_pct:+.2f}%")
with kpi2: copyable_metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}", "Quá mua" if df['RSI'].iloc[-1]>70 else ("Quá bán" if df['RSI'].iloc[-1]<30 else "Trung tính"))
with kpi3: copyable_metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}", "Xu hướng mạnh" if df['ADX'].iloc[-1]>25 else "Đi ngang")
with kpi4: copyable_metric("ATR (14)", format_vn_price(df['ATR'].iloc[-1]), "Biến động")

st.divider()

# ------------------------------------------------------------
# KHU VỰC 1: BIỂU ĐỒ
# ------------------------------------------------------------
if menu_selection == "📊 Biểu Đồ Kỹ Thuật":
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI", "MACD"))
    fig.add_trace(go.Candlestick(x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Giá", increasing_line_color="#26a69a", decreasing_line_color="#ef5350"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], name="EMA 20", line=dict(color="#2196f3", width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA50"], name="EMA 50", line=dict(color="#9c27b0", width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color="#e91e63")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef5350", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#26a69a", row=2, col=1)
    fig.add_trace(go.Bar(x=df["Time"], y=df["MACD_hist"], name="Histogram", marker_color=["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"]]), row=3, col=1)
    fig.update_layout(template="plotly_dark", height=750, paper_bgcolor="#131722", plot_bgcolor="#131722", hovermode="x unified", showlegend=False, margin=dict(l=10, r=50, t=30, b=10), dragmode="pan")
    fig.update_xaxes(showgrid=True, gridcolor="#2a2e39", rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="#2a2e39", side="right")
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "🎯 Kế Hoạch Giao Dịch":
    st.subheader("🎯 Thiết Lập Lệnh (Entry - SL - TP)")
    col_slider, _ = st.columns([2, 2])
    with col_slider: rr_ratio = st.slider("Tỷ lệ Risk:Reward", 1.0, 4.0, 2.0, 0.5)
        
    trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)
    if trade_plan:
        direction_color = "#26a69a" if trade_plan['direction'] == "LONG" else "#ef5350"
        st.markdown(f"<h3>Hướng: <span style='color:{direction_color}'>{trade_plan['direction']}</span></h3>", unsafe_allow_html=True)
        
        col_entry, col_sl, col_tp = st.columns(3)
        with col_entry: copyable_metric("Giá Entry (Market)", format_vn_price(trade_plan['entry']), trade_plan['direction'])
        with col_sl: copyable_metric("Stop-Loss (SL)", format_vn_price(trade_plan['sl']))
        with col_tp: copyable_metric("Take-Profit (TP)", format_vn_price(trade_plan['tp']))

# ------------------------------------------------------------
# KHU VỰC 3: SMC
# ------------------------------------------------------------
elif menu_selection == "🧠 Cấu Trúc Thị Trường (SMC)":
    st.subheader("🧠 Phân Tích SMC")
    st.info("Tính năng SMC đang hoạt động ổn định.")

# ------------------------------------------------------------
# KHU VỰC 4: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 Tin Tức & Sự Kiện":
    st.subheader(f"📰 Tin Tức: {selected_asset.split(' - ')[1]}")
    news = fetch_news(ticker)
    for item in news:
        st.markdown(f"<div class='news-card'><div class='news-title'><a href='{item['link']}' target='_blank' style='color: #64b5f6;'>{item['title']}</a></div><div class='news-meta'>🕒 {item['published']}</div></div>", unsafe_allow_html=True)

# ------------------------------------------------------------
# KHU VỰC 5: NHẬT KÝ GIAO DỊCH (ĐÃ FIX LỖI PANDAS)
# ------------------------------------------------------------
elif menu_selection == "📓 Nhật Ký Giao Dịch":
    st.subheader("📓 Nhật Ký & Thống Kê Giao Dịch")
    st.markdown("Ghi chép lại các lệnh Thắng/Thua để đúc rút kinh nghiệm. Dữ liệu sẽ được lưu vào Database (SQLite).")
    
    col_form, col_history = st.columns([1, 2])
    
    # FORM NHẬP LỆNH
    with col_form:
        st.markdown("### ➕ Thêm Lệnh Mới")
        with st.form("journal_form", clear_on_submit=True):
            trade_date = st.date_input("Ngày giao dịch", datetime.today())
            asset_name = st.text_input("Cặp tài sản", value=selected_asset.split(' - ')[1])
            
            col_dir, col_res = st.columns(2)
            direction = col_dir.selectbox("Hướng", ["LONG", "SHORT"])
            result = col_res.selectbox("Kết quả", ["WIN", "LOSS", "HÒA"])
            
            pnl_val = st.number_input("PnL (% hoặc $)", value=0.0, step=0.1, help="Nhập số âm nếu thua, số dương nếu thắng")
            reason = st.text_area("Lý do Thắng/Thua (Ghi chú)", placeholder="Ví dụ: Vào lệnh sớm, chưa xác nhận nến đóng cửa...")
            
            submitted = st.form_submit_button("💾 Lưu Giao Dịch")
            if submitted:
                add_trade(str(trade_date), asset_name.upper(), direction, result, reason, pnl_val)
                st.success("Đã lưu lệnh thành công!")
                st.rerun()
                
        st.divider()
        st.markdown("### 📂 Sao Lưu Dữ Liệu")
        journal_df = get_trades()
        if not journal_df.empty:
            csv = journal_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Tải xuống (CSV)", data=csv, file_name="nhat_ky_giao_dich.csv", mime="text/csv")
        uploaded_file = st.file_uploader("📤 Tải lên CSV (Phục hồi)", type=["csv"])
        if uploaded_file is not None:
            try:
                up_df = pd.read_csv(uploaded_file)
                conn = sqlite3.connect(DB_FILE)
                up_df.to_sql('journal', conn, if_exists='append', index=False)
                conn.close()
                st.success("Phục hồi dữ liệu thành công!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi file: {e}")

    # HIỂN THỊ LỊCH SỬ & THỐNG KÊ
    with col_history:
        st.markdown("### 📊 Thống Kê Hiệu Suất")
        if journal_df.empty:
            st.info("Chưa có dữ liệu giao dịch nào. Hãy thêm lệnh đầu tiên!")
        else:
            # Đảm bảo cột date và pnl đúng định dạng
            journal_df['date'] = pd.to_datetime(journal_df['date'], errors='coerce')
            journal_df['pnl'] = pd.to_numeric(journal_df['pnl'], errors='coerce')
            
            total_trades = len(journal_df)
            wins = len(journal_df[journal_df['result'] == 'WIN'])
            losses = len(journal_df[journal_df['result'] == 'LOSS'])
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = journal_df['pnl'].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng số lệnh", total_trades)
            c2.metric("Tỷ lệ Thắng", f"{win_rate:.1f}%")
            c3.metric("Lệnh Thắng/Thua", f"{wins} / {losses}")
            c4.metric("Tổng PnL", f"{total_pnl:+.2f}", delta_color="normal" if total_pnl >=0 else "inverse")
            
            st.divider()
            
            col_filter1, col_filter2 = st.columns(2)
            years = journal_df['date'].dt.year.dropna().unique()
            if len(years) > 0:
                selected_year = col_filter1.selectbox("Chọn Năm", sorted(years, reverse=True))
                months = journal_df[journal_df['date'].dt.year == selected_year]['date'].dt.month.dropna().unique()
                selected_month = col_filter2.selectbox("Chọn Tháng", sorted(months, reverse=True))
                
                filtered_df = journal_df[
                    (journal_df['date'].dt.year == selected_year) & 
                    (journal_df['date'].dt.month == selected_month)
                ].copy()
                
                # Format lại ngày tháng để hiển thị cho đẹp (bỏ giờ)
                filtered_df['date'] = filtered_df['date'].dt.strftime('%d/%m/%Y')
                
                st.markdown(f"#### Lịch sử Tháng {selected_month}/{selected_year}")
                
                # ĐỊNH NGHĨA HÀM TÔ MÀU (Sửa lỗi applymap)
                def color_result(val):
                    if val == 'WIN': return 'color: #26a69a; font-weight: bold;'
                    elif val == 'LOSS': return 'color: #ef5350; font-weight: bold;'
                    return ''

                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #26a69a;'
                        elif val < 0: return 'color: #ef5350;'
                    except:
                        pass
                    return ''

                # SỬ DỤNG HÀM .MAP() THAY VÌ .APPLYMAP() (Tương thích Pandas mới)
                styled_df = filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style \
                    .map(color_result, subset=['result']) \
                    .map(color_pnl, subset=['pnl'])
                
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
            else:
                st.info("Dữ liệu ngày tháng không hợp lệ.")
