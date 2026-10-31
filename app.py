import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
import sqlite3
from datetime import datetime, timedelta

# Thư viện chỉ báo kỹ thuật
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

try:
    import pyvsmc as smc
    HAS_SMC = True
except ImportError:
    HAS_SMC = False

# ============================================================
# 1. CẤU HÌNH GIAO DIỆN & CSS  (AURORA GLASS - NGHIA_TRADING)
# ============================================================
st.set_page_config(
    page_title="Nghia_Trading | Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

:root {
    --bg: #05060a;
    --surface: rgba(255,255,255,0.035);
    --surface-hi: rgba(255,255,255,0.06);
    --line: rgba(255,255,255,0.07);
    --line-hi: rgba(255,255,255,0.16);
    --txt: #eef0f6;
    --muted: #8b90a0;
    --dim: #5b6070;
    --brand: #7c7cff;
    --brand2: #b06cff;
    --up: #22d3a0;
    --down: #ff5470;
    --warn: #fbbf24;
    --ease: cubic-bezier(.22,1,.36,1);
}

* { -webkit-tap-highlight-color: transparent; }
html { scroll-behavior: smooth; }

/* ---------- Nền Aurora động ---------- */
.stApp {
    background: var(--bg);
    color: var(--txt) !important;
    font-family: 'Inter', sans-serif;
}
.stApp::before, .stApp::after {
    content: ""; position: fixed; z-index: 0; pointer-events: none;
    width: 55vw; height: 55vw; border-radius: 50%; filter: blur(90px); opacity: .55;
}
.stApp::before {
    top: -20vw; left: -10vw;
    background: radial-gradient(circle, rgba(124,124,255,.32), transparent 65%);
    animation: drift1 22s ease-in-out infinite alternate;
}
.stApp::after {
    bottom: -25vw; right: -15vw;
    background: radial-gradient(circle, rgba(34,211,160,.20), transparent 65%);
    animation: drift2 26s ease-in-out infinite alternate;
}
@keyframes drift1 { to { transform: translate(18vw, 14vh) scale(1.15); } }
@keyframes drift2 { to { transform: translate(-16vw, -12vh) scale(1.2); } }

[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 2.2rem !important; max-width: 1500px; position: relative; z-index: 1; }

/* ---------- Animation vào trang ---------- */
@keyframes fadeUp { from { opacity: 0; transform: translateY(18px) scale(.985); } to { opacity: 1; transform: none; } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes pulseDot { 0% { box-shadow: 0 0 0 0 rgba(34,211,160,.6); } 70% { box-shadow: 0 0 0 10px rgba(34,211,160,0); } 100% { box-shadow: 0 0 0 0 rgba(34,211,160,0); } }
@keyframes gradShift { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
@keyframes floaty { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
@keyframes ripple { to { transform: scale(4); opacity: 0; } }
@keyframes sweep { from { transform: translateX(-120%); } to { transform: translateX(220%); } }

.block-container [data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"],
.block-container [data-testid="stVerticalBlock"] > div[data-testid="element-container"] {
    animation: fadeUp .65s var(--ease) both;
}
.block-container [data-testid="stVerticalBlock"] > div:nth-child(1) { animation-delay: .00s; }
.block-container [data-testid="stVerticalBlock"] > div:nth-child(2) { animation-delay: .06s; }
.block-container [data-testid="stVerticalBlock"] > div:nth-child(3) { animation-delay: .12s; }
.block-container [data-testid="stVerticalBlock"] > div:nth-child(4) { animation-delay: .18s; }
.block-container [data-testid="stVerticalBlock"] > div:nth-child(5) { animation-delay: .24s; }
.block-container [data-testid="stVerticalBlock"] > div:nth-child(6) { animation-delay: .30s; }
.block-container [data-testid="stVerticalBlock"] > div:nth-child(n+7) { animation-delay: .36s; }
[data-testid="stHorizontalBlock"] > div { animation: fadeUp .6s var(--ease) both; }
[data-testid="stHorizontalBlock"] > div:nth-child(2) { animation-delay: .08s; }
[data-testid="stHorizontalBlock"] > div:nth-child(3) { animation-delay: .16s; }
[data-testid="stHorizontalBlock"] > div:nth-child(4) { animation-delay: .24s; }

.stPlotlyChart {
    touch-action: pan-y pinch-zoom !important;
    border-radius: 18px; overflow: hidden;
    border: 1px solid var(--line);
    background: linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.01));
    box-shadow: 0 20px 50px -20px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.05);
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: rgba(8,9,14,.72) !important;
    backdrop-filter: blur(28px) saturate(140%);
    -webkit-backdrop-filter: blur(28px) saturate(140%);
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] > div:first-child { animation: fadeIn .8s ease both; }

.sidebar-header { padding: 6px 0 20px 0; border-bottom: 1px solid var(--line); margin-bottom: 20px; display: flex; align-items: center; gap: 12px; }
.sidebar-logo {
    width: 42px; height: 42px; border-radius: 13px; display: flex; justify-content: center; align-items: center; color: #fff;
    background: linear-gradient(135deg, var(--brand), var(--brand2), #4ee3c1, var(--brand));
    background-size: 300% 300%; animation: gradShift 6s linear infinite, floaty 4s ease-in-out infinite;
    box-shadow: 0 8px 24px rgba(124,124,255,.45);
}
.sidebar-title { font-size: 18px; font-weight: 800; color: #fff; margin: 0; letter-spacing: -.3px; }
.sidebar-subtitle { font-size: 10.5px; color: var(--muted); text-transform: uppercase; letter-spacing: 1.6px; margin-top: 2px; }
.side-label { color: var(--muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.2px; margin: 4px 0 6px 2px; }

.pro-card {
    position: relative; overflow: hidden; border-radius: 16px; padding: 16px; margin-top: 22px;
    background: linear-gradient(135deg, rgba(124,124,255,.14), rgba(176,108,255,.10));
    border: 1px solid rgba(124,124,255,.25);
}
.pro-card::after {
    content: ""; position: absolute; inset: 0; width: 40%;
    background: linear-gradient(100deg, transparent, rgba(255,255,255,.12), transparent);
    animation: sweep 4.5s ease-in-out infinite;
}
.pro-card h4 { margin: 0 0 5px 0; font-size: 14px; color: #fff; font-weight: 700; }
.pro-card p { margin: 0; font-size: 12px; color: #a8adbd; line-height: 1.5; }
.copyright { text-align: center; color: var(--dim); font-size: 11px; margin-top: 26px; padding-top: 14px; border-top: 1px dashed var(--line); }

/* ---------- Menu điều hướng dạng viên thuốc ---------- */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex; flex-wrap: nowrap; gap: 6px !important; overflow-x: auto; scrollbar-width: none;
    padding: 6px; border-radius: 16px; background: var(--surface); border: 1px solid var(--line);
    backdrop-filter: blur(16px); -webkit-overflow-scrolling: touch;
}
div[data-testid="stRadio"] > div[role="radiogroup"]::-webkit-scrollbar { display: none; }
div[data-testid="stRadio"] > div[role="radiogroup"] > label {
    position: relative; overflow: hidden; flex: 0 0 auto; padding: 10px 18px !important; border-radius: 11px !important;
    cursor: pointer !important; background: transparent !important; border: 1px solid transparent;
    color: var(--muted) !important; transition: all .3s var(--ease); margin: 0 !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { background: var(--surface-hi) !important; color: var(--txt) !important; transform: translateY(-1px); }
div[data-testid="stRadio"] > div[role="radiogroup"] > label:active { transform: scale(.94); }
div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"],
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(135deg, rgba(124,124,255,.28), rgba(176,108,255,.18)) !important;
    border: 1px solid rgba(124,124,255,.4);
    box-shadow: 0 6px 20px -6px rgba(124,124,255,.55), inset 0 1px 0 rgba(255,255,255,.1);
    color: #fff !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none !important; }
div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p { font-size: 13.5px !important; font-weight: 600 !important; white-space: nowrap; }
div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p,
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #fff !important; }

/* ---------- Inputs ---------- */
.stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {
    background-color: var(--surface) !important; border: 1px solid var(--line) !important;
    border-radius: 12px !important; color: var(--txt) !important; font-family: 'Inter', sans-serif !important;
    transition: all .25s var(--ease);
}
.stSelectbox div[data-baseweb="select"] > div:hover, .stTextInput input:hover, .stNumberInput input:hover { border-color: var(--line-hi) !important; transform: translateY(-1px); }
.stSelectbox div[data-baseweb="select"] > div:focus-within, .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
    border-color: var(--brand) !important; box-shadow: 0 0 0 3px rgba(124,124,255,.22) !important;
}
[data-testid="stSlider"] [role="slider"] { background: var(--brand) !important; box-shadow: 0 0 0 5px rgba(124,124,255,.25); transition: box-shadow .2s; }
[data-testid="stSlider"] [role="slider"]:active { box-shadow: 0 0 0 9px rgba(124,124,255,.25); }

/* ---------- Buttons ---------- */
.stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button {
    position: relative; overflow: hidden; width: 100%; border-radius: 12px !important; border: 1px solid rgba(255,255,255,.12) !important;
    background: linear-gradient(135deg, var(--brand), var(--brand2)) !important; color: #fff !important;
    font-family: 'Inter', sans-serif !important; font-weight: 600; padding: 10px 14px;
    transition: transform .25s var(--ease), box-shadow .25s var(--ease), filter .25s;
    box-shadow: 0 6px 20px -6px rgba(124,124,255,.6);
}
.stButton>button:hover, .stDownloadButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover {
    transform: translateY(-2px); box-shadow: 0 12px 28px -8px rgba(124,124,255,.75); filter: brightness(1.08);
}
.stButton>button:active, .stDownloadButton>button:active, [data-testid="stFormSubmitButton"]>button:active { transform: scale(.95); }
.ripple-dot { position: absolute; border-radius: 50%; background: rgba(255,255,255,.5); transform: scale(0); animation: ripple .65s ease-out; pointer-events: none; }

/* ---------- Dataframe / Metric Streamlit ---------- */
[data-testid="stDataFrame"] { border-radius: 16px !important; border: 1px solid var(--line) !important; overflow: hidden; background: var(--surface) !important; }
[data-testid="stMetric"] {
    background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 14px 18px;
    transition: transform .3s var(--ease), border-color .3s, box-shadow .3s;
}
[data-testid="stMetric"]:hover { transform: translateY(-3px); border-color: var(--line-hi); box-shadow: 0 14px 30px -12px rgba(0,0,0,.6); }
[data-testid="stMetricLabel"] p { color: var(--muted) !important; font-size: 12px !important; text-transform: uppercase; letter-spacing: .6px; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-weight: 700 !important; }
[data-testid="stAlert"] { border-radius: 14px !important; border: 1px solid var(--line) !important; backdrop-filter: blur(10px); }
[data-testid="stForm"] { border: none !important; padding: 0 !important; }

/* ---------- Titles ---------- */
h1, h2, h3 { color: #fff !important; font-family: 'Inter', sans-serif !important; font-weight: 800 !important; letter-spacing: -.5px; }
h3 { position: relative; padding-left: 14px; }
.stMarkdown h3::before, [data-testid="stSubheader"]::before { content: none; }
[data-testid="stCaptionContainer"] { color: var(--dim) !important; }

/* ---------- Cards ---------- */
.glass-card {
    position: relative; overflow: hidden; background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.015));
    border: 1px solid var(--line); border-radius: 18px; padding: 20px; margin-bottom: 14px;
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    box-shadow: 0 12px 30px -16px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.06);
    transition: transform .4s var(--ease), box-shadow .4s var(--ease), border-color .3s;
    --mx: 50%; --my: 0%;
}
.glass-card::before {
    content: ""; position: absolute; inset: 0; pointer-events: none; opacity: 0; transition: opacity .35s;
    background: radial-gradient(380px circle at var(--mx) var(--my), rgba(124,124,255,.16), transparent 60%);
}
.glass-card:hover { transform: translateY(-4px); border-color: var(--line-hi); box-shadow: 0 24px 48px -18px rgba(0,0,0,.8), 0 0 0 1px rgba(124,124,255,.12); }
.glass-card:hover::before { opacity: 1; }
.glass-card:active { transform: translateY(-1px) scale(.992); }
.card-title { color: #fff; font-weight: 700; font-size: 15px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--line); padding-bottom: 12px; }
.row-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px; color: var(--muted); }
.val-data { color: var(--txt); font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.val-up { color: var(--up) !important; }
.val-down { color: var(--down) !important; }

.signal-card {
    position: relative; overflow: hidden; border-radius: 18px; padding: 22px; margin-bottom: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.015)); border: 1px solid var(--line);
    transition: transform .4s var(--ease), box-shadow .4s var(--ease);
}
.signal-card::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--accent, var(--brand)); box-shadow: 0 0 20px var(--accent, var(--brand)); }
.signal-card:hover { transform: translateY(-3px); box-shadow: 0 20px 40px -18px rgba(0,0,0,.8); }
.score-badge { background: linear-gradient(135deg, rgba(124,124,255,.25), rgba(176,108,255,.2)); border: 1px solid rgba(124,124,255,.35); color: #d6c6ff; padding: 6px 14px; border-radius: 99px; font-weight: 700; font-size: 13px; }
.score-bar { height: 6px; border-radius: 99px; background: rgba(255,255,255,.06); overflow: hidden; margin: 4px 0 16px 0; }
.score-bar > div { height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--brand), var(--up)); animation: grow 1.2s var(--ease) both; }
@keyframes grow { from { width: 0 !important; } }
.reason-line { padding: 7px 0; font-size: 13px; color: #b4b9c8; line-height: 1.55; animation: fadeUp .5s var(--ease) both; }

.bot-active { border-radius: 16px; padding: 16px 18px; margin-bottom: 18px; background: rgba(124,124,255,.10); border: 1px solid rgba(124,124,255,.35); animation: glowPulse 2.8s ease-in-out infinite; }
@keyframes glowPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(124,124,255,0); } 50% { box-shadow: 0 0 26px 0 rgba(124,124,255,.28); } }

