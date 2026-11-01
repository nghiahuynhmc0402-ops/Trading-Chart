import json
import random as _random
import warnings
warnings.filterwarnings("ignore", module="yfinance")
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

/* ===================== V3: VŨ TRỤ ===================== */
:root {
    --bg: #02030a; --brand: #8b7bff; --brand2: #ff5ecb; --cyan: #38e1ff;
    --up: #2de2a6; --down: #ff4d7d;
    --line: rgba(180,170,255,.11); --line-hi: rgba(180,170,255,.30);
}
@keyframes twinkle { 0% { opacity: .35; } 50% { opacity: 1; } 100% { opacity: .55; } }
@keyframes spin2 { to { transform: rotate(360deg); } }
@keyframes floatPlanet { 0%,100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-16px) rotate(4deg); } }
@keyframes ringPulse { 0%,100% { opacity: .55; transform: scale(1); } 50% { opacity: .95; transform: scale(1.035); } }
@keyframes shimmerText { to { background-position: 200% center; } }

html, body { background: #02030a !important; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"], [data-testid="stBottom"] { background: transparent !important; }

/* Tinh vân */
.stApp::before {
    top: -20vh; left: -20vw; width: 140vw; height: 140vh; border-radius: 0; filter: blur(60px); opacity: .95;
    background:
        radial-gradient(40% 35% at 20% 25%, rgba(120,90,255,.30), transparent 70%),
        radial-gradient(35% 30% at 80% 18%, rgba(56,225,255,.17), transparent 70%),
        radial-gradient(45% 40% at 72% 85%, rgba(255,94,203,.17), transparent 70%),
        radial-gradient(30% 30% at 10% 90%, rgba(45,226,166,.10), transparent 70%);
    animation: drift1 34s ease-in-out infinite alternate;
}
/* Sao CSS (dự phòng, ẩn khi canvas chạy) */
.stApp::after {
    top: 0; left: 0; bottom: auto; right: auto; width: 1px; height: 1px; border-radius: 0; filter: none; opacity: 1; background: transparent;
    box-shadow: __STARS__;
    animation: twinkle 5s ease-in-out infinite alternate;
}
html.nt-canvas .stApp::after { display: none; }

/* Quỹ đạo khổng lồ + hành tinh */
[data-testid="stAppViewContainer"]::before {
    inset: auto; right: -34vmax; top: -34vmax; width: 86vmax; height: 86vmax; border-radius: 50%;
    background-image: repeating-radial-gradient(circle at center, transparent 0 7vmax, rgba(150,140,255,.08) calc(7vmax + 1px) calc(7vmax + 2px)) !important;
    background-size: auto !important;
    -webkit-mask-image: radial-gradient(circle, #000 0%, transparent 68%); mask-image: radial-gradient(circle, #000 0%, transparent 68%);
    animation: ringPulse 10s ease-in-out infinite;
}
[data-testid="stAppViewContainer"]::after {
    content: ""; position: fixed; left: -9vmax; bottom: 5vh; width: 22vmax; height: 22vmax; border-radius: 50%;
    z-index: 0; pointer-events: none; opacity: .5;
    background: radial-gradient(circle at 32% 28%, rgba(255,255,255,.28), rgba(139,123,255,.55) 18%, rgba(60,40,150,.85) 45%, rgba(8,6,30,.96) 72%);
    box-shadow: inset -2vmax -2vmax 4vmax rgba(0,0,0,.65), 0 0 6vmax rgba(139,123,255,.28);
    animation: floatPlanet 14s ease-in-out infinite;
}
@media (max-width: 768px) {
    [data-testid="stAppViewContainer"]::after { width: 34vmax; height: 34vmax; left: -16vmax; bottom: 2vh; opacity: .4; }
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(12,9,32,.80), rgba(3,4,14,.90)) !important;
    border-right: 1px solid var(--line-hi); position: relative; z-index: 2;
}
.sidebar-logo {
    position: relative; border-radius: 50% !important;
    background: radial-gradient(circle at 30% 30%, #fff 0, #c3b6ff 12%, #6a4cff 45%, #1b1250 100%) !important;
    animation: floaty 4s ease-in-out infinite !important;
    box-shadow: 0 0 24px rgba(139,123,255,.75), inset -6px -6px 12px rgba(0,0,0,.5) !important;
}
.sidebar-logo svg { position: relative; z-index: 1; }
.sidebar-logo::after {
    content: ""; position: absolute; left: -11px; right: -11px; top: 50%; height: 15px; margin-top: -7px;
    border: 1.5px solid rgba(56,225,255,.75); border-radius: 50%; transform: rotate(-24deg); box-shadow: 0 0 9px rgba(56,225,255,.5);
}
.sidebar-title { background: linear-gradient(90deg, #fff, #b9a8ff, #38e1ff); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }

/* Nút bấm vũ trụ */
.stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button {
    background: linear-gradient(120deg, #6a4cff, #b24cff, #ff5ecb, #6a4cff) !important; background-size: 250% 100% !important;
    animation: gradShift 6s linear infinite; box-shadow: 0 8px 26px -8px rgba(178,76,255,.7);
}
.stButton>button:hover, .stDownloadButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover { box-shadow: 0 14px 34px -8px rgba(255,94,203,.75); }

/* Menu */
div[data-testid="stRadio"] > div[role="radiogroup"] { background: rgba(10,8,30,.55); border-color: var(--line-hi); }
div[data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(135deg, rgba(139,123,255,.34), rgba(255,94,203,.22)) !important;
    border: 1px solid rgba(160,140,255,.55) !important; box-shadow: 0 6px 22px -6px rgba(139,123,255,.7), inset 0 1px 0 rgba(255,255,255,.12) !important;
}

/* Hero vũ trụ */
.hero { background: conic-gradient(from var(--ang), rgba(255,255,255,.07) 0%, rgba(255,255,255,.07) 48%, var(--cyan) 68%, var(--c) 80%, var(--brand2) 92%, rgba(255,255,255,.07) 100%); }
.hero-in { background: linear-gradient(160deg, rgba(14,10,38,.94), rgba(4,5,16,.97)); }
.hero-name { background: linear-gradient(90deg, #fff, #b9a8ff, #38e1ff, #ff5ecb, #fff); background-size: 200% auto; -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; animation: shimmerText 7s linear infinite; }
.hero-top, .hero-mid, .hero-stats { z-index: 1; }
.orbit { position: absolute; right: -34px; top: -34px; width: 240px; height: 240px; pointer-events: none; opacity: .9; }
.orbit i { position: absolute; border: 1px solid rgba(139,123,255,.30); border-radius: 50%; animation: spin2 var(--t, 18s) linear infinite; }
.orbit i:nth-child(1) { inset: 0; --t: 24s; }
.orbit i:nth-child(2) { inset: 30px; --t: 15s; animation-direction: reverse; }
.orbit i:nth-child(3) { inset: 60px; --t: 9s; }
.orbit i::after { content: ""; position: absolute; top: -4px; left: 50%; margin-left: -4px; width: 8px; height: 8px; border-radius: 50%; background: var(--c); box-shadow: 0 0 12px 2px var(--c); }
.orbit i:nth-child(2)::after { background: var(--cyan); box-shadow: 0 0 12px 2px var(--cyan); width: 6px; height: 6px; margin-left: -3px; top: -3px; }
.orbit i:nth-child(3)::after { background: var(--brand2); box-shadow: 0 0 12px 2px var(--brand2); }

/* Thẻ chỉ số (không còn iframe) */
.qm {
    position: relative; overflow: hidden; box-sizing: border-box; min-height: 112px; padding: 16px 18px; border-radius: 16px;
    display: flex; flex-direction: column; justify-content: center; margin-bottom: 6px;
    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02)); border: 1px solid var(--bc);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    box-shadow: 0 10px 26px -14px rgba(0,0,0,.8), inset 0 1px 0 rgba(255,255,255,.07);
    transition: transform .35s var(--ease), box-shadow .35s var(--ease);
}
.qm::before { content: ""; position: absolute; left: 0; top: 0; height: 3px; width: 100%; background: var(--bar); }
.qm::after { content: ""; position: absolute; top: 0; bottom: 0; width: 35%; background: linear-gradient(100deg, transparent, rgba(255,255,255,.09), transparent); transform: translateX(-130%); pointer-events: none; }
.qm:hover { transform: translateY(-4px); box-shadow: 0 20px 34px -16px rgba(0,0,0,.9), 0 0 0 1px rgba(139,123,255,.25); }
.qm:hover::after { animation: sweep 1.1s ease; }
.qm:active { transform: scale(.97); }
.qm-lbl { color: var(--muted); font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: .8px; margin-bottom: 8px; }
.qm-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.qm-val { color: var(--tc); font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 700; line-height: 1; text-shadow: 0 0 14px var(--gl); white-space: nowrap; }
.qm-delta { font-size: 12.5px; font-weight: 600; margin-top: 9px; letter-spacing: .2px; }
.nt-copy {
    position: relative; width: 32px; height: 32px; flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center;
    border-radius: 9px; cursor: pointer; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); color: #8b90a0; transition: all .25s;
}
.nt-copy:hover { background: rgba(139,123,255,.28); border-color: rgba(139,123,255,.55); transform: scale(1.08); color: #fff; }
.nt-copy:active { transform: scale(.88); }
.nt-copy .i-ok { display: none; color: #2de2a6; }
.nt-copy.ok .i-ok { display: inline; }
.nt-copy.ok .i-copy { display: none; }
@media (max-width: 640px) { .qm-val { font-size: 20px; } }

a.news-card { display: block; text-decoration: none; color: inherit; }

/* ===================== V4: WARP / LẬT / XOAY ===================== */
@keyframes warpIn { from { opacity: 0; transform: perspective(1200px) translateZ(-280px) rotateX(16deg) scale(.93); filter: blur(10px) brightness(1.8); } }
@keyframes coin { to { transform: rotateY(360deg); } }
.block-container [data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"],
.block-container [data-testid="stVerticalBlock"] > div[data-testid="element-container"] { animation: warpIn .85s var(--ease) both; }
[data-testid="stHorizontalBlock"] > div { animation: warpIn .8s var(--ease) both; }
html.nt-warping .block-container { animation: none; }

/* Hero: kéo / chạm để xoay, nảy lò xo khi thả */
.hero {
    transform: perspective(1100px) rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg));
    transition: transform .65s cubic-bezier(.2,1.5,.4,1), box-shadow .4s;
    cursor: grab; touch-action: pan-y; user-select: none; -webkit-user-select: none; will-change: transform;
    animation: spin 7s linear infinite, warpIn .9s var(--ease) both;
}
.hero.drag { transition: transform .08s linear; cursor: grabbing; box-shadow: 0 40px 90px -30px var(--c), 0 0 0 1px rgba(255,255,255,.12); }
.orbit { transition: transform .9s var(--ease); }
.hero.drag .orbit { transform: scale(1.18) rotate(40deg); }
.hint { color: var(--dim); font-size: 11px; margin-left: 8px; }

/* Thẻ lật 3D */
.flip { position: relative; perspective: 1100px; cursor: pointer; margin-bottom: 14px; transition: transform .35s var(--ease); }
.flip:hover { transform: translateY(-4px); }
.flip-in { position: relative; transform-style: preserve-3d; transition: transform .95s cubic-bezier(.34,1.45,.5,1); }
.flip.flipped .flip-in { transform: rotateY(180deg); }
.ff, .fb { backface-visibility: hidden; -webkit-backface-visibility: hidden; }
.ff { position: relative; }
.ff::after { content: "⟳"; position: absolute; right: 11px; bottom: 6px; font-size: 13px; color: var(--dim); pointer-events: none; }
.flip .glass-card, .flip .qm { margin-bottom: 0; backdrop-filter: none; -webkit-backdrop-filter: none; }
.flip .qm:hover { transform: none; }
.fb {
    position: absolute; inset: 0; transform: rotateY(180deg); border-radius: 17px; padding: 14px 18px; box-sizing: border-box;
    display: flex; flex-direction: column; justify-content: center; gap: 6px; overflow: hidden;
    background: radial-gradient(120% 120% at 20% 0%, rgba(139,123,255,.38), rgba(10,8,30,.97) 62%), #0a0820;
    border: 1px solid rgba(160,140,255,.5); box-shadow: 0 0 30px -6px rgba(139,123,255,.65), inset 0 0 34px rgba(56,225,255,.09);
}
.fb::before { content: ""; position: absolute; inset: -60%; background: conic-gradient(from 0deg, transparent 0 70%, rgba(56,225,255,.22), transparent); animation: spin2 5s linear infinite; pointer-events: none; }
.fb b, .fb span { position: relative; }
.fb b { color: #fff; font-size: 12px; letter-spacing: .8px; }
.fb span { color: #cfd1e6; font-size: 12.5px; line-height: 1.5; }
.mtf-icon { animation: coin 5s cubic-bezier(.6,0,.4,1) infinite; }

footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
"""
def _stars(n, seed):
    r = _random.Random(seed)
    cols = ["255,255,255", "190,215,255", "255,205,235"]
    return ",".join(
        f"{r.randint(0, 100)}vw {r.randint(0, 100)}vh 0 {r.choice([0, 0, 0, 1])}px rgba({r.choice(cols)},{r.choice([.5, .7, .9])})"
        for _ in range(n)
    )


APP_CSS = APP_CSS.replace("__STARS__", _stars(150, 7))
st.markdown(APP_CSS, unsafe_allow_html=True)

# ---------- Hiệu ứng vũ trụ + chạm (JS được chèn 1 lần vào trang cha) ----------
FX_JS = r"""
(function(){
  if (window.__ntFx3) return; window.__ntFx3 = true;
  var D = document;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- Đèn rọi + nghiêng 3D ---- */
  D.addEventListener('pointermove', function(e){
    var c = e.target.closest && e.target.closest('.glass-card'); if (!c) return;
    var r = c.getBoundingClientRect();
    c.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    c.style.setProperty('--my', (e.clientY - r.top) + 'px');
    if (e.pointerType === 'mouse') {
      c.style.setProperty('--rx', (-((e.clientY - r.top) / r.height - .5) * 7).toFixed(2) + 'deg');
      c.style.setProperty('--ry', (((e.clientX - r.left) / r.width - .5) * 7).toFixed(2) + 'deg');
    }
  }, {passive:true});
  D.addEventListener('pointerout', function(e){
    var c = e.target.closest && e.target.closest('.glass-card');
    if (c && !(e.relatedTarget && c.contains(e.relatedTarget))) { c.style.setProperty('--rx','0deg'); c.style.setProperty('--ry','0deg'); }
  }, {passive:true});

  /* ---- Nút copy ---- */
  function fallbackCopy(txt){
    var t = D.createElement('textarea'); t.value = txt; D.body.appendChild(t); t.select();
    try { D.execCommand('copy'); } catch(err) {}
    t.remove();
  }
  D.addEventListener('click', function(e){
    var b = e.target.closest && e.target.closest('.nt-copy'); if (!b) return;
    var txt = b.getAttribute('data-copy') || 'x';
    try { navigator.clipboard.writeText(txt).catch(function(){ fallbackCopy(txt); }); } catch(err) { fallbackCopy(txt); }
    b.classList.add('ok'); setTimeout(function(){ b.classList.remove('ok'); }, 1600);
  });

  /* ---- Số chạy (count-up) ---- */
  var fmt = function(v, d){ return v.toLocaleString('de-DE', {minimumFractionDigits: d, maximumFractionDigits: d}); };
  var run = function(){
    D.querySelectorAll('.nt-count:not([data-done])').forEach(function(el){
      el.setAttribute('data-done', '1');
      var to = parseFloat(el.getAttribute('data-v')), d = parseInt(el.getAttribute('data-d') || '0', 10);
      var plain = el.getAttribute('data-vn') === '0';
      if (isNaN(to)) return;
      var orig = el.textContent, t0 = performance.now(), dur = 1200;
      var step = function(now){
        var p = Math.min(1, (now - t0) / dur), k = 1 - Math.pow(1 - p, 4);
        el.textContent = plain ? (to * k).toFixed(d) : fmt(to * k, d);
        if (p < 1) requestAnimationFrame(step); else el.textContent = orig;
      };
      requestAnimationFrame(step);
    });
  };
  run();
  new MutationObserver(run).observe(D.body, {childList: true, subtree: true});

  if (reduce) return;

  /* ---- Vũ trụ: sao lấp lánh, thị sai, sao băng, bụi sao khi chạm ---- */
  var cv = D.createElement('canvas');
  cv.id = 'nt-cosmos'; cv.style.cssText = 'position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:0;pointer-events:none';
  D.body.appendChild(cv);
  D.documentElement.classList.add('nt-canvas');
  var dpr = Math.min(window.devicePixelRatio || 1, 2), w = 0, h = 0;
  var a = cv.getContext('2d');
  function size(){
    w = window.innerWidth; h = window.innerHeight;
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    a.setTransform(dpr,0,0,dpr,0,0);
  }
  size(); window.addEventListener('resize', size);

  var N = window.innerWidth < 700 ? 80 : 160, stars = [], shoot = [];
  var cols = ['255,255,255', '190,215,255', '255,205,235', '170,255,240'];
  for (var i = 0; i < N; i++) {
    var z = Math.random() * .9 + .1;
    stars.push({x: Math.random(), y: Math.random(), z: z, r: .35 + z * 1.15, tw: Math.random() * 6.28, sp: .5 + Math.random() * 2, c: cols[Math.floor(Math.random() * cols.length)]});
  }
  var tx = 0, ty = 0, px = 0, py = 0, sy = 0, lastTrail = 0;
  var pal = ['139,123,255', '56,225,255', '255,94,203', '255,255,255', '45,226,166'];

  D.addEventListener('pointermove', function(e){
    tx = e.clientX / w - .5; ty = e.clientY / h - .5;
  }, {passive:true});
  D.addEventListener('scroll', function(e){ var t = e.target; if (t && typeof t.scrollTop === 'number') sy = t.scrollTop; }, true);

  var last = 0;
  function frame(t){
    requestAnimationFrame(frame);
    if (D.hidden || t - last < 30) return;
    var dt = Math.min((t - last) / 16.7, 3); last = t;
    px += (tx - px) * .04; py += (ty - py) * .04;
    a.clearRect(0, 0, w, h);
    for (var i = 0; i < stars.length; i++) {
      var s = stars[i];
      var x = ((s.x * w - px * 40 * s.z) % w + w) % w;
      var y = ((s.y * h - py * 40 * s.z - sy * .04 * s.z) % h + h) % h;
      var al = .3 + .7 * (.5 + .5 * Math.sin(t * .0012 * s.sp + s.tw));
      a.fillStyle = 'rgba(' + s.c + ',' + al.toFixed(3) + ')';
      a.beginPath(); a.arc(x, y, s.r, 0, 6.283); a.fill();
      if (s.r > 1.1) { a.fillStyle = 'rgba(' + s.c + ',' + (al * .16).toFixed(3) + ')'; a.beginPath(); a.arc(x, y, s.r * 3.4, 0, 6.283); a.fill(); }
    }
    if (shoot.length < 2 && Math.random() < .005) {
      shoot.push({x: Math.random() * w * .9, y: Math.random() * h * .35, vx: 7 + Math.random() * 5, vy: 3 + Math.random() * 3, l: 1});
    }
    for (var k = shoot.length - 1; k >= 0; k--) {
      var m = shoot[k];
      m.x += m.vx * dt; m.y += m.vy * dt; m.l -= .016 * dt;
      var g = a.createLinearGradient(m.x, m.y, m.x - m.vx * 10, m.y - m.vy * 10);
      g.addColorStop(0, 'rgba(255,255,255,' + Math.max(m.l, 0).toFixed(3) + ')'); g.addColorStop(1, 'rgba(139,123,255,0)');
      a.strokeStyle = g; a.lineWidth = 1.6; a.beginPath(); a.moveTo(m.x, m.y); a.lineTo(m.x - m.vx * 10, m.y - m.vy * 10); a.stroke();
      if (m.l <= 0 || m.x > w + 50 || m.y > h + 50) shoot.splice(k, 1);
    }
  }
  requestAnimationFrame(frame);
})();
"""


FX_JS2 = r"""
(function(){
  if (window.__ntFx4) return; window.__ntFx4 = true;
  var D = document, reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var q = function(e, s){ return e.target.closest && e.target.closest(s); };

  /* ---- Lật thẻ khi chạm ---- */
  D.addEventListener('click', function(e){
    var f = q(e, '.flip'); if (!f || q(e, '.nt-copy') || q(e, 'a')) return;
    f.classList.toggle('flipped');
  });
  if (reduce) return;

  /* ---- Canvas warp (chuyển cảnh) + sóng chạm ---- */
  var cv = D.createElement('canvas');
  cv.id = 'nt-warp'; cv.style.cssText = 'position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:99998;pointer-events:none';
  D.body.appendChild(cv);
  var c = cv.getContext('2d'), w = 0, h = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
  function size(){ w = window.innerWidth; h = window.innerHeight; cv.width = w * dpr; cv.height = h * dpr; c.setTransform(dpr,0,0,dpr,0,0); }
  size(); window.addEventListener('resize', size);
  var pal = ['139,123,255', '56,225,255', '255,94,203', '255,255,255'];
  var st = [], rings = [], t0 = 0, on = false, running = false, last = 0, DUR = 1000;

  function go(){ if (!running) { running = true; last = performance.now(); requestAnimationFrame(tick); } }
  function warp(){
    t0 = performance.now(); on = true; st = [];
    for (var i = 0, n = w < 700 ? 110 : 230; i < n; i++) st.push({a: Math.random() * 6.283, r: Math.random() * .12, v: .5 + Math.random(), c: pal[i % 4]});
    D.documentElement.classList.add('nt-warping'); go();
  }
  function ring(x, y){ rings.push({x: x, y: y, r: 4, l: 1}, {x: x, y: y, r: -10, l: .7}); go(); }
  function roll(){
    var el = D.querySelector('.hero'); if (!el || !el.animate) return;
    el.animate([{transform: 'perspective(1100px) rotateY(0deg)'}, {transform: 'perspective(1100px) rotateY(360deg) scale(1.03)'}, {transform: 'perspective(1100px) rotateY(360deg)'}], {duration: 1100, easing: 'cubic-bezier(.3,.9,.3,1)'});
  }

  function tick(t){
    var dt = Math.min((t - last) / 16.7, 3); last = t;
    c.clearRect(0, 0, w, h);
    var cx = w / 2, cy = h * .42, dg = Math.hypot(w, h) / 2;
    if (on) {
      var p = (t - t0) / DUR;
      if (p >= 1) { on = false; D.documentElement.classList.remove('nt-warping'); }
      else {
        var k = Math.sin(p * Math.PI), g = c.createRadialGradient(cx, cy, 0, cx, cy, dg * .9);
        g.addColorStop(0, 'rgba(190,170,255,' + (.3 * k * k).toFixed(3) + ')');
        g.addColorStop(.5, 'rgba(90,60,220,' + (.1 * k).toFixed(3) + ')');
        g.addColorStop(1, 'rgba(0,0,0,0)');
        c.fillStyle = g; c.fillRect(0, 0, w, h); c.lineCap = 'round';
        for (var i = 0; i < st.length; i++) {
          var s = st[i]; s.r += s.v * (.003 + .045 * k * k) * dt; if (s.r > 1.05) s.r = Math.random() * .06;
          var r1 = s.r * dg * 1.1, r0 = Math.max(r1 - (6 + 240 * k * k) * s.v, 0), co = Math.cos(s.a), si = Math.sin(s.a);
          c.strokeStyle = 'rgba(' + s.c + ',' + Math.min(1, .15 + k * 1.1).toFixed(3) + ')'; c.lineWidth = .6 + s.r * 1.8;
          c.beginPath(); c.moveTo(cx + co * r0, cy + si * r0); c.lineTo(cx + co * r1, cy + si * r1); c.stroke();
        }
      }
    }
    for (var j = rings.length - 1; j >= 0; j--) {
      var o = rings[j]; o.r += (7 + o.r * .06) * dt; o.l -= .025 * dt;
      if (o.l <= 0) { rings.splice(j, 1); continue; }
      if (o.r <= 0) continue;
      c.strokeStyle = 'rgba(' + (j % 2 ? '56,225,255' : '139,123,255') + ',' + o.l.toFixed(3) + ')'; c.lineWidth = 2.2 * o.l + .4;
      c.beginPath(); c.arc(o.x, o.y, o.r, 0, 6.283); c.stroke();
    }
    if (on || rings.length) requestAnimationFrame(tick); else { running = false; c.clearRect(0, 0, w, h); }
  }

  /* Chạm: sóng xung kích; đổi tab / tài sản / làm mới: warp + hero xoay 360° */
  D.addEventListener('pointerdown', function(e){
    if (q(e, 'div[data-testid="stRadio"] label')) { warp(); roll(); }
    else if (q(e, 'li[role="option"]') || q(e, '.stButton>button')) warp();
  }, {passive: true});

  /* ---- Hero: kéo để xoay (chuột + cảm ứng), rê chuột nghiêng nhẹ, con quay hồi chuyển ---- */
  var drag = null;
  function tilt(el, e, amp){
    var r = el.getBoundingClientRect();
    el.style.setProperty('--ry', (((e.clientX - r.left) / r.width - .5) * amp).toFixed(1) + 'deg');
    el.style.setProperty('--rx', (-((e.clientY - r.top) / r.height - .5) * amp).toFixed(1) + 'deg');
  }
  function reset(el){ el.style.setProperty('--rx', '0deg'); el.style.setProperty('--ry', '0deg'); }
  D.addEventListener('pointerdown', function(e){ var el = q(e, '.hero'); if (!el) return; drag = el; el.classList.add('drag'); tilt(el, e, 30); }, {passive: true});
  D.addEventListener('pointermove', function(e){
    if (drag) return tilt(drag, e, 30);
    var el = e.pointerType === 'mouse' && q(e, '.hero'); if (el) tilt(el, e, 10);
  }, {passive: true});
  D.addEventListener('pointerout', function(e){
    var el = q(e, '.hero'); if (el && !drag && !(e.relatedTarget && el.contains(e.relatedTarget))) reset(el);
  }, {passive: true});
  function end(){ if (!drag) return; drag.classList.remove('drag'); reset(drag); drag = null; }
  D.addEventListener('pointerup', end); D.addEventListener('pointercancel', end);
  window.addEventListener('deviceorientation', function(e){
    var el = D.querySelector('.hero'); if (!el || drag || e.gamma == null) return;
    el.style.setProperty('--ry', Math.max(-12, Math.min(12, e.gamma / 3)).toFixed(1) + 'deg');
    el.style.setProperty('--rx', Math.max(-12, Math.min(12, ((e.beta || 45) - 45) / 4)).toFixed(1) + 'deg');
  }, {passive: true});
})();
"""


def inject_js(code: str):
    """Chèn script vào trang cha 1 lần (chạy bền vững, không phụ thuộc vòng đời iframe)."""
    loader = ("<script>(function(){try{var P=window.parent,D=P.document;"
              "if(D.getElementById('nt-fx-v4'))return;"
              "var s=D.createElement('script');s.id='nt-fx-v4';s.textContent=" + json.dumps(code) + ";"
              "D.head.appendChild(s);}catch(e){}})();</" + "script>")
    try:
        components.html(loader, height=0)
    except Exception:
        try:
            st.iframe(loader, height=1)
        except Exception:
            pass


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


def to_vn_naive(x):
    """Chuẩn hoá mọi mốc thời gian về giờ Việt Nam, không múi giờ (tránh lỗi tz-naive vs tz-aware)."""
    if x is None:
        return pd.NaT
    try:
        ts = pd.Timestamp(x)
    except Exception:
        return pd.NaT
    if pd.isna(ts):
        return pd.NaT
    if ts.tzinfo is not None:
        ts = ts.tz_convert("Asia/Ho_Chi_Minh").tz_localize(None)
    return ts


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
    border_color = "rgba(180,170,255,0.16)"
    text_color = "#ffffff"
    delta_color = "#8b90a0"
    glow = "rgba(255,255,255,0.0)"
    bar = "linear-gradient(90deg,#8b7bff,#38e1ff,#ff5ecb)"

    if is_positive is not None:
        up = bool(is_positive)
        text_color = "#2de2a6" if up else "#ff4d7d"
        delta_color = text_color
        border_color = "rgba(45,226,166,0.32)" if up else "rgba(255,77,125,0.32)"
        glow = "rgba(45,226,166,0.5)" if up else "rgba(255,77,125,0.5)"
        bar = "linear-gradient(90deg,#2de2a6,#38e1ff)" if up else "linear-gradient(90deg,#ff4d7d,#ff9a5c)"

    delta_html = ""
    if delta_text:
        if is_positive is None:
            delta_color = "#2de2a6" if ("+" in str(delta_text) or "MUA" in str(delta_text)) else ("#ff4d7d" if ("-" in str(delta_text) or "BÁN" in str(delta_text)) else "#8b90a0")
        delta_html = f"<div class='qm-delta' style='color:{delta_color}'>{delta_text}</div>"

    val_cls, val_attr = "qm-val", ""
    try:
        if raw is not None and not pd.isna(raw):
            val_cls = "qm-val nt-count"
            val_attr = f" data-v='{float(raw)}' data-d='{int(dec)}' data-vn='{1 if vn else 0}'"
    except Exception:
        pass

    safe_val = str(value_str).replace("'", "").replace('"', "")
    _hints = {
        "GIÁ HIỆN TẠI": "Giá đóng cửa của nến mới nhất. Xanh là tăng so với nến trước, đỏ là giảm.",
        "RSI (14)": "Trên 70: quá mua, dễ điều chỉnh. Dưới 30: quá bán, dễ hồi. Quanh 50: trung tính.",
        "ADX (14)": "Đo sức mạnh xu hướng, không đo hướng. Trên 25 là xu hướng mạnh, dưới 20 là đi ngang.",
        "PHIÊN Á 07–15H": "Giờ VN (xấp xỉ). Thanh khoản vừa, hay đi ngang; Vàng và JPY hoạt động nhiều.",
        "PHIÊN ÂU 14–23H": "Giờ VN (xấp xỉ). Biên độ lớn, thường tạo xu hướng trong ngày.",
        "PHIÊN MỸ 20–04H": "Giờ VN (xấp xỉ). Biến động mạnh nhất, nhất là lúc giao phiên với Âu.",
        "ATR (14)": "Biên độ dao động trung bình 14 nến. Dùng để đặt SL/TP theo độ biến động.",
        "GIÁ VÀO LỆNH": "Giá đóng cửa nến mới nhất, dùng làm điểm vào tham chiếu.",
        "CẮT LỖ (SL)": "Vùng thoát lệnh khi thị trường đi sai: ngoài đỉnh/đáy 20 nến, cộng thêm 0,5 ATR.",
        "CHỐT LỜI (TP)": "Mục tiêu lợi nhuận theo tỷ lệ R:R bạn chọn ở thanh trượt.",
    }
    _hint = _hints.get(label, "Chạm lần nữa để lật lại.")
    html(f"""
        <div class='flip'><div class='flip-in'><div class='ff'><div class='qm' style='--bc:{border_color}; --tc:{text_color}; --gl:{glow}; --bar:{bar};'>
            <div class='qm-lbl'>{label}</div>
            <div class='qm-row'>
                <span class='{val_cls}'{val_attr}>{value_str}</span>
                <span class='nt-copy' role='button' tabindex='0' title='Copy' data-copy='{safe_val}'>
                    <svg class='i-copy' width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><rect x='9' y='9' width='13' height='13' rx='2' ry='2'></rect><path d='M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1'></path></svg>
                    <svg class='i-ok' width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4'><polyline points='20 6 9 17 4 12'></polyline></svg>
                </span>
            </div>
            {delta_html}
        </div></div><div class='fb'><b>{label}</b><span>{_hint}</span></div></div></div>
    """)


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
        last_close_time = to_vn_naive(last_closed['close_time'])
        cooldown = timedelta(hours=4) if "Giờ" not in timeframe else timedelta(hours=12)
        if "Ngày" in timeframe or "Tuần" in timeframe: cooldown = timedelta(days=3)
        if pd.notna(last_close_time) and (to_vn_naive(latest['Time']) - last_close_time) < cooldown: return
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
        if getattr(df["Time"].dt, "tz", None) is not None:
            df["Time"] = df["Time"].dt.tz_convert("Asia/Ho_Chi_Minh").dt.tz_localize(None)
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
# 3b. AI ENTRY ENGINE (numpy thuần: logistic regression + triple-barrier + kiểm chứng ngoài mẫu)
# ============================================================
SESSIONS_UTC = {"Á": (0, 8), "Âu": (7, 16), "Mỹ": (13, 21)}  # xấp xỉ, lệch ±1h theo DST. Giờ VN = UTC+7
SESSION_VN = {"Á": "07–15h", "Âu": "14–23h", "Mỹ": "20–04h"}


def contract_value(ticker: str, price: float) -> float:
    """USD lãi/lỗ cho mỗi 1.0 đơn vị giá của 1 lot chuẩn (ước tính, có thể ghi đè)."""
    if ticker == "GC=F": return 100.0
    if ticker == "SI=F": return 5000.0
    if ticker == "CL=F": return 1000.0
    if ticker == "JPY=X": return 100000.0 / max(price, 1e-9)
    if ticker.endswith("=X"): return 100000.0
    return 1.0


def market_state(ticker: str, now_vn):
    """(đang đóng cửa?, danh sách phiên đang mở) tại giờ VN (naive)."""
    utc = now_vn - timedelta(hours=7)
    h, wd = utc.hour + utc.minute / 60, utc.weekday()
    crypto = ticker.endswith("-USD")
    closed = False
    if not crypto:
        if ticker.startswith("^") or ticker.isalpha():
            closed = wd >= 5 or not (13.5 <= h < 21)
        else:
            closed = wd == 5 or (wd == 4 and h >= 22) or (wd == 6 and h < 22)
    sess = [n for n, (a, b) in SESSIONS_UTC.items() if a <= h < b]
    return closed, (sess or ["Ngoài giờ"])


def ai_features(df: pd.DataFrame) -> pd.DataFrame:
    c, atr = df["Close"], df["ATR"].replace(0, np.nan)
    f = pd.DataFrame(index=df.index)
    f["trend"] = (df["EMA20"] - df["EMA50"]) / atr
    f["pos"] = (c - df["EMA20"]) / atr
    f["r1"], f["r5"], f["r20"] = c.diff(1) / atr, c.diff(5) / atr, c.diff(20) / atr
    f["rsi"] = (df["RSI"] - 50) / 50
    f["macd"] = df["MACD_hist"] / atr
    f["adx"] = df["ADX"] / 50
    f["bb"] = (c - df["BB_lower"]) / (df["BB_upper"] - df["BB_lower"]).replace(0, np.nan) - 0.5
    f["vol"] = (atr / c).rolling(100, min_periods=30).rank(pct=True) - 0.5
    f["body"] = (c - df["Open"]) / (df["High"] - df["Low"]).replace(0, np.nan)
    f["dhi"] = (df["High"].rolling(20).max() - c) / atr
    f["dlo"] = (c - df["Low"].rolling(20).min()) / atr
    hr = (df["Time"] - pd.Timedelta(hours=7)).dt.hour
    f["hs"], f["hc"] = np.sin(2 * np.pi * hr / 24), np.cos(2 * np.pi * hr / 24)
    return f.replace([np.inf, -np.inf], np.nan).clip(-6, 6)


def sl_distance(df: pd.DataFrame, side: str, mode: str, k: float) -> pd.Series:
    atr = df["ATR"]
    if mode == "Cấu trúc (swing 10 nến)":
        sw = (df["Close"] - df["Low"].rolling(10).min() if side == "LONG" else df["High"].rolling(10).max() - df["Close"]) + 0.25 * atr
        return sw.clip(lower=0.8 * atr, upper=3.5 * atr)
    return k * atr


def triple_barrier(df: pd.DataFrame, side: str, sld: pd.Series, rr: float, horizon: int) -> np.ndarray:
    """1 nếu chạm TP trước SL trong `horizon` nến (cùng nến = thua, hết hạn = không thắng)."""
    hi, lo, cl, d = df["High"].values, df["Low"].values, df["Close"].values, sld.values
    n, y, big = len(df), np.full(len(df), np.nan), 10 ** 6
    for i in range(n - horizon - 1):
        if not np.isfinite(d[i]) or d[i] <= 0: continue
        h, l = hi[i + 1:i + 1 + horizon], lo[i + 1:i + 1 + horizon]
        if side == "LONG": a, b = l <= cl[i] - d[i], h >= cl[i] + d[i] * rr
        else: a, b = h >= cl[i] + d[i], l <= cl[i] - d[i] * rr
        t_sl, t_tp = (a.argmax() if a.any() else big), (b.argmax() if b.any() else big)
        y[i] = 1.0 if t_tp < t_sl else 0.0
    return y


def wilson_lb(hit: float, n: int, horizon: int, z: float = 1.28) -> float:
    """Cận dưới tin cậy của tỷ lệ thắng; n bị chiết khấu vì các lệnh chồng lấn nhau trong `horizon` nến."""
    ne = max(n / max(horizon / 6.0, 1.0), 1e-9)
    return float((hit + z * z / (2 * ne) - z * np.sqrt(hit * (1 - hit) / ne + z * z / (4 * ne * ne))) / (1 + z * z / ne)) if n else 0.0


def _sig(z): return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_logit(X, y, l2=5.0, iters=400, lr=0.15):
    m = float(np.clip(y.mean(), 0.02, 0.98))
    w, b = np.zeros(X.shape[1]), float(np.log(m / (1 - m)))
    for _ in range(iters):
        g = _sig(X @ w + b) - y
        w -= lr * (X.T @ g / len(y) + l2 * w / len(y))
        b -= lr * g.mean()
    return w, b


@st.cache_data(ttl=120, show_spinner="🤖 AI ĐANG HUẤN LUYỆN & KIỂM CHỨNG...")
def ai_predict(df, rr, k, mode, horizon, thr):
    X, out = ai_features(df).values, {}
    for side in ("LONG", "SHORT"):
        sld = sl_distance(df, side, mode, k)
        y = triple_barrier(df, side, sld, rr, horizon)
        idx = np.where(np.isfinite(X).all(1) & np.isfinite(y))[0]
        if len(idx) < 150:
            out[side] = None
            continue
        cut = int(len(idx) * 0.7)
        tr, te = idx[:max(cut - horizon, 60)], idx[cut:]  # chừa khoảng trống `horizon` nến để không rò rỉ nhãn
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        w, b = fit_logit((X[tr] - mu) / sd, y[tr])
        pt, ye = _sig(((X[te] - mu) / sd) @ w + b), y[te]
        sel = pt >= thr
        n = int(sel.sum())
        mu2, sd2 = X[idx].mean(0), X[idx].std(0) + 1e-9
        w2, b2 = fit_logit((X[idx] - mu2) / sd2, y[idx])
        p = float(_sig(((X[-1] - mu2) / sd2) @ w2 + b2)) if np.isfinite(X[-1]).all() else None
        out[side] = dict(p=p, n=n, hit=float(ye[sel].mean()) if n else 0.0,
                         ev=float((ye[sel] * rr - (1 - ye[sel])).mean()) if n else 0.0,
                         base=float(ye.mean()), ntest=int(len(te)), sld=float(sld.iloc[-1]),
                         lb=wilson_lb(float(ye[sel].mean()) if n else 0.0, n, horizon))
    return out


def ai_decide(res, df, mtf, rr, margin, ticker, now_vn, allow_off, split_tp):
    be, cands = 1 / (1 + rr), {s: r for s, r in res.items() if r and r["p"] is not None}
    if not cands: return None
    thr = be + margin
    side = max(cands, key=lambda s: cands[s]["p"])
    r, last, sgn = cands[side], df.iloc[-1], (1 if side == "LONG" else -1)
    want = "TĂNG" if side == "LONG" else "GIẢM"
    agree = sum(1 for v in mtf.values() if v == want)
    closed, sess = market_state(ticker, now_vn)
    vol = ai_features(df.tail(150))["vol"].iloc[-1]
    sess_ok = allow_off or (not closed and sess != ["Ngoài giờ"])
    gates = [
        (r["p"] >= thr, f"Xác suất thắng ước tính <b>{r['p'] * 100:.1f}%</b> (ngưỡng an toàn ≥ {thr * 100:.1f}%, hòa vốn {be * 100:.1f}%)."),
        (r["n"] >= 8 and r["lb"] > be, f"Kiểm chứng ngoài mẫu: <b>{r['n']}</b> tín hiệu, thắng {r['hit'] * 100:.0f}%, cận dưới tin cậy <b>{r['lb'] * 100:.0f}%</b> (phải > hòa vốn {be * 100:.0f}%, loại bỏ may rủi)."),
        (sess_ok, "Phiên: <b>" + ("THỊ TRƯỜNG ĐÓNG" if closed else "+".join(sess)) + "</b> (tránh vào lệnh ngoài giờ thanh khoản thấp)."),
        (float(last["ADX"]) >= 18, f"ADX <b>{last['ADX']:.1f}</b> (cần ≥ 18 để tránh thị trường nhiễu đi ngang)."),
        (agree >= 2, f"Đồng thuận đa khung: <b>{agree}/3</b> khung cùng {want}."),
        (bool(vol == vol and vol <= 0.45), "Biến động không nằm trong nhóm 5% cao bất thường."),
    ]
    entry, sld = float(last["Close"]), r["sld"]
    ok = all(g[0] for g in gates)
    return dict(side=side, ok=ok, p=r["p"], thr=thr, be=be, ev_exp=r["p"] * rr - (1 - r["p"]), gates=gates, r=r,
                grade=("A" if ok and r["p"] >= thr + 0.07 else "B") if ok else "—",
                entry=entry, sl=entry - sgn * sld, tp1=entry + sgn * sld, tp2=entry + sgn * sld * rr, sld=sld, atr=float(last["ATR"]))


@st.cache_data(ttl=3, show_spinner=False)
def live_price(ticker: str):
    try:
        fi = yf.Ticker(ticker).fast_info
        return float(fi["last_price"]), float(fi["previous_close"])
    except Exception:
        try:
            d = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            return float(d["Close"].iloc[-1]), float(d["Open"].iloc[0])
        except Exception:
            return None


@st.fragment(run_every="5s")
def live_monitor(ticker, plan, lot, cv, atr):
    lp = live_price(ticker)
    if lp is None:
        st.caption("⚠️ Chưa lấy được giá trực tiếp, đang thử lại...")
        return
    price, prev = lp
    now = pd.Timestamp.utcnow().tz_localize(None) + timedelta(hours=7)
    chg = (price - prev) / prev * 100 if prev else 0.0
    closed, sess = market_state(ticker, now)
    col = "#22d3a0" if chg >= 0 else "#ff5470"
    state = "THỊ TRƯỜNG ĐÓNG" if closed else "PHIÊN " + "+".join(sess).upper()
    extra = ""
    if plan:
        sgn = 1 if plan["side"] == "LONG" else -1
        pnl, dist = (price - plan["entry"]) * sgn * lot * cv, (price - plan["entry"]) * sgn / max(atr, 1e-9)
        if sgn * (price - plan["sl"]) <= 0: msg, mc = "⛔ GIÁ ĐÃ CHẠM SL, kế hoạch hết hiệu lực", "#ff5470"
        elif sgn * (price - plan["tp2"]) >= 0: msg, mc = "🎯 GIÁ ĐÃ ĐẠT TP", "#22d3a0"
        elif dist > 0.5: msg, mc = "⚠️ GIÁ ĐÃ CHẠY XA ENTRY, KHÔNG ĐUỔI, chờ hồi về vùng vào lệnh", "#fbbf24"
        elif dist < -0.5: msg, mc = "🟠 Giá đang đi ngược hướng, chờ xác nhận lại", "#fbbf24"
        else: msg, mc = "✅ Giá trong vùng vào lệnh", "#22d3a0"
        extra = (f"<div class='row-item' style='margin-top:10px'><span style='color:{mc};font-weight:700'>{msg}</span>"
                 f"<span class='val-data' style='color:{'#22d3a0' if pnl >= 0 else '#ff5470'}'>{pnl:+,.2f}$ ({lot:.2f} lot)</span></div>")
    html(f"""
        <div class='glass-card' style='padding:12px 18px; margin-bottom:12px'>
            <div class='row-item'><span><b style='color:#ff5470'>● LIVE</b> &nbsp;<b style='color:#fff;font-size:20px'>{format_vn_price(price)}</b>
            &nbsp;<span style='color:{col}'>{chg:+.2f}%</span></span>
            <span style='color:#9a9ab5;font-size:12px'>{state} • {now:%H:%M:%S} (giờ VN)</span></div>{extra}
        </div>
    """)


@st.cache_data(ttl=900, show_spinner=False)
def session_stats(ticker: str):
    d = load_data(ticker, "60m")
    if d is None or len(d) < 48: return None
    hr = (d["Time"] - pd.Timedelta(hours=7)).dt.hour
    rng = (d["High"] - d["Low"]) / d["Close"] * 100
    return {n: float(rng[(hr >= a) & (hr < b)].mean()) for n, (a, b) in SESSIONS_UTC.items()}


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
    if st.button("🔄 Cập nhật dữ liệu", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    html(f"""
        <div class='pro-card'>
            <h4>Nghia_Trading Pro</h4>
            <p>Mở khóa tính năng Bot AI và dữ liệu Realtime.</p>
        </div>
        <div class='copyright'>© {datetime.now().year} Nghia_Trading.<br>All rights reserved.</div>
    """)

    if not st.session_state.get("_fx_loaded"):
        st.session_state["_fx_loaded"] = True
        inject_js(FX_JS + "\n" + FX_JS2)

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
            <div class='orbit'><i></i><i></i><i></i></div>
            <div class='hero-top'>
                <div>
                    <div class='hero-name'>{selected_asset.split(' - ')[1]}</div>
                    <div class='hero-sub'>{ticker} • {timeframe}<span class='hint'>✦ kéo để xoay</span></div>
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
    ["📊 Biểu đồ", "🎯 Kế hoạch giao dịch", "🤖 AI Vào lệnh", "🧠 Phân tích SMC", "🌐 Đa Khung Thời Gian", "📏 Fibonacci", "📰 Tin tức", "📓 Nhật ký"],
    horizontal=True, label_visibility="collapsed"
)
html("<div style='height:14px'></div>")
if menu_selection != "🤖 AI Vào lệnh":
    live_monitor(ticker, None, 0.0, 1.0, float(df["ATR"].iloc[-1]))

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

    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["EMA20"], name="EMA 20", line=dict(color="#38e1ff", width=2, shape="spline", smoothing=0.6)), row=1, col=1)
    fig.add_trace(go.Scatter(x=chart_df["Time"], y=chart_df["EMA50"], name="EMA 50", line=dict(color="#ff5ecb", width=1.5, dash='dot', shape="spline", smoothing=0.6)), row=1, col=1)

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

    st.plotly_chart(fig, width="stretch", config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})
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
        display_df['open_time'] = pd.to_datetime(display_df['open_time'].apply(to_vn_naive)).dt.strftime('%d/%m/%Y %H:%M')
        display_df['close_time'] = pd.to_datetime(display_df['close_time'].apply(to_vn_naive)).dt.strftime('%d/%m/%Y %H:%M').fillna('-')
        display_df['direction'] = display_df['direction'].replace({'LONG': 'MUA', 'SHORT': 'BÁN'})
        display_df['status'] = display_df['status'].replace({'WIN': 'THẮNG', 'LOSS': 'THUA', 'CUT_EARLY': 'CẮT SỚM', 'ACTIVE': 'ĐANG MỞ'})
        for col in ['entry_price', 'exit_price', 'sl', 'tp']:
            display_df[col] = display_df[col].apply(lambda x: format_vn_price(x) if pd.notna(x) else '-')

        def color_bot_status(val):
            if val == 'THẮNG': return 'color: #22d3a0; font-weight: bold;'
            if val == 'THUA': return 'color: #ff5470; font-weight: bold;'
            if val == 'CẮT SỚM': return 'color: #8b90a0; font-weight: bold;'
            return ''

        st.dataframe(display_df[['open_time', 'close_time', 'direction', 'entry_price', 'exit_price', 'sl', 'tp', 'status', 'reason']].style.map(color_bot_status, subset=['status']), hide_index=True, width="stretch")

# ------------------------------------------------------------
# KHU VỰC 3: PHÂN TÍCH SMC
# ------------------------------------------------------------
elif menu_selection == "🤖 AI Vào lệnh":
    st.subheader("AI Vào lệnh: chọn lọc, có kiểm chứng, an toàn vốn")
    col_l, col_r = st.columns([1.5, 1], gap="large")
    with col_r:
        html("<div class='side-label'>Tùy biến SL / TP</div>")
        sl_mode = st.selectbox("Kiểu SL", ["ATR (theo biến động)", "Cấu trúc (swing 10 nến)"], key="ai_slm")
        k_sl = st.slider("Hệ số ATR cho SL", 0.8, 3.0, 1.5, 0.1, key="ai_k", disabled=sl_mode.startswith("Cấu trúc"))
        rr_ai = st.slider("Tỷ lệ R:R (TP)", 1.0, 4.0, 2.0, 0.5, key="ai_rr")
        split_tp = st.toggle("Chia 2 mục tiêu (TP1 = 1R, dời SL về hòa vốn)", value=True, key="ai_split")
        safety = st.select_slider("Mức an toàn", ["Mạo hiểm", "Cân bằng", "Thận trọng"], value="Cân bằng", key="ai_safe")
        allow_off = st.toggle("Cho phép vào lệnh ngoài giờ / đóng cửa", value=False, key="ai_off")
        html("<div class='side-label' style='margin-top:10px'>Vốn & Lot</div>")
        bal_ai = st.number_input("Số dư ($)", value=1000.0, step=100.0, key="ai_bal")
        risk_ai = st.number_input("Rủi ro mỗi lệnh (%)", value=1.0, min_value=0.1, max_value=3.0, step=0.1, key="ai_risk")
        lev_ai = st.number_input("Đòn bẩy tài khoản (1:x)", value=100, min_value=1, step=10, key="ai_lev")
        lot_step = st.selectbox("Bước lot", [0.01, 0.1, 1.0], key="ai_step")
        cv_auto = contract_value(ticker, float(last_close))
        cv = st.number_input("USD / 1.0 giá / 1 lot (ghi đè nếu broker khác)", value=float(round(cv_auto, 4)), key=f"ai_cv_{ticker}")

    iv_h = {"1m": 48, "5m": 48, "15m": 48, "60m": 24, "1d": 10, "1wk": 6}[interval]
    margin = {"Mạo hiểm": 0.02, "Cân bằng": 0.05, "Thận trọng": 0.08}[safety]
    dfa = df.iloc[:-1].reset_index(drop=True)  # chỉ dùng nến đã đóng
    res = ai_predict(dfa, rr_ai, k_sl, sl_mode, iv_h, 1 / (1 + rr_ai) + margin)
    mtf_ai = load_mtf_data(ticker)
    now_vn = pd.Timestamp.utcnow().tz_localize(None) + timedelta(hours=7)
    dec = ai_decide(res, dfa, mtf_ai, rr_ai, margin, ticker, now_vn, allow_off, split_tp)

    with col_l:
        if dec is None:
            st.warning("Chưa đủ dữ liệu lịch sử để huấn luyện (cần ≥ 150 mẫu hợp lệ). Hãy chọn khung thời gian nhỏ hơn.")
        else:
            side_vn = "MUA (LONG)" if dec["side"] == "LONG" else "BÁN (SHORT)"
            accent = ("#22d3a0" if dec["side"] == "LONG" else "#ff5470") if dec["ok"] else "#fbbf24"
            title = f"Tín hiệu: {side_vn}" if dec["ok"] else f"ĐỨNG NGOÀI (nghiêng về {side_vn})"
            off_ = 264 * (1 - min(dec["p"], 1.0))
            reasons = "".join(f"<div class='reason-line' style='animation-delay:{0.1 + i * 0.07:.2f}s'>{'🟢' if ok else '⛔'} {t}</div>" for i, (ok, t) in enumerate(dec["gates"]))
            html(f"""
                <div class='signal-card' style='--accent: {accent};'>
                    <div class='sig-head'>
                        <div class='ring'><svg viewBox='0 0 100 100'>
                            <defs><linearGradient id='rg2' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='#7c7cff'/><stop offset='100%' stop-color='#22d3a0'/></linearGradient></defs>
                            <circle cx='50' cy='50' r='42' class='ring-bg'/><circle cx='50' cy='50' r='42' class='ring-fg' stroke='url(#rg2)' style='--off:{off_:.1f}'/></svg>
                            <div class='ring-num'><span class='nt-count' data-v='{dec["p"] * 100:.1f}' data-d='1'>{dec["p"] * 100:.1f}</span><small>%</small></div></div>
                        <div class='sig-info'><div class='sig-kicker'>XÁC SUẤT THẮNG (AI)</div>
                            <h3 style='color: {accent} !important;'>{title}</h3>
                            <div class='score-badge'>{'HẠNG ' + dec['grade'] if dec['ok'] else 'CHƯA ĐỦ ĐIỀU KIỆN AN TOÀN'}</div></div>
                    </div>{reasons}
                </div>
            """)
            lot_raw = (bal_ai * risk_ai / 100) / max(dec["sld"] * cv, 1e-12)
            lot = max(np.floor(lot_raw / lot_step) * lot_step, lot_step)
            real_risk = lot * dec["sld"] * cv
            c1, c2, c3 = st.columns(3)
            with c1: quantum_metric("GIÁ VÀO LỆNH", format_vn_price(dec["entry"]), "NẾN ĐÃ ĐÓNG", is_positive=None, raw=dec["entry"])
            with c2: quantum_metric("CẮT LỖ (SL)", format_vn_price(dec["sl"]), f"-{real_risk:,.2f}$", is_positive=False, raw=dec["sl"])
            with c3: quantum_metric("CHỐT LỜI (TP)", format_vn_price(dec["tp2"]), f"+{real_risk * rr_ai:,.2f}$", is_positive=True, raw=dec["tp2"])
            if split_tp:
                html(f"<div class='math-box'><b style='color:#fff;'>Kế hoạch 2 mục tiêu:</b> chốt 50% tại TP1 <b style='color:#22d3a0'>{format_vn_price(dec['tp1'])}</b> (1R), dời SL về giá vào lệnh, phần còn lại chạy tới TP <b style='color:#22d3a0'>{format_vn_price(dec['tp2'])}</b>.</div>")
            warn = "" if lot_raw >= lot_step else "<div class='row-item'><span style='color:#fbbf24'>⚠️ SL quá xa so với vốn: lot tối thiểu đã vượt mức rủi ro bạn đặt.</span></div>"
            notional = lot * cv * dec["entry"]
            html(f"""
                <div class='glass-card'>
                    <div class='card-title'>🧮 Khối lượng (Lot) & Rủi ro</div>
                    <div class='row-item'><span>Tiền rủi ro mục tiêu:</span><span class='val-data'>${bal_ai * risk_ai / 100:,.2f}</span></div>
                    <div class='row-item'><span>Khoảng cách SL:</span><span class='val-data'>{format_vn_price(dec['sld'])}</span></div>
                    <div class='row-item' style='margin-top:12px;padding-top:12px;border-top:1px dashed rgba(255,255,255,0.1);'><span style='color:#fff;font-weight:700'>Lot đề xuất:</span><span class='val-data val-up' style='font-size:22px'>{lot:.2f}</span></div>
                    <div class='row-item'><span>Rủi ro thực tế sau làm tròn:</span><span class='val-data val-down'>${real_risk:,.2f} ({real_risk / max(bal_ai, 1e-9) * 100:.2f}%)</span></div>
                    <div class='row-item'><span>Giá trị vị thế / Ký quỹ ước tính (1:{lev_ai}):</span><span class='val-data'>${notional:,.0f} / ${notional / lev_ai:,.2f}</span></div>{warn}
                </div>
            """)
            r = dec["r"]
            html(f"""
                <div class='glass-card'>
                    <div class='card-title'>🔬 Kiểm chứng ngoài mẫu (30% dữ liệu mới nhất, mô hình chưa từng thấy)</div>
                    <div class='row-item'><span>Tỷ lệ thắng nền (mọi nến):</span><span class='val-data'>{r['base'] * 100:.1f}%</span></div>
                    <div class='row-item'><span>Khi AI chọn vào lệnh:</span><span class='val-data val-up'>{r['hit'] * 100:.1f}% ({r['n']} / {r['ntest']} nến)</span></div>
                    <div class='row-item'><span>Kỳ vọng lịch sử / lệnh:</span><span class='val-data' style='color:{"#22d3a0" if r["ev"] > 0 else "#ff5470"}'>{r['ev']:+.2f}R</span></div>
                </div>
            """)
            html("<div class='math-box'><b style='color:#fff;'>Lưu ý trung thực:</b> đây là xác suất ước lượng từ lịch sử, không phải lời đảm bảo. Không mô hình nào thắng chắc. Lợi thế đến từ việc <b>chỉ vào lệnh khi nhiều điều kiện cùng đúng</b>, SL đặt theo biến động và rủi ro cố định mỗi lệnh. Tránh vào lệnh quanh giờ công bố tin lớn.</div>")

    st_s = session_stats(ticker)
    html("<div style='height:6px'></div>")
    s1, s2, s3 = st.columns(3)
    _cl, _se = market_state(ticker, now_vn)
    for cc, nm in zip((s1, s2, s3), ("Á", "Âu", "Mỹ")):
        with cc:
            quantum_metric(f"PHIÊN {nm} {SESSION_VN[nm]}".upper(), f"{st_s[nm]:.2f}%" if st_s else "N/A", "ĐANG MỞ" if (nm in _se and not _cl) else "ĐÓNG", is_positive=(nm in _se and not _cl) or None)
    st.caption("Biên độ trung bình mỗi nến 1 giờ theo phiên (giờ VN, xấp xỉ, lệch ±1h khi đổi giờ mùa hè).")

    if dec is not None:
        plan = dict(side=dec["side"], entry=dec["entry"], sl=dec["sl"], tp2=dec["tp2"])
        live_monitor(ticker, plan if dec["ok"] else None, float(lot), float(cv), float(dec["atr"]))

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
        _back = {"TĂNG": "EMA20 nằm trên EMA50, xu hướng tăng. Ưu tiên tìm điểm MUA khi các khung cùng đồng thuận.",
                 "GIẢM": "EMA20 nằm dưới EMA50, xu hướng giảm. Ưu tiên tìm điểm BÁN khi các khung cùng đồng thuận."}.get(trend_val, "Chưa đủ dữ liệu (cần hơn 50 nến) để xác định xu hướng.")
        with col:
            html(f"""
                <div class='flip'><div class='flip-in'><div class='ff'><div class='glass-card mtf-card' style='border-top: 3px solid {color};'>
                    <div style='color: #8b90a0; font-size: 12px; font-weight: 700; letter-spacing: 1.2px;'>{tf_name}</div>
                    <div class='mtf-icon'>{icon}</div>
                    <div style='color: {color}; font-size: 21px; font-weight: 800;'>{trend_val}</div>
                </div></div><div class='fb'><b>{tf_name}</b><span>{_back}</span></div></div></div>
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
            <a class='glass-card news-card' href='{safe_link}' target='_blank' rel='noopener noreferrer'>
                <div class='news-title'>{item['title']}</div>
                <div style='color: #8b90a0; font-size: 12px; display: flex; align-items: center; gap: 6px;'>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    {item['published']}
                </div>
            </a>
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
            if st.form_submit_button("Lưu dữ liệu", width="stretch"):
                add_trade(str(trade_date), asset_name.upper(), direction, result, reason, pnl_val)
                st.rerun()

        journal_df = get_trades()
        if not journal_df.empty:
            csv = journal_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Xuất file CSV", data=csv, file_name="nhat_ky.csv", mime="text/csv", width="stretch")

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

                st.dataframe(filtered_df[['date', 'asset', 'direction', 'result', 'pnl', 'reason']].style.map(color_result, subset=['result']).map(color_pnl, subset=['pnl']), hide_index=True, width="stretch")