.news-card { cursor: pointer; padding: 16px 18px; margin-bottom: 12px; }
.news-card:hover .news-title { color: #fff; transform: translateX(4px); }
.news-title { color: #a9a9ff; font-weight: 600; font-size: 15px; margin-bottom: 8px; transition: all .3s var(--ease); line-height: 1.45; }

.mtf-card { text-align: center; }
.mtf-icon { font-size: 42px; margin: 6px 0 10px 0; display: inline-block; animation: floaty 3.5s ease-in-out infinite; }

.page-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; animation: fadeUp .6s var(--ease) both; }
.page-header h1 { margin: 0; font-size: 28px; background: linear-gradient(90deg, #fff, #b9b9ff 60%, #fff); background-size: 200% auto; -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; animation: gradShift 8s linear infinite; }
.page-header p { margin: 2px 0 0 0; color: var(--muted); font-size: 13px; font-weight: 500; }
.live-pill { background: rgba(34,211,160,.10); border: 1px solid rgba(34,211,160,.28); padding: 6px 13px; border-radius: 99px; display: flex; align-items: center; gap: 8px; }
.live-pill i { width: 7px; height: 7px; background: var(--up); border-radius: 50%; animation: pulseDot 1.8s infinite; }
.live-pill span { color: var(--up); font-size: 12px; font-weight: 700; letter-spacing: .5px; }

.math-box { background: var(--surface); border: 1px dashed var(--line-hi); border-radius: 14px; padding: 15px 17px; margin-top: 14px; font-size: 13px; color: var(--muted); line-height: 1.6; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.12); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(124,124,255,.5); }

@media (max-width: 768px) {
    .block-container { padding: 1.2rem .8rem !important; }
    .page-header h1 { font-size: 22px; }
    .glass-card, .signal-card { padding: 16px; }
}
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }


/* ===================== V2: FIX + WOW ===================== */
@property --ang { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
@keyframes spin { to { --ang: 360deg; } }
@keyframes ringfill { from { stroke-dashoffset: 264; } }
@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes gridmove { to { background-position: 0 56px, 56px 0; } }

/* --- Sửa menu: bỏ vòng tròn radio, không vỡ chữ --- */
div[data-testid="stRadio"] { width: 100%; }
div[data-testid="stRadio"] > div[role="radiogroup"] { flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto !important; }
div[data-testid="stRadio"] label {
    width: auto !important; min-width: max-content !important; flex: 0 0 auto !important;
    display: flex !important; align-items: center !important; margin: 0 !important;
}
div[data-testid="stRadio"] label > input,
div[data-testid="stRadio"] label > div:not(:has([data-testid="stMarkdownContainer"])) { display: none !important; }
div[data-testid="stRadio"] label > div { width: auto !important; min-width: max-content !important; margin: 0 !important; }
div[data-testid="stRadio"] label [data-testid="stMarkdownContainer"] { width: max-content !important; }
div[data-testid="stRadio"] label p {
    white-space: nowrap !important; word-break: keep-all !important; overflow-wrap: normal !important; margin: 0 !important;
}

/* --- Lưới nền chuyển động --- */
[data-testid="stAppViewContainer"]::before {
    content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
    background-size: 56px 56px;
    -webkit-mask-image: radial-gradient(ellipse at 50% 15%, #000 0%, transparent 72%);
    mask-image: radial-gradient(ellipse at 50% 15%, #000 0%, transparent 72%);
    animation: gridmove 7s linear infinite;
}

/* --- Thẻ nghiêng 3D + đèn rọi --- */
.glass-card {
    transform: perspective(900px) rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg)) translateY(var(--ty,0px));
    transition: transform .25s ease-out, box-shadow .4s var(--ease), border-color .3s; will-change: transform;
}
.glass-card:hover { --ty: -4px; transform: perspective(900px) rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg)) translateY(-4px); }
.glass-card:active { transform: perspective(900px) scale(.985); }

/* --- Hero giá --- */
.hero {
    position: relative; border-radius: 24px; padding: 1.5px; margin-bottom: 18px;
    background: conic-gradient(from var(--ang), rgba(255,255,255,.07) 0%, rgba(255,255,255,.07) 55%, var(--c) 78%, #7c7cff 90%, rgba(255,255,255,.07) 100%);
    animation: spin 7s linear infinite, fadeUp .7s var(--ease) both;
    box-shadow: 0 30px 70px -34px var(--c);
}
.hero-in {
    position: relative; overflow: hidden; border-radius: 23px; padding: 22px 24px;
    background: linear-gradient(160deg, rgba(14,15,24,.97), rgba(8,9,14,.98));
}
.hero-in::before {
    content: ""; position: absolute; right: -90px; top: -90px; width: 280px; height: 280px; border-radius: 50%;
    background: radial-gradient(circle, var(--c), transparent 70%); opacity: .17; filter: blur(12px);
}
.hero-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; position: relative; }
.hero-name { font-size: clamp(22px, 4.4vw, 30px); font-weight: 800; letter-spacing: -.6px; color: #fff; }
.hero-sub { color: var(--muted); font-size: 13px; font-weight: 500; margin-top: 2px; }
.hero-mid { display: grid; grid-template-columns: minmax(0,1.1fr) minmax(0,1fr); align-items: end; gap: 18px; margin-top: 16px; position: relative; }
.hero-price {
    font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: clamp(30px, 7vw, 46px);
    line-height: 1.05; color: #fff; letter-spacing: -1px; text-shadow: 0 0 34px var(--c);
}
.chg {
    display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; padding: 5px 12px; border-radius: 99px;
    font-weight: 700; font-size: 13px; font-family: 'JetBrains Mono', monospace;
    color: var(--c); background: var(--cbg); border: 1px solid var(--cbd);
}
.spark { width: 100%; height: auto; overflow: visible; }
.spark .ln {
    fill: none; stroke: var(--c); stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round;
    stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 1.9s var(--ease) .2s forwards; filter: drop-shadow(0 0 6px var(--c));
}
.spark .ar { opacity: 0; animation: fadeIn 1.1s ease 1.1s forwards; }
.hero-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 18px; position: relative; }
.hero-stats > div {
    padding: 10px 12px; border-radius: 12px; background: rgba(255,255,255,.04); border: 1px solid var(--line);
    transition: transform .3s var(--ease), border-color .3s, background .3s;
}
.hero-stats > div:hover { transform: translateY(-3px); border-color: var(--line-hi); background: rgba(255,255,255,.07); }
.hero-stats > div:active { transform: scale(.96); }
.hero-stats span { display: block; font-size: 10.5px; color: var(--muted); text-transform: uppercase; letter-spacing: .8px; margin-bottom: 3px; }
.hero-stats b { font-family: 'JetBrains Mono', monospace; font-size: 13.5px; color: #fff; word-break: break-all; }
@media (max-width: 640px) {
    .hero-mid { grid-template-columns: 1fr; gap: 10px; }
    .hero-in { padding: 18px; }
    .hero-stats b { font-size: 12px; }
}

/* --- Vòng tròn điểm chất lượng --- */
.sig-head { display: flex; align-items: center; gap: 18px; margin-bottom: 14px; flex-wrap: wrap; }
.ring { position: relative; width: 108px; height: 108px; flex: 0 0 auto; }
.ring svg { width: 100%; height: 100%; transform: rotate(-90deg); filter: drop-shadow(0 0 10px rgba(124,124,255,.5)); }
.ring circle { fill: none; stroke-width: 8; }
.ring-bg { stroke: rgba(255,255,255,.07); }
.ring-fg { stroke-linecap: round; stroke-dasharray: 264; stroke-dashoffset: var(--off); animation: ringfill 1.6s var(--ease) .2s both; }
.ring-num {
    position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 28px; color: #fff; line-height: 1;
}
.ring-num small { font-size: 11px; color: var(--muted); margin-top: 3px; font-weight: 500; }
.sig-kicker { font-size: 11px; letter-spacing: 1.6px; color: var(--muted); font-weight: 700; margin-bottom: 4px; }
.sig-info h3 { margin: 0 0 8px 0 !important; padding: 0 !important; font-size: 22px !important; }

footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)

# Hiệu ứng chạm: ripple khi bấm + đèn rọi theo con trỏ/ngón tay trên card
components.html("""
<script>
(function(){
  try {
    const P = window.parent, D = P.document;
    if (P.__ntFx2) return; P.__ntFx2 = true;
    D.addEventListener('pointerdown', function(e){
      const t = e.target.closest('.stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button, div[data-testid="stRadio"] label');
      if (!t) return;
      const r = t.getBoundingClientRect(), s = Math.max(r.width, r.height);
      const d = D.createElement('span'); d.className = 'ripple-dot';
      d.style.width = d.style.height = s + 'px';
      d.style.left = (e.clientX - r.left - s/2) + 'px';
      d.style.top = (e.clientY - r.top - s/2) + 'px';
      t.appendChild(d); setTimeout(() => d.remove(), 700);
    }, {passive:true});
    D.addEventListener('pointermove', function(e){
      const c = e.target.closest('.glass-card'); if (!c) return;
      const r = c.getBoundingClientRect();
      c.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      c.style.setProperty('--my', (e.clientY - r.top) + 'px');
      if (e.pointerType === 'mouse') {
        c.style.setProperty('--rx', (-((e.clientY - r.top) / r.height - .5) * 7).toFixed(2) + 'deg');
        c.style.setProperty('--ry', (((e.clientX - r.left) / r.width - .5) * 7).toFixed(2) + 'deg');
      }
    }, {passive:true});
    D.addEventListener('pointerout', function(e){
      const c = e.target.closest && e.target.closest('.glass-card');
      if (c && !(e.relatedTarget && c.contains(e.relatedTarget))) { c.style.setProperty('--rx','0deg'); c.style.setProperty('--ry','0deg'); }
    }, {passive:true});
    const fmt = (v, d) => v.toLocaleString('de-DE', {minimumFractionDigits: d, maximumFractionDigits: d});
    const run = () => {
      D.querySelectorAll('.nt-count:not([data-done])').forEach(function(el){
        el.setAttribute('data-done', '1');
        const to = parseFloat(el.dataset.v), d = parseInt(el.dataset.d || '0');
        if (isNaN(to)) return;
        const t0 = performance.now(), dur = 1200;
        const step = function(now){
          const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 4);
          el.textContent = fmt(to * e, d);
          if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      });
    };
    run();
    new MutationObserver(run).observe(D.body, {childList: true, subtree: true});
  } catch(err) {}
})();
</script>
""", height=0)

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
        df = pd.read_sql_query("SELECT * FROM bot_journal WHERE asset=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1", conn, params=(asset,))
    return df.iloc[0] if not df.empty else None


def get_last_closed_bot_trade(asset):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT * FROM bot_journal WHERE asset=? AND status!='ACTIVE' ORDER BY id DESC LIMIT 1", conn, params=(asset,))
    return df.iloc[0] if not df.empty else None


def add_bot_trade(open_time, asset, direction, entry, sl, tp):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO bot_journal (open_time, asset, direction, entry_price, sl, tp, status) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')", (open_time, asset, direction, entry, sl, tp))


def close_bot_trade(trade_id, close_time, exit_price, status, reason):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE bot_journal SET close_time=?, exit_price=?, status=?, reason=? WHERE id=?", (close_time, exit_price, status, reason, int(trade_id)))


def get_bot_history(asset):
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query("SELECT * FROM bot_journal WHERE asset=? ORDER BY id DESC", conn, params=(asset,))


# ============================================================
# 3. UI COMPONENTS & LOGIC
# ============================================================
def html(s: str):
    """Gộp HTML thành 1 dòng để Markdown không biến nó thành code block."""
    st.markdown("".join(line.strip() for line in s.splitlines()), unsafe_allow_html=True)


def format_vn_price(value) -> str:
    if value is None or pd.isna(value): return "N/A"
    try: return f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except Exception: return str(value)


def quantum_metric(label, value_str, delta_text=None, is_positive=None, raw=None, dec=2, vn=True):
    border_color = "rgba(255,255,255,0.08)"
    text_color = "#ffffff"
    delta_color = "#8b90a0"
    glow = "rgba(255,255,255,0.0)"
    bar = "linear-gradient(90deg,#7c7cff,#b06cff)"

    if is_positive is not None:
        up = bool(is_positive)
        text_color = "#22d3a0" if up else "#ff5470"
        delta_color = text_color
        border_color = "rgba(34,211,160,0.28)" if up else "rgba(255,84,112,0.28)"
        glow = "rgba(34,211,160,0.45)" if up else "rgba(255,84,112,0.45)"
        bar = "linear-gradient(90deg,#22d3a0,#4ee3c1)" if up else "linear-gradient(90deg,#ff5470,#ff8a5c)"

    delta_html = ""
    if delta_text:
        if is_positive is None:
            delta_color = "#22d3a0" if ("+" in str(delta_text) or "MUA" in str(delta_text)) else ("#ff5470" if ("-" in str(delta_text) or "BÁN" in str(delta_text)) else "#8b90a0")
        delta_html = f"<div class='delta' style='color:{delta_color}'>{delta_text}</div>"

    safe_val = str(value_str).replace("'", "")
    try:
        raw_js = "null" if raw is None or pd.isna(raw) else repr(float(raw))
    except Exception:
        raw_js = "null"
    vn_js = "true" if vn else "false"
    html_code = f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600&family=JetBrains+Mono:wght@700&display=swap');
      html,body {{ margin:0; background:transparent; font-family:'Inter',sans-serif; overflow:hidden; }}
      @keyframes pop {{ from {{ opacity:0; transform:translateY(14px) scale(.96); }} to {{ opacity:1; transform:none; }} }}
      @keyframes sweep {{ from {{ transform:translateX(-130%); }} to {{ transform:translateX(260%); }} }}
      .card {{ position:relative; overflow:hidden; box-sizing:border-box; height:112px; padding:16px 18px; border-radius:16px;
        background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.02)); border:1px solid {border_color};
        box-shadow:0 10px 26px -14px rgba(0,0,0,.8), inset 0 1px 0 rgba(255,255,255,.07);
        display:flex; flex-direction:column; justify-content:center; animation:pop .6s cubic-bezier(.22,1,.36,1) both;
        transition:transform .35s cubic-bezier(.22,1,.36,1), box-shadow .35s; cursor:default; }}
      .card:hover {{ transform:translateY(-4px); box-shadow:0 20px 34px -16px rgba(0,0,0,.9), 0 0 0 1px rgba(124,124,255,.18); }}
      .card:active {{ transform:scale(.97); }}
      .card::before {{ content:""; position:absolute; left:0; top:0; height:3px; width:100%; background:{bar}; opacity:.9; }}
      .card::after {{ content:""; position:absolute; top:0; bottom:0; width:35%; background:linear-gradient(100deg,transparent,rgba(255,255,255,.07),transparent); transform:translateX(-130%); }}
      .card:hover::after {{ animation:sweep 1.1s ease; }}
      .lbl {{ color:#8b90a0; font-size:11.5px; font-weight:600; text-transform:uppercase; letter-spacing:.8px; margin-bottom:8px; }}
      .row {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
      .val {{ color:{text_color}; font-family:'JetBrains Mono',monospace; font-size:24px; font-weight:700; line-height:1; text-shadow:0 0 14px {glow}; white-space:nowrap; }}
      .delta {{ font-size:12.5px; font-weight:600; margin-top:9px; letter-spacing:.2px; }}
      .copy {{ position:relative; overflow:hidden; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); border-radius:9px; cursor:pointer; width:32px; height:32px;
        display:flex; align-items:center; justify-content:center; transition:all .25s; flex:0 0 auto; }}
      .copy:hover {{ background:rgba(124,124,255,.25); border-color:rgba(124,124,255,.5); transform:scale(1.08); }}
      .copy:active {{ transform:scale(.88); }}
    </style>
    <div class="card">
      <div class="lbl">{label}</div>
      <div class="row">
        <span class="val" id="vv">{value_str}</span>
        <button class="copy" id="cp" title="Copy" aria-label="Copy">
          <svg id="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8b90a0" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
        </button>
      </div>
      {delta_html}
    </div>
    <script>
      const cp = document.getElementById('cp'), ic = document.getElementById('ic');
      const copyIcon = ic.innerHTML;
      cp.addEventListener('click', () => {{
        const txt = '{safe_val}';
        try {{ navigator.clipboard.writeText(txt); }} catch(e) {{
          const t = document.createElement('textarea'); t.value = txt; document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove();
        }}
        ic.setAttribute('stroke', '#22d3a0'); ic.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';
        setTimeout(() => {{ ic.setAttribute('stroke', '#8b90a0'); ic.innerHTML = copyIcon; }}, 1600);
      }});
      const RAW = {raw_js}, DEC = {dec}, VN = {vn_js};
      if (RAW !== null) {{
        const vv = document.getElementById('vv');
        const f = v => VN ? v.toLocaleString('de-DE', {{minimumFractionDigits: DEC, maximumFractionDigits: DEC}}) : v.toFixed(DEC);
        const t0 = performance.now();
        const step = now => {{
          const p = Math.min(1, (now - t0) / 1000), e = 1 - Math.pow(1 - p, 4);
          vv.textContent = f(RAW * e);
          if (p < 1) requestAnimationFrame(step); else vv.textContent = '{safe_val}';
        }};
        requestAnimationFrame(step);
      }}
    </script>
    """
    components.html(html_code, height=124)


def get_trade_diagnosis(df, trade_plan):
    """Chuẩn đoán chất lượng lệnh và trả về HTML in đậm chuẩn"""
    last = df.iloc[-1]
    score = 0
    reasons = []

    if trade_plan['direction'] == "LONG":
        if last['EMA20'] > last['EMA50']:
            score += 30
            reasons.append("🟢 <b>Xu hướng:</b> EMA20 > EMA50 (Uptrend).")
        else:
            reasons.append("🔴 <b>Xu hướng:</b> EMA20 < EMA50 (Ngược xu hướng).")
    else:
        if last['EMA20'] < last['EMA50']:
            score += 30
            reasons.append("🟢 <b>Xu hướng:</b> EMA20 < EMA50 (Downtrend).")
        else:
            reasons.append("🔴 <b>Xu hướng:</b> EMA20 > EMA50 (Ngược xu hướng).")

    if trade_plan['direction'] == "LONG":
        if 40 < last['RSI'] < 70: score += 10; reasons.append("🟢 <b>RSI:</b> Nằm trong vùng an toàn (40-70).")
        if last['MACD_hist'] > 0: score += 10; reasons.append("🟢 <b>MACD:</b> Histogram dương (Động lượng tăng).")
    else:
        if 30 < last['RSI'] < 60: score += 10; reasons.append("🟢 <b>RSI:</b> Nằm trong vùng an toàn (30-60).")
        if last['MACD_hist'] < 0: score += 10; reasons.append("🟢 <b>MACD:</b> Histogram âm (Động lượng giảm).")

    if last['ADX'] > 25:
        score += 20
        reasons.append(f"🟢 <b>ADX ({last['ADX']:.1f}):</b> Xu hướng mạnh, đáng tin cậy.")
    elif last['ADX'] > 20:
        score += 10
        reasons.append(f"🟡 <b>ADX ({last['ADX']:.1f}):</b> Xu hướng hình thành.")
    else:
        reasons.append(f"🔴 <b>ADX ({last['ADX']:.1f}):</b> Thị trường đi ngang, dễ nhiễu.")

    if trade_plan['direction'] == "LONG" and last['Close'] < last['BB_lower']:
        score += 15; reasons.append("🟢 <b>Bollinger:</b> Giá chạm dải dưới (Quá bán).")
    elif trade_plan['direction'] == "SHORT" and last['Close'] > last['BB_upper']:
        score += 15; reasons.append("🟢 <b>Bollinger:</b> Giá chạm dải trên (Quá mua).")
    else:
        reasons.append("⚪ <b>Bollinger:</b> Giá đang ở giữa dải (Chưa tối ưu).")

    if last['ADX'] > 25: score += 15

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
    except Exception:
        return None


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
        except Exception:
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
    html("""
        <div class='sidebar-header'>
            <div class='sidebar-logo'>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>
            </div>
            <div>
                <h2 class='sidebar-title'>Nghia_Trading</h2>
                <div class='sidebar-subtitle'>Terminal UI</div>
            </div>
        </div>
    """)

    html("<div class='side-label'>Tài sản giao dịch</div>")
    selected_asset = st.selectbox("Asset", list(flat_assets.keys()), index=0, label_visibility="collapsed")
    ticker = flat_assets[selected_asset]

    html("<div style='height:14px'></div><div class='side-label'>Khung thời gian (Biểu đồ)</div>")
    timeframe = st.selectbox("TF", ["1 Phút", "5 Phút", "15 Phút", "1 Giờ", "1 Ngày", "1 Tuần"], index=4, label_visibility="collapsed")
    interval = {"1 Phút": "1m", "5 Phút": "5m", "15 Phút": "15m", "1 Giờ": "60m", "1 Ngày": "1d", "1 Tuần": "1wk"}[timeframe]

    html("<div style='height:10px'></div>")
    if st.button("🔄 Cập nhật dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    html(f"""
        <div class='pro-card'>
            <h4>Nghia_Trading Pro</h4>
            <p>Mở khóa tính năng Bot AI và dữ liệu Realtime.</p>
        </div>
        <div class='copyright'>© {datetime.now().year} Nghia_Trading.<br>All rights reserved.</div>
    """)

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

# HERO (khối giá + sparkline)
_spark = df["Close"].tail(80).astype(float).values
_n = len(_spark)
_mn, _mx = float(np.min(_spark)), float(np.max(_spark))
_rg = (_mx - _mn) or 1.0
_pts = [(i / max(_n - 1, 1) * 300, 54 - (float(v) - _mn) / _rg * 48) for i, v in enumerate(_spark)]
_line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in _pts)
_area = _line + " L300,60 L0,60 Z"
_up = change_pct >= 0
_c = "#22d3a0" if _up else "#ff5470"
_cbg = "rgba(34,211,160,.14)" if _up else "rgba(255,84,112,.14)"
_cbd = "rgba(34,211,160,.35)" if _up else "rgba(255,84,112,.35)"
_arrow = "▲" if _up else "▼"
_hi100, _lo100 = df["High"].tail(100).max(), df["Low"].tail(100).min()

html(f"""
    <div class='hero' style='--c:{_c}; --cbg:{_cbg}; --cbd:{_cbd};'>
        <div class='hero-in'>
            <div class='hero-top'>
                <div>
                    <div class='hero-name'>{selected_asset.split(' - ')[1]}</div>
                    <div class='hero-sub'>{ticker} • {timeframe}</div>
                </div>
                <div class='live-pill'><i></i><span>LIVE</span></div>
            </div>
            <div class='hero-mid'>
                <div>
                    <div class='hero-price nt-count' data-v='{float(last_close)}' data-d='2'>{format_vn_price(last_close)}</div>
                    <span class='chg'>{_arrow} {change_pct:+.2f}%</span>
                </div>
                <svg class='spark' viewBox='0 0 300 60'>
                    <defs><linearGradient id='sg' x1='0' y1='0' x2='0' y2='1'>
                        <stop offset='0%' stop-color='{_c}' stop-opacity='.35'/><stop offset='100%' stop-color='{_c}' stop-opacity='0'/>
                    </linearGradient></defs>
                    <path class='ar' d='{_area}' fill='url(#sg)'/>
                    <path class='ln' d='{_line}' pathLength='1'/>
                </svg>
            </div>
            <div class='hero-stats'>
                <div><span>Cao (100 nến)</span><b>{format_vn_price(_hi100)}</b></div>
                <div><span>Thấp (100 nến)</span><b>{format_vn_price(_lo100)}</b></div>
                <div><span>ATR (14)</span><b>{format_vn_price(df['ATR'].iloc[-1])}</b></div>
            </div>
        </div>
    </div>
""")

# MENU NGANG (viên thuốc, vuốt ngang trên di động)
menu_selection = st.radio(
    "Menu",
    ["📊 Biểu đồ", "🎯 Kế hoạch giao dịch", "🧠 Phân tích SMC", "🌐 Đa Khung Thời Gian", "📏 Fibonacci", "📰 Tin tức", "📓 Nhật ký"],
    horizontal=True, label_visibility="collapsed"
)
html("<div style='height:14px'></div>")

# ------------------------------------------------------------
# KHU VỰC 1: BIỂU ĐỒ (Bao gồm KPI)
# ------------------------------------------------------------
if menu_selection == "📊 Biểu đồ":
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1: quantum_metric("GIÁ HIỆN TẠI", format_vn_price(last_close), f"{change_pct:+.2f}%", is_positive=(change_pct >= 0), raw=last_close)
    with kpi2: quantum_metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}", "QUÁ MUA" if df['RSI'].iloc[-1] > 70 else ("QUÁ BÁN" if df['RSI'].iloc[-1] < 30 else "TRUNG TÍNH"), is_positive=(df['RSI'].iloc[-1] < 70), raw=df['RSI'].iloc[-1], dec=1, vn=False)
    with kpi3: quantum_metric("ADX (14)", f"{df['ADX'].iloc[-1]:.1f}", "XU HƯỚNG MẠNH" if df['ADX'].iloc[-1] > 25 else "ĐI NGANG", is_positive=None, raw=df['ADX'].iloc[-1], dec=1, vn=False)
    with kpi4: quantum_metric("ATR (14)", format_vn_price(df['ATR'].iloc[-1]), "ĐỘ BIẾN ĐỘNG", is_positive=None, raw=df['ATR'].iloc[-1])

    chart_df = df.tail(300).copy()

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("", "RSI (14)", "MACD (12, 26, 9)"))

    fig.add_trace(go.Candlestick(
        x=chart_df["Time"], open=chart_df["Open"], high=chart_df["High"], low=chart_df["Low"], close=chart_df["Close"], name="PRICE",
        increasing_line_color="#22d3a0", decreasing_line_color="#ff5470",
        increasing_fillcolor="#22d3a0", decreasing_fillcolor="#ff5470"
    ), row=1, col=1)

    active_trade = get_active_bot_trade(ticker)
    if active_trade is not None:
        fig.add_hline(y=active_trade['entry_price'], line_dash="solid", line_color="#7c7cff", line_width=1.5, annotation_text="ENTRY", row=1, col=1)
        fig.add_hline(y=active_trade['sl'], line_dash="dash", line_color="#ff5470", line_width=1, annotation_text="SL", row=1, col=1)
        fig.add_hline(y=active_trade['tp'], line_dash="dash", line_color="#22d3a0", line_width=1, annotation_text="TP", row=1, col=1)

    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["EMA20"], name="EMA 20", line=dict(color="#7c7cff", width=2, shape="spline", smoothing=0.6)), row=1, col=1)
    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["EMA50"], name="EMA 50", line=dict(color="#b06cff", width=1.5, dash='dot', shape="spline", smoothing=0.6)), row=1, col=1)

    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["RSI"], name="RSI", line=dict(color="#fbbf24", width=1.6), fill="tozeroy", fillcolor="rgba(251,191,36,0.05)"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff5470", line_width=1, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#22d3a0", line_width=1, row=2, col=1)

    fig.add_trace(go.Bar(x=chart_df["Time"], y=chart_df["MACD_hist"], name="MACD", marker_color=["#22d3a0" if v >= 0 else "#ff5470" for v in chart_df["MACD_hist"]]), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", height=720, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x", showlegend=False, margin=dict(l=10, r=50, t=30, b=10), dragmode="pan",
        font=dict(family="Inter, sans-serif", color="#8b90a0", size=12), uirevision='constant',
        hoverlabel=dict(bgcolor="rgba(12,13,20,0.92)", bordercolor="rgba(124,124,255,0.5)", font=dict(family="JetBrains Mono, monospace", size=12, color="#eef0f6")),
        transition=dict(duration=500, easing="cubic-in-out")
    )

    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", gridwidth=1, rangeslider_visible=False,
                     showspikes=True, spikecolor="rgba(124,124,255,0.5)", spikethickness=1, spikedash="dot", spikemode="across")
    fig.update_xaxes(rangeslider=dict(visible=True, bgcolor="rgba(255,255,255,0.02)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1), row=3, col=1)
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1D", step="day", stepmode="backward"),
                dict(count=7, label="1W", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(step="all", label="TẤT CẢ")
            ]),
            bgcolor="rgba(255,255,255,0.05)", activecolor="#7c7cff", font=dict(color="#c4c8d6")
        ), row=1, col=1
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", side="right", gridwidth=1)

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})
    st.caption("💡 **Mẹo di động:** Dùng 2 ngón tay để phóng to/thu nhỏ. Dùng 1 ngón tay để kéo biểu đồ. Hoặc dùng thanh trượt ở dưới cùng.")

# ------------------------------------------------------------
# KHU VỰC 2: KẾ HOẠCH GIAO DỊCH & CHUẨN ĐOÁN
# ------------------------------------------------------------
elif menu_selection == "🎯 Kế hoạch giao dịch":
    st.subheader("Chuẩn đoán & Kế hoạch giao dịch")

    col_left, col_right = st.columns([1.5, 1], gap="large")

    with col_left:
        rr_ratio = st.slider("Tỷ lệ R:R", 1.0, 4.0, 2.0, 0.5)
        trade_plan = calculate_trade_levels(df, risk_reward=rr_ratio)

        if trade_plan:
            direction_color = "#22d3a0" if trade_plan['direction'] == "LONG" else "#ff5470"
            direction_vn = "MUA (LONG)" if trade_plan['direction'] == "LONG" else "BÁN (SHORT)"

            score, quality, reasons = get_trade_diagnosis(df, trade_plan)
            reasons_html = "".join(f"<div class='reason-line' style='animation-delay:{0.1 + i * 0.07:.2f}s'>{r}</div>" for i, r in enumerate(reasons))

            _off = 264 * (1 - min(score, 100) / 100)
            html(f"""
                <div class='signal-card' style='--accent: {direction_color};'>
                    <div class='sig-head'>
                        <div class='ring'>
                            <svg viewBox='0 0 100 100'>
                                <defs><linearGradient id='rg' x1='0' y1='0' x2='1' y2='1'>
                                    <stop offset='0%' stop-color='#7c7cff'/><stop offset='100%' stop-color='#22d3a0'/>
                                </linearGradient></defs>
                                <circle cx='50' cy='50' r='42' class='ring-bg'/>
                                <circle cx='50' cy='50' r='42' class='ring-fg' stroke='url(#rg)' style='--off:{_off:.1f}'/>
                            </svg>
                            <div class='ring-num'><span class='nt-count' data-v='{score}' data-d='0'>{score}</span><small>/100</small></div>
                        </div>
                        <div class='sig-info'>
                            <div class='sig-kicker'>ĐIỂM CHẤT LƯỢNG</div>
                            <h3 style='color: {direction_color} !important;'>Tín hiệu: {direction_vn}</h3>
                            <div class='score-badge'>{quality}</div>
                        </div>
                    </div>
                    {reasons_html}
                </div>
            """)

            col_entry, col_sl, col_tp = st.columns(3)
            with col_entry: quantum_metric("GIÁ VÀO LỆNH", format_vn_price(trade_plan['entry']), "THỰC THI", is_positive=None, raw=trade_plan['entry'])
            with col_sl: quantum_metric("CẮT LỖ (SL)", format_vn_price(trade_plan['sl']), "BẢO VỆ VỐN", is_positive=False, raw=trade_plan['sl'])
            with col_tp: quantum_metric("CHỐT LỜI (TP)", format_vn_price(trade_plan['tp']), "MỤC TIÊU", is_positive=True, raw=trade_plan['tp'])

            be_wr = (1 / (1 + rr_ratio)) * 100
            html(f"""
                <div class='math-box'>
                    <b style='color:#fff;'>Toán học Giao dịch:</b> Với tỷ lệ R:R = 1:{rr_ratio:.1f}, bạn cần tỷ lệ thắng (Win rate) tối thiểu là <b style='color:#fbbf24;'>{be_wr:.1f}%</b> để hòa vốn. Nếu lịch sử của bạn cao hơn mức này, chiến lược này có lãi.
                </div>
            """)

    with col_right:
        balance = st.number_input("Số dư tài khoản ($)", value=1000.0, step=100.0)
        risk_pct = st.number_input("Rủi ro mỗi lệnh (%)", value=1.0, step=0.5)

        if trade_plan:
            risk_amount = balance * (risk_pct / 100)
            sl_distance = abs(trade_plan['entry'] - trade_plan['sl'])

            if sl_distance > 0:
                position_size = risk_amount / sl_distance
                leverage = (position_size * trade_plan['entry']) / balance if balance > 0 else 0

                html(f"""
                    <div class='glass-card'>
                        <div class='card-title'>🧮 Máy Tính Vị Thế</div>
                        <div class='row-item'><span>Tiền rủi ro tối đa:</span> <span class='val-data val-down'>${risk_amount:,.2f}</span></div>
                        <div class='row-item'><span>Khoảng cách SL:</span> <span class='val-data'>{format_vn_price(sl_distance)}</span></div>
                        <div class='row-item' style='margin-top: 14px; padding-top: 14px; border-top: 1px dashed rgba(255,255,255,0.1);'><span style='color: #fff; font-weight: 700;'>Khối lượng (Size):</span> <span class='val-data val-up' style='font-size: 20px;'>{position_size:,.4f}</span></div>
                        <div class='row-item'><span>Đòn bẩy (Leverage) khuyến nghị:</span> <span class='val-data' style='color: #fbbf24;'>x{leverage:.1f}</span></div>
                    </div>
                """)

    html("<div style='height:18px'></div>")
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
        html(f"""
            <div class='bot-active'>
                <div style='color: #c4a8ff; font-weight: 700; margin-bottom: 6px;'>⚡ BOT ĐANG GIỮ LỆNH: {dir_vn}</div>
                <div style='color: #e4e4e7; font-size: 14px;'>Vào lệnh: <b>{format_vn_price(active_bot['entry_price'])}</b> |
                SL: <span style='color:#ff5470'>{format_vn_price(active_bot['sl'])}</span> |
                TP: <span style='color:#22d3a0'>{format_vn_price(active_bot['tp'])}</span></div>
            </div>
        """)
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

        html("<div style='height:14px'></div>")
        display_df = bot_df.copy()
        display_df['open_time'] = pd.to_datetime(display_df['open_time']).dt.strftime('%d/%m/%Y %H:%M')
        display_df['close_time'] = pd.to_datetime(display_df['close_time']).dt.strftime('%d/%m/%Y %H:%M').fillna('-')
        display_df['direction'] = display_df['direction'].replace({'LONG': 'MUA', 'SHORT': 'BÁN'})
        display_df['status'] = display_df['status'].replace({'WIN': 'THẮNG', 'LOSS': 'THUA', 'CUT_EARLY': 'CẮT SỚM', 'ACTIVE': 'ĐANG MỞ'})
        for col in ['entry_price', 'exit_price', 'sl', 'tp']:
            display_df[col] = display_df[col].apply(lambda x: format_vn_price(x) if pd.notna(x) else '-')

        def color_bot_status(val):
            if val == 'THẮNG': return 'color: #22d3a0; font-weight: bold;'
            if val == 'THUA': return 'color: #ff5470; font-weight: bold;'
            if val == 'CẮT SỚM': return 'color: #8b90a0; font-weight: bold;'
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
                trend_color = "#22d3a0" if trend_val == 1 else ("#ff5470" if trend_val == -1 else "#8b90a0")

                bos_bull = structure.bos_bullish[-1] if isinstance(structure.bos_bullish, np.ndarray) else structure.bos_bullish
                bos_bear = structure.bos_bearish[-1] if isinstance(structure.bos_bearish, np.ndarray) else structure.bos_bearish
                choch_val = 0
                if hasattr(structure, 'choch'): choch_val = structure.choch[-1] if isinstance(structure.choch, np.ndarray) else structure.choch

                col_fvg, col_obs, col_struct = st.columns(3)
                with col_fvg:
                    html(f"""
                        <div class='glass-card'>
                            <div class='card-title'>📊 Fair Value Gaps</div>
                            <div class='row-item'><span>FVG Tăng:</span> <span class='val-data val-up'>{len(fvg.bullish)}</span></div>
                            <div class='row-item'><span>FVG Giảm:</span> <span class='val-data val-down'>{len(fvg.bearish)}</span></div>
                            <div class='row-item'><span>Đã lấp đầy:</span> <span class='val-data'>{len(fvg.mitigated_50)}</span></div>
                        </div>
                    """)
                with col_obs:
                    html(f"""
                        <div class='glass-card'>
                            <div class='card-title'>📦 Order Blocks</div>
                            <div class='row-item'><span>OB Cầu:</span> <span class='val-data val-up'>{len(obs.bullish_ob)}</span></div>
                            <div class='row-item'><span>OB Cung:</span> <span class='val-data val-down'>{len(obs.bearish_ob)}</span></div>
                            <div class='row-item'><span>OB Phá vỡ:</span> <span class='val-data'>{len(obs.is_breaker)}</span></div>
                        </div>
                    """)
                with col_struct:
                    html(f"""
                        <div class='glass-card'>
                            <div class='card-title'>📈 Cấu Trúc Giá</div>
                            <div class='row-item'><span>Xu hướng:</span> <span class='val-data' style='color: {trend_color};'>{trend_text}</span></div>
                            <div class='row-item'><span>BOS Tăng:</span> <span class='val-data val-up'>{'CÓ' if bos_bull else 'KHÔNG'}</span></div>
                            <div class='row-item'><span>BOS Giảm:</span> <span class='val-data val-down'>{'CÓ' if bos_bear else 'KHÔNG'}</span></div>
                            <div class='row-item'><span>CHOCH:</span> <span class='val-data'>{'CÓ' if choch_val != 0 else 'KHÔNG'}</span></div>
                        </div>
                    """)
            except Exception as e:
                st.error(f"Lỗi phân tích SMC: {e}")

# ------------------------------------------------------------
# KHU VỰC 4: ĐA KHUNG THỜI GIAN (MTF)
# ------------------------------------------------------------
elif menu_selection == "🌐 Đa Khung Thời Gian":
    st.subheader("Phân Tích Đa Khung Thời Gian (MTF)")
    html("<p style='color: #8b90a0; font-size: 14px; line-height:1.6;'>Hệ thống tự động quét xu hướng dựa trên giao cắt EMA20 và EMA50 trên 3 khung thời gian. Khi cả 3 khung đồng thuận, xác suất thắng sẽ cao hơn.</p>")

    mtf_data = load_mtf_data(ticker)
    col1, col2, col3 = st.columns(3)

    def render_mtf_card(col, tf_name, trend_val):
        color = "#22d3a0" if trend_val == "TĂNG" else ("#ff5470" if trend_val == "GIẢM" else "#8b90a0")
        icon = "📈" if trend_val == "TĂNG" else ("📉" if trend_val == "GIẢM" else "➖")
        with col:
            html(f"""
                <div class='glass-card mtf-card' style='border-top: 3px solid {color};'>
                    <div style='color: #8b90a0; font-size: 12px; font-weight: 700; letter-spacing: 1.2px;'>{tf_name}</div>
                    <div class='mtf-icon'>{icon}</div>
                    <div style='color: {color}; font-size: 21px; font-weight: 800;'>{trend_val}</div>
                </div>
            """)

    render_mtf_card(col1, "KHUNG 15 PHÚT", mtf_data.get("15 Phút", "N/A"))
    render_mtf_card(col2, "KHUNG 1 GIỜ", mtf_data.get("1 Giờ", "N/A"))
    render_mtf_card(col3, "KHUNG 1 NGÀY", mtf_data.get("1 Ngày", "N/A"))

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
            html(f"""
                <div class='glass-card'>
                    <div class='card-title'>📍 Điểm Neo (Swing)</div>
                    <div class='row-item'><span>Đỉnh (Swing High):</span> <span class='val-data val-down'>{format_vn_price(fib_data['Swing High'])}</span></div>
                    <div class='row-item'><span>Đáy (Swing Low):</span> <span class='val-data val-up'>{format_vn_price(fib_data['Swing Low'])}</span></div>
                </div>
            """)
        with col_levels:
            html(f"""
                <div class='glass-card'>
                    <div class='card-title'>📏 Các Mức Hỗ Trợ / Kháng Cự</div>
                    <div class='row-item'><span>Fib 0.236:</span> <span class='val-data'>{format_vn_price(fib_data['Fib 0.236'])}</span></div>
                    <div class='row-item'><span>Fib 0.382:</span> <span class='val-data'>{format_vn_price(fib_data['Fib 0.382'])}</span></div>
                    <div class='row-item'><span>Fib 0.500 (Vàng):</span> <span class='val-data' style='color: #fbbf24;'>{format_vn_price(fib_data['Fib 0.500'])}</span></div>
                    <div class='row-item'><span>Fib 0.618 (Vàng):</span> <span class='val-data' style='color: #fbbf24;'>{format_vn_price(fib_data['Fib 0.618'])}</span></div>
                    <div class='row-item'><span>Fib 0.786:</span> <span class='val-data'>{format_vn_price(fib_data['Fib 0.786'])}</span></div>
                </div>
            """)
        st.info("💡 **Mẹo:** Mức 0.5 và 0.618 (Golden Ratio) là những vùng phản ứng giá rất mạnh. Nếu giá hồi về đây và có tín hiệu đảo chiều, đó là điểm vào lệnh tuyệt vời.")
    else:
        st.warning("Không đủ dữ liệu để tính Fibonacci.")

# ------------------------------------------------------------
# KHU VỰC 6: TIN TỨC
# ------------------------------------------------------------
elif menu_selection == "📰 Tin tức":
    st.subheader(f"Tin tức: {selected_asset.split(' - ')[1]}")
    news = fetch_news(ticker)
    if not news:
        st.info("Hiện chưa có tin tức cho tài sản này.")
    for item in news:
        safe_link = str(item['link']).replace("'", "%27")
        html(f"""
            <div class='glass-card news-card' onclick="window.open('{safe_link}', '_blank')">
                <div class='news-title'>{item['title']}</div>
                <div style='color: #8b90a0; font-size: 12px; display: flex; align-items: center; gap: 6px;'>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    {item['published']}
                </div>
            </div>
        """)

# ------------------------------------------------------------
# KHU VỰC 7: NHẬT KÝ GIAO DỊCH
# ------------------------------------------------------------
elif menu_selection == "📓 Nhật ký":
    st.subheader("Nhật ký giao dịch thủ công")
    col_form, col_history = st.columns([1, 2], gap="large")

    with col_form:
        with st.form("journal_form", clear_on_submit=True):
            html("<p style='color: #ffffff; font-weight: 700; margin-bottom: 12px;'>➕ Ghi nhận lệnh mới</p>")
            trade_date = st.date_input("Ngày")
            asset_name = st.text_input("Tài sản", value=selected_asset.split(' - ')[1])
            direction = st.selectbox("Hướng", ["LONG", "SHORT"])
            result = st.selectbox("Kết quả", ["THẮNG", "THUA", "HÒA"])
            pnl_val = st.number_input("PnL", value=0.0, step=0.1)
            reason = st.text_area("Lý do", placeholder="Nhập ghi chú...")
            if st.form_submit_button("Lưu dữ liệu", use_container_width=True):
                add_trade(str(trade_date), asset_name.upper(), direction, result, reason, pnl_val)
                st.rerun()

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
            c3.metric("Tổng PnL", f"{total_pnl:+.2f}", delta_color="normal" if total_pnl >= 0 else "inverse")

            html("<div style='height:14px'></div>")

            col_filter1, col_filter2 = st.columns(2)
            years = journal_df['date'].dt.year.dropna().unique()
            if len(years) > 0:
                selected_year = col_filter1.selectbox("Năm", sorted(years, reverse=True))
                months = journal_df[journal_df['date'].dt.year == selected_year]['date'].dt.month.dropna().unique()
                selected_month = col_filter2.selectbox("Tháng", sorted(months, reverse=True))

                filtered_df = journal_df[(journal_df['date'].dt.year == selected_year) & (journal_df['date'].dt.month == selected_month)].copy()
                filtered_df['date'] = filtered_df['date'].dt.strftime('%d/%m/%Y')

                def color_result(val):
                    if val == 'THẮNG': return 'color: #22d3a0; font-weight: bold;'
                    elif val == 'THUA': return 'color: #ff5470; font-weight: bold;'
                    return 'color: #8b90a0;'

                def color_pnl(val):
                    try:
                        val = float(val)
                        if val > 0: return 'color: #22d3a0;'
                        elif val < 0: return 'color: #ff5470;'
                    except Exception: pass
                    return 'color: #8b90a0;'

                st.dataframe(filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style.map(color_result, subset=['result']).map(color_pnl, subset=['pnl']), hide_index=True, use_container_width=True)
