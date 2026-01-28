"""
Trading System Dashboard - Clean UI
깔끔하고 미니멀한 상용 서비스 UI

실행: streamlit run dashboard/app.py
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# === 페이지 설정 ===
st.set_page_config(
    page_title="StockLens | 스마트 스크리너",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === 다크모드 금융 터미널 디자인 시스템 ===
# TradingView / Bloomberg Terminal 스타일
CLEAN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    /* 다크 Slate 팔레트 */
    --bg-primary: #0f172a;      /* 메인 배경 */
    --bg-secondary: #1e293b;    /* 카드/섹션 배경 */
    --bg-tertiary: #334155;     /* 호버/액티브 */
    --bg-elevated: #1e293b;     /* 떠있는 요소 */

    --border: #334155;          /* 테두리 (최소화) */
    --border-light: #475569;    /* 밝은 테두리 */

    /* 텍스트 */
    --text-primary: #f1f5f9;    /* 주요 텍스트 */
    --text-secondary: #94a3b8;  /* 보조 텍스트 */
    --text-muted: #64748b;      /* 흐린 텍스트 */
    --text-dim: #475569;        /* 매우 흐린 */

    /* 금융 컬러 - 네온/글로우 효과 */
    --bull: #34d399;            /* 밝은 에메랄드 */
    --bull-dim: #10b981;
    --bull-bg: rgba(52, 211, 153, 0.1);
    --bull-glow: rgba(52, 211, 153, 0.2);

    --bear: #fb7185;            /* 밝은 로즈 */
    --bear-dim: #f43f5e;
    --bear-bg: rgba(251, 113, 133, 0.1);
    --bear-glow: rgba(251, 113, 133, 0.2);

    --warning: #fbbf24;         /* 앰버 */
    --warning-bg: rgba(251, 191, 36, 0.1);

    --info: #60a5fa;            /* 블루 */
    --info-bg: rgba(96, 165, 250, 0.1);

    /* 프라이머리 - 시안/블루 */
    --primary: #38bdf8;
    --primary-dim: #0ea5e9;
    --primary-bg: rgba(56, 189, 248, 0.1);

    /* 폰트 */
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
}

/* === 기본 설정 === */
* { font-family: var(--font-sans); }

.stApp {
    background: var(--bg-primary) !important;
}

.main .block-container {
    padding: 1rem 1.5rem;
    max-width: 1600px;
}

/* === 타이포그래피 === */
h1 {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.025em;
}
h2 {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}
h3, h4, h5 {
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
}
p, span, div, label {
    font-size: 0.8125rem;
    color: var(--text-secondary);
}

/* === 사이드바 === */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div { padding-top: 1rem; }
[data-testid="stSidebar"] * { color: var(--text-secondary); }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--text-primary) !important; }

/* === 버튼 === */
.stButton > button {
    background: var(--primary) !important;
    color: #ffffff !important;  /* 흰색 텍스트 */
    border: none !important;
    border-radius: 6px !important;
    padding: 0.5rem 1rem !important;
    font-size: 0.8125rem !important;
    font-weight: 600 !important;
    min-height: 36px !important;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: var(--primary-dim) !important;
    box-shadow: 0 0 20px var(--primary-bg);
    color: #ffffff !important;
}
.stButton > button[kind="secondary"] {
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
}
/* 버튼 내부 span/p 태그도 흰색으로 */
.stButton > button span,
.stButton > button p {
    color: #ffffff !important;
}

/* === 입력 필드 === */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-size: 0.8125rem !important;
    color: var(--text-primary) !important;
}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 2px var(--primary-bg) !important;
}
.stTextInput > div > div > input::placeholder {
    color: var(--text-muted) !important;
}

/* 셀렉트박스 드롭다운 */
[data-baseweb="popover"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
}
[data-baseweb="menu"] {
    background: var(--bg-secondary) !important;
}
[data-baseweb="menu"] li {
    color: var(--text-secondary) !important;
}
[data-baseweb="menu"] li:hover {
    background: var(--bg-tertiary) !important;
}

/* 멀티셀렉트 - 선택된 태그 스타일 */
.stMultiSelect [data-baseweb="tag"] {
    background: var(--bg-tertiary) !important;
    border: none !important;
    border-radius: 4px !important;
}
.stMultiSelect [data-baseweb="tag"] span {
    color: var(--text-primary) !important;
}
.stMultiSelect [data-baseweb="tag"] svg {
    fill: var(--text-muted) !important;
}
.stMultiSelect [data-baseweb="tag"]:hover {
    background: var(--border-light) !important;
}
/* 멀티셀렉트 입력 */
.stMultiSelect input {
    background: transparent !important;
    color: var(--text-primary) !important;
}
.stMultiSelect input::placeholder {
    color: var(--text-muted) !important;
}

/* === 탭 === */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--border) !important;
    background: transparent !important;
    padding: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 0 !important;
    color: var(--text-muted);
    font-size: 0.8125rem;
    font-weight: 500;
    padding: 0.75rem 1rem;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-secondary);
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: var(--primary) !important;
    border-bottom: 2px solid var(--primary) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* === 카드 (테두리 최소화, 밝기로 구분) === */
.card {
    background: var(--bg-secondary);
    border: none;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
}
.card-title {
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
}
.card-desc {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    line-height: 1.5;
}
.card-meta {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.5rem;
}

/* 전략 카드 */
.strategy-card {
    background: var(--bg-secondary);
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0.875rem;
    margin-bottom: 0.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    transition: all 0.15s ease;
}
.strategy-card:hover {
    border-color: var(--border);
    background: var(--bg-tertiary);
}
.strategy-info { flex: 1; }
.strategy-name {
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
    font-size: 0.875rem;
}
.strategy-desc {
    font-size: 0.75rem;
    color: var(--text-secondary);
    line-height: 1.4;
}
.strategy-meta {
    font-size: 0.6875rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
}
.strategy-btn { flex-shrink: 0; }

/* === 금융 데이터 스타일 === */

/* 숫자 - 모노스페이스 */
.num, .price, .pct, .score-value {
    font-family: var(--font-mono) !important;
    font-weight: 500;
    letter-spacing: -0.02em;
}

/* 가격/퍼센트 컬러 코딩 - 글로우 효과 */
.bull, .up, .positive, .long {
    color: var(--bull) !important;
    text-shadow: 0 0 10px var(--bull-glow);
}
.bear, .down, .negative, .short {
    color: var(--bear) !important;
    text-shadow: 0 0 10px var(--bear-glow);
}
.neutral { color: var(--text-secondary) !important; }

/* 메트릭 박스 */
.metric-box {
    background: var(--bg-secondary);
    border: none;
    border-radius: 8px;
    padding: 0.75rem;
    text-align: center;
}
.metric-value {
    font-family: var(--font-mono);
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
}
.metric-label {
    font-size: 0.6875rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* 점수 뱃지 - 다크모드 */
.score-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.5rem;
    height: 1.5rem;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
}
.score-s { background: var(--bull-bg); color: var(--bull); }
.score-a { background: var(--info-bg); color: var(--info); }
.score-b { background: var(--warning-bg); color: var(--warning); }
.score-c { background: var(--bg-tertiary); color: var(--text-muted); }

/* 점수 원형 */
.score-circle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 0.875rem;
}
.score-high { background: var(--bull-bg); color: var(--bull); }
.score-mid { background: var(--warning-bg); color: var(--warning); }
.score-low { background: var(--bear-bg); color: var(--bear); }

/* 시장 상태 박스 */
.market-box {
    background: var(--bg-secondary);
    border: none;
    border-radius: 8px;
    padding: 0.875rem;
    margin-bottom: 0.75rem;
}
.market-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}
.market-title {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 0.875rem;
}
.market-detail {
    font-size: 0.75rem;
    color: var(--text-secondary);
    line-height: 1.5;
}
.market-indicator {
    display: flex;
    justify-content: space-between;
    padding: 0.375rem 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.75rem;
    color: var(--text-secondary);
}
.market-indicator:last-child { border-bottom: none; }

/* 탑 카드 */
.top-card {
    background: var(--bg-secondary);
    border: none;
    border-radius: 8px;
    padding: 0.875rem;
    text-align: center;
    transition: background 0.15s ease;
}
.top-card:hover {
    background: var(--bg-tertiary);
}
.top-rank { font-size: 1.25rem; margin-bottom: 0.375rem; }
.top-ticker {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 0.9375rem;
    color: var(--text-primary);
}
.top-name {
    font-size: 0.6875rem;
    color: var(--text-muted);
    margin-bottom: 0.375rem;
}

/* 텍스트 유틸리티 */
.text-sm { font-size: 0.75rem; color: var(--text-secondary); }
.text-xs { font-size: 0.6875rem; color: var(--text-muted); }
.text-mono { font-family: var(--font-mono); }
.text-glow-bull { color: var(--bull); text-shadow: 0 0 10px var(--bull-glow); }
.text-glow-bear { color: var(--bear); text-shadow: 0 0 10px var(--bear-glow); }

/* 로고 */
.logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0 1rem 0;
}
.logo-icon { font-size: 1.25rem; }
.logo-text {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.025em;
}

/* 태그/뱃지 */
.tag {
    display: inline-flex;
    align-items: center;
    padding: 0.125rem 0.5rem;
    border-radius: 4px;
    font-size: 0.6875rem;
    font-weight: 500;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    margin-right: 0.25rem;
}
.tag-bull { background: var(--bull-bg); color: var(--bull); }
.tag-bear { background: var(--bear-bg); color: var(--bear); }
.tag-info { background: var(--info-bg); color: var(--info); }

/* 섹션 타이틀 */
.section-title {
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* === 테이블 스타일 (금융 데이터) === */
.stDataFrame {
    font-size: 0.75rem !important;
}
.stDataFrame td, .stDataFrame th {
    font-size: 0.75rem !important;
    padding: 0.5rem 0.75rem !important;
    background: var(--bg-secondary) !important;
    color: var(--text-secondary) !important;
    border-color: var(--border) !important;
}
.stDataFrame th {
    background: var(--bg-tertiary) !important;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.6875rem !important;
}
.stDataFrame tbody tr:hover td {
    background: var(--bg-tertiary) !important;
}

/* 시그널 상태 뱃지 - 글로우 효과 */
.signal-go {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.5rem;
    background: var(--bull-bg);
    color: var(--bull);
    border-radius: 4px;
    font-size: 0.6875rem;
    font-weight: 600;
    box-shadow: 0 0 8px var(--bull-glow);
}
.signal-wait {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.5rem;
    background: var(--warning-bg);
    color: var(--warning);
    border-radius: 4px;
    font-size: 0.6875rem;
    font-weight: 600;
}

/* 방향 뱃지 - 글로우 */
.dir-long {
    color: var(--bull);
    font-weight: 600;
    text-shadow: 0 0 8px var(--bull-glow);
}
.dir-short {
    color: var(--bear);
    font-weight: 600;
    text-shadow: 0 0 8px var(--bear-glow);
}

/* Streamlit 기본 요소 숨김 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Expander 스타일 - 다크 */
.streamlit-expanderHeader {
    font-size: 0.8125rem !important;
    background: var(--bg-secondary) !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
}
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    background: var(--bg-secondary) !important;
}
[data-testid="stExpander"] details {
    background: var(--bg-secondary) !important;
}

/* 필터 행 정렬 */
div[data-testid="stExpander"] div[data-testid="stHorizontalBlock"] {
    align-items: center !important;
    gap: 0.5rem !important;
    margin-bottom: 0.25rem !important;
}

/* 입력 필드 스타일 */
div[data-testid="stExpander"] .stTextInput > div { margin-bottom: 0 !important; }
div[data-testid="stExpander"] .stTextInput input {
    padding: 0.375rem 0.5rem !important;
    font-size: 0.8125rem !important;
    text-align: right !important;
    font-family: var(--font-mono) !important;
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
div[data-testid="stExpander"] .stTextInput input:disabled {
    background: var(--bg-primary) !important;
    color: var(--text-muted) !important;
}

/* 체크박스 - 다크 */
div[data-testid="stExpander"] .stCheckbox { margin-bottom: 0 !important; }
div[data-testid="stExpander"] .stCheckbox > label {
    padding: 0 !important;
    font-size: 0.8125rem !important;
    color: var(--text-secondary) !important;
}
.stCheckbox label span { color: var(--text-secondary) !important; }

/* 토글 */
div[data-testid="stExpander"] div[data-testid="stToggle"] > label { margin-bottom: 0 !important; }

/* expander 간격 */
div[data-testid="stExpander"] > details > div[data-testid="stExpanderDetails"] {
    padding: 0.5rem 0.75rem !important;
    background: var(--bg-secondary) !important;
}
div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] { gap: 0.125rem !important; }

/* 툴팁 스타일 */
.tooltip-container {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}
.tooltip-trigger {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--bg-tertiary);
    color: var(--text-muted);
    font-size: 9px;
    font-weight: 600;
    cursor: help;
    position: relative;
    transition: all 0.15s ease;
}
.tooltip-trigger:hover {
    background: var(--primary);
    color: var(--bg-primary);
}
.tooltip-trigger:hover .tooltip-content {
    visibility: visible;
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}
.tooltip-content {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%) translateY(-5px);
    width: 260px;
    padding: 0.625rem 0.75rem;
    background: var(--bg-elevated);
    color: var(--text-primary);
    font-size: 0.6875rem;
    font-weight: 400;
    line-height: 1.5;
    border-radius: 6px;
    border: 1px solid var(--border);
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    z-index: 1000;
    transition: all 0.15s ease;
}
.tooltip-content::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 5px solid transparent;
    border-top-color: var(--bg-elevated);
}
.tooltip-title {
    font-weight: 600;
    margin-bottom: 0.25rem;
    color: #93c5fd;
    font-size: 0.75rem;
}
.tooltip-example {
    margin-top: 0.375rem;
    padding-top: 0.375rem;
    border-top: 1px solid var(--border);
    font-size: 0.625rem;
    color: var(--text-muted);
}

/* === 추가 금융 유틸리티 === */

/* 가격 표시 */
.price-display {
    font-family: var(--font-mono);
    font-weight: 500;
    color: var(--text-primary);
}

/* 변동률 - 글로우 */
.change-positive {
    color: var(--bull);
    font-family: var(--font-mono);
    text-shadow: 0 0 8px var(--bull-glow);
}
.change-positive::before { content: '+'; }
.change-negative {
    color: var(--bear);
    font-family: var(--font-mono);
    text-shadow: 0 0 8px var(--bear-glow);
}

/* 미니 차트 영역 */
.mini-chart {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: 0.5rem;
}

/* 데이터 그리드 */
.data-grid {
    display: grid;
    gap: 0.5rem;
}
.data-grid-2 { grid-template-columns: repeat(2, 1fr); }
.data-grid-3 { grid-template-columns: repeat(3, 1fr); }
.data-grid-4 { grid-template-columns: repeat(4, 1fr); }
.data-grid-6 { grid-template-columns: repeat(6, 1fr); }

/* 데이터 셀 */
.data-cell {
    background: var(--bg-secondary);
    border: none;
    border-radius: 6px;
    padding: 0.625rem;
}
.data-cell-label {
    font-size: 0.625rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.25rem;
}
.data-cell-value {
    font-family: var(--font-mono);
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
}

/* 시그널 리스트 아이템 */
.signal-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.625rem 0.75rem;
    background: var(--bg-secondary);
    border: 1px solid transparent;
    border-radius: 6px;
    margin-bottom: 0.375rem;
    cursor: pointer;
    transition: all 0.15s ease;
}
.signal-item:hover {
    border-color: var(--primary);
    background: var(--bg-tertiary);
    box-shadow: 0 0 12px var(--primary-bg);
}
.signal-item-active {
    border-color: var(--primary);
    background: var(--primary-bg);
}
.signal-ticker {
    font-family: var(--font-mono);
    font-weight: 600;
    color: var(--text-primary);
    font-size: 0.875rem;
}
.signal-score {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 0.8125rem;
}

/* === Streamlit 기본 컴포넌트 다크 오버라이드 === */

/* 메트릭 */
[data-testid="stMetric"] {
    background: var(--bg-secondary) !important;
    padding: 0.75rem !important;
    border-radius: 8px !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-muted) !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-family: var(--font-mono) !important;
}
[data-testid="stMetricDelta"] {
    font-family: var(--font-mono) !important;
}
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stMetricDelta"][data-testid-delta-type="positive"] {
    color: var(--bull) !important;
}
[data-testid="stMetricDelta"][data-testid-delta-type="negative"] {
    color: var(--bear) !important;
}

/* 슬라이더 - 완전 다크 스타일 */
.stSlider {
    padding-top: 0.5rem !important;
}
.stSlider > div > div > div {
    background: var(--bg-tertiary) !important;
}
.stSlider [data-baseweb="slider"] {
    background: transparent !important;
}
.stSlider [data-baseweb="slider"] > div {
    background: var(--bg-tertiary) !important;
    height: 6px !important;
    border-radius: 3px !important;
}
.stSlider [data-baseweb="slider"] > div > div {
    background: var(--primary) !important;
    height: 6px !important;
    border-radius: 3px !important;
}
/* 슬라이더 thumb */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--primary) !important;
    border: 2px solid var(--bg-primary) !important;
    box-shadow: 0 0 8px var(--primary-bg) !important;
    width: 16px !important;
    height: 16px !important;
}
.stSlider [data-baseweb="slider"] [role="slider"]:focus {
    box-shadow: 0 0 12px var(--primary) !important;
}
/* 슬라이더 라벨 */
.stSlider label {
    color: var(--text-secondary) !important;
}
.stSlider [data-testid="stTickBarMin"],
.stSlider [data-testid="stTickBarMax"] {
    color: var(--text-muted) !important;
    font-family: var(--font-mono) !important;
}

/* 라디오 버튼 */
.stRadio > label {
    color: var(--text-secondary) !important;
}
.stRadio [data-baseweb="radio"] {
    background: var(--bg-secondary) !important;
    border-color: var(--border) !important;
}
.stRadio [data-baseweb="radio"]:hover {
    border-color: var(--primary) !important;
}

/* 프로그레스 바 */
.stProgress > div > div {
    background: var(--bg-tertiary) !important;
}
.stProgress > div > div > div {
    background: var(--primary) !important;
}

/* 스피너 */
.stSpinner > div {
    border-color: var(--primary) transparent transparent transparent !important;
}

/* 경고/정보 박스 */
.stAlert {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-secondary) !important;
}

/* 구분선 */
hr {
    border-color: var(--border) !important;
}

/* 스크롤바 - 다크 */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: var(--bg-primary);
}
::-webkit-scrollbar-thumb {
    background: var(--bg-tertiary);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--border-light);
}

/* 텍스트 영역 */
.stTextArea textarea {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}

/* 캡션 */
.stCaption {
    color: var(--text-muted) !important;
}
</style>
"""

st.markdown(CLEAN_CSS, unsafe_allow_html=True)


# === 용어 사전 (툴팁용) ===
GLOSSARY = {
    "market_breadth": {
        "title": "시장 브레드스 (Market Breadth)",
        "desc": "시장 전체 종목의 참여도를 측정하는 지표. 지수는 대형주에 의해 왜곡될 수 있지만, 브레드스는 실제로 얼마나 많은 종목이 상승/하락하는지 보여줍니다.",
        "example": "지수 +1%인데 상승종목 30%뿐이면 → 소수 대형주가 지수를 끌어올리는 것 (위험 신호)"
    },
    "ad_ratio": {
        "title": "A/D Ratio (상승/하락 비율)",
        "desc": "상승 종목수 ÷ 하락 종목수. 1보다 크면 상승 우위, 1보다 작으면 하락 우위.",
        "example": "A/D=1.5 → 상승종목이 하락종목의 1.5배"
    },
    "ma200_ratio": {
        "title": "MA200↑ 비율",
        "desc": "200일 이동평균선 위에 있는 종목의 비율. 장기 추세의 건강도를 나타냅니다. 50% 이상이면 시장 전반이 상승 추세.",
        "example": "MA200↑ 70% → 대부분 종목이 장기 상승 추세"
    },
    "trend_score": {
        "title": "추세 점수 (-100 ~ +100)",
        "desc": "MA정렬(25점) + 가격위치(20점) + 모멘텀(30점) + 추세일관성(15점) + RSI(10점)를 종합한 점수. 높을수록 강한 상승 추세.",
        "example": "+60 이상: 강한 상승 | +30~60: 상승 | -30~+30: 중립 | -60 이하: 강한 하락"
    },
    "golden_cross": {
        "title": "골든크로스",
        "desc": "단기 이동평균(MA20)이 중기 이동평균(MA50)을 상향 돌파하는 것. 상승 추세 전환 신호로 해석됩니다.",
        "example": "MA20이 MA50 위로 올라감 → 매수 신호"
    },
    "death_cross": {
        "title": "데드크로스",
        "desc": "단기 이동평균(MA20)이 중기 이동평균(MA50)을 하향 돌파하는 것. 하락 추세 전환 신호로 해석됩니다.",
        "example": "MA20이 MA50 아래로 내려감 → 매도 신호"
    },
    "52w_high": {
        "title": "52주 신고가",
        "desc": "지난 1년간 최고가를 돌파한 종목. 강한 상승 모멘텀을 나타내며, 추가 상승 가능성이 있습니다.",
        "example": "박스권 돌파 후 신고가 → 새로운 상승 파동 시작 가능"
    },
    "52w_low": {
        "title": "52주 신저가",
        "desc": "지난 1년간 최저가를 이탈한 종목. 강한 하락 모멘텀을 나타내며, 추가 하락 위험이 있습니다.",
        "example": "지지선 붕괴 후 신저가 → 투매 가능성"
    },
    "volume_spike": {
        "title": "거래량 급증",
        "desc": "평균 거래량 대비 2.5배 이상 급증한 종목. 기관/외국인의 관심 또는 중요한 이벤트 발생을 의미할 수 있습니다.",
        "example": "거래량 3x + 가격 상승 → 강한 매수세 유입"
    },
    "ma_alignment": {
        "title": "MA 정렬 상태",
        "desc": "이동평균선의 배열 상태. Perfect Bull: 가격>MA20>MA50>MA200 (완벽한 상승정렬), Perfect Bear: 가격<MA20<MA50<MA200 (완벽한 하락정렬)",
        "example": "MA20↑ MA50↑ MA200↑ → 모든 이평선 위에 있음 (강세)"
    },
    "momentum": {
        "title": "모멘텀",
        "desc": "가격의 변화 속도와 방향. 1주/1개월/3개월 수익률로 측정하며, 높은 모멘텀은 추세 지속 가능성을 시사합니다.",
        "example": "1M +15%, 3M +30% → 강한 상승 모멘텀"
    },
    "sector_rotation": {
        "title": "섹터 로테이션",
        "desc": "시장 사이클에 따라 강세 섹터가 바뀌는 현상. 경기 확장기엔 기술/소비재, 수축기엔 유틸리티/필수소비재가 강세.",
        "example": "기술주↓ 에너지↑ → 경기 사이클 후반 진입 가능"
    },
}


def tooltip(term_key: str, label: str = "") -> str:
    """
    툴팁이 있는 라벨 생성

    Args:
        term_key: GLOSSARY의 키
        label: 표시할 텍스트 (없으면 title 사용)

    Returns:
        HTML 문자열 (한 줄)
    """
    term = GLOSSARY.get(term_key)
    if not term:
        return label or term_key

    display_label = label or term["title"].split("(")[0].strip()
    example_html = f'<div class="tooltip-example">예: {term["example"]}</div>' if term.get("example") else ""

    # 한 줄로 반환 (f-string 내에서 사용 가능)
    return (
        f'<span class="tooltip-container">'
        f'<span>{display_label}</span>'
        f'<span class="tooltip-trigger">?'
        f'<span class="tooltip-content">'
        f'<div class="tooltip-title">{term["title"]}</div>'
        f'<div>{term["desc"]}</div>'
        f'{example_html}'
        f'</span></span></span>'
    )


def section_title_with_tooltip(title: str, term_key: str) -> str:
    """툴팁이 있는 섹션 제목"""
    term = GLOSSARY.get(term_key)
    if not term:
        return f'<div class="section-title">{title}</div>'

    example_html = f'<div class="tooltip-example">예: {term["example"]}</div>' if term.get("example") else ""

    # 한 줄로 반환
    return (
        f'<div class="section-title" style="display:flex; align-items:center; gap:0.5rem;">'
        f'{title}'
        f'<span class="tooltip-trigger">?'
        f'<span class="tooltip-content">'
        f'<div class="tooltip-title">{term["title"]}</div>'
        f'<div>{term["desc"]}</div>'
        f'{example_html}'
        f'</span></span></div>'
    )


# === 유틸리티 ===

def render_metric(label: str, value: str):
    return f'<div class="metric-box"><div class="metric-value">{value}</div><div class="metric-label">{label}</div></div>'

def render_tag(text: str):
    return f'<span class="tag">{text}</span>'

def render_score(score: float):
    cls = "score-high" if score >= 70 else "score-mid" if score >= 50 else "score-low"
    return f'<div class="score-circle {cls}">{score:.0f}</div>'


# === 헬퍼 함수 ===

def is_korean_stock(symbol: str) -> bool:
    """한국 주식 여부 확인"""
    if not symbol:
        return False
    return symbol.endswith(".KS") or symbol.endswith(".KQ")

def format_price(price: float, symbol: str = None, is_korean: bool = None) -> str:
    """가격 포맷팅 (한국: 원화, 그 외: 달러)"""
    if is_korean is None:
        is_korean = is_korean_stock(symbol) if symbol else False

    if is_korean:
        # 원화: 천 단위 구분, 소수점 없음
        return f"₩{price:,.0f}"
    else:
        # 달러: 소수점 2자리
        return f"${price:.2f}"

# === 세션 상태 ===

def init_session_state():
    for k, v in {"screening_results": None, "selected_idea": None, "selected_universe": None}.items():
        if k not in st.session_state:
            st.session_state[k] = v

@st.cache_resource
def load_managers():
    """매니저 로드 (캐시됨)"""
    from screener.ideas import IdeaManager, MarketCondition
    from screener.universe import UniverseManager
    from screener.runner import ScreenerRunner
    return IdeaManager(), UniverseManager(), ScreenerRunner(), MarketCondition


@st.cache_data(ttl=300)  # 5분 캐시
def fetch_stock_data_cached(symbol: str, period: str = "6mo"):
    """주가 데이터 캐시 (5분)"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            return None
        df.columns = df.columns.str.lower()
        df = df.reset_index()
        df = df.rename(columns={'date': 'timestamp'})
        return df
    except Exception:
        return None


@st.cache_data(ttl=600)  # 10분 캐시
def get_universe_symbols_cached(universe_name: str):
    """유니버스 종목 리스트 캐시"""
    from data.universe import get_universe_manager, Universe
    manager = get_universe_manager()
    try:
        universe = Universe[universe_name.upper()]
        return manager.get_symbols(universe)
    except KeyError:
        return []


@st.cache_resource
def get_data_layer_cached():
    """데이터 레이어 매니저 캐시 (리소스)"""
    from data.data_layer import get_data_layer_manager
    return get_data_layer_manager()


@st.cache_data(ttl=300, show_spinner=False)  # 5분 캐시
def fetch_ohlcv_cached(symbol: str, days: int = 180):
    """OHLCV 데이터 캐시"""
    dlm = get_data_layer_cached()
    return dlm.get_data(symbol, days=days, with_indicators=True)

def auto_detect_market(market_code: str = "us"):
    """시장 상황 자동 감지 (캐시 우선)"""
    cache_key = f"detected_{market_code}"

    # 세션 캐시 확인
    cached = st.session_state.get(cache_key)
    if cached:
        return cached

    try:
        from analysis.market_detector import detect_market_condition
        # market_detector 내부에서 파일 캐시 + 폴백 처리
        result = detect_market_condition(market_code)
        st.session_state[cache_key] = result
        return result
    except Exception as e:
        # 에러 시에도 폴백 결과 반환
        from analysis.market_detector import MarketConditionResult, MarketRegime
        from datetime import datetime
        fallback = MarketConditionResult(
            condition=MarketRegime.SIDEWAYS,
            confidence=0,
            timestamp=datetime.now(),
            signals=["⚠️ 시장 데이터 로드 실패"],
            summary="시장 데이터를 가져올 수 없습니다.",
        )
        st.session_state[cache_key] = fallback
        return fallback


# === 사이드바 ===

def render_sidebar():
    st.sidebar.markdown('<div class="logo"><span class="logo-icon">📈</span><span class="logo-text">StockLens</span></div>', unsafe_allow_html=True)

    menu_options = ["📊 마켓", "📈 차트", "🔬 TA 스크리너", "🎯 스크리너", "🌐 유니버스", "⚙️ 설정"]

    # 네비게이션 요청 처리 (위젯 생성 전에)
    nav_to = st.session_state.pop("_nav_to", None)
    if nav_to and nav_to in menu_options:
        default_idx = menu_options.index(nav_to)
    else:
        default_idx = 0

    menu = st.sidebar.radio("메뉴", menu_options, index=default_idx, label_visibility="collapsed")
    st.sidebar.markdown("---")

    # 시장 선택
    st.sidebar.markdown("**분석 시장**")
    market_map = {"미국": "us", "한국": "korea", "크립토": "crypto"}
    selected = st.sidebar.radio("시장", list(market_map.keys()), horizontal=True, label_visibility="collapsed")
    market_code = market_map[selected]

    # 시장 감지
    detected = auto_detect_market(market_code)
    cond_str = "강세장"

    if detected:
        cond = detected.condition.value
        conf = detected.confidence
        labels = {"bull": "강세장", "bear": "약세장", "sideways": "횡보장", "volatile": "변동성", "recovery": "회복기", "correction": "조정기"}
        cond_str = labels.get(cond, "강세장")

        # 시장 상황 상세 표시
        st.sidebar.markdown(f'''
        <div class="market-box">
            <div class="market-header">
                <span class="market-title">{cond_str}</span>
                <span class="text-xs">신뢰도 {conf:.0f}%</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        # 판단 근거 표시
        with st.sidebar.expander("판단 근거 보기"):
            if detected.index_analyses:
                for idx in detected.index_analyses[:5]:
                    trend_icon = "↑" if idx.trend == "uptrend" else "↓" if idx.trend == "downtrend" else "→"
                    st.markdown(f"**{idx.name}** {trend_icon}")
                    col1, col2 = st.columns(2)
                    col1.caption(f"1M: {idx.change_1m:+.1f}%")
                    col2.caption(f"MA: {'상향' if idx.above_ma50 else '하향'}")

            # 추가 지표
            if detected.vix_level:
                indicator_name = "F&G" if market_code == "crypto" else "VIX"
                st.markdown(f"**{indicator_name}**: {detected.vix_level:.1f}")

            if hasattr(detected, 'metadata') and detected.metadata:
                meta = detected.metadata
                if 'macd_signal' in meta:
                    st.caption(f"MACD: {meta.get('macd_signal', 'N/A')}")
                if 'adx' in meta:
                    st.caption(f"ADX: {meta.get('adx', 0):.1f}")

    # 수동 변경
    with st.sidebar.expander("시장 수동 설정"):
        manual = st.selectbox("상황", ["강세장", "약세장", "횡보장", "회복기", "조정기"], label_visibility="collapsed")
        if st.button("적용", width="stretch", key="apply_market"):
            cond_str = manual

    return menu, cond_str


# === 스크리너 페이지 ===

def render_screening_page(idea_manager, universe_manager, runner, market_cond_str, MarketCondition):
    st.markdown("## 🎯 스마트 스크리너")
    st.caption("시장 상황에 맞는 최적의 종목을 발굴합니다")

    cond_map = {"강세장": MarketCondition.BULL, "약세장": MarketCondition.BEAR, "횡보장": MarketCondition.SIDEWAYS, "회복기": MarketCondition.RECOVERY, "조정기": MarketCondition.CORRECTION}
    current_cond = cond_map.get(market_cond_str, MarketCondition.BULL)

    tab1, tab2, tab3, tab4 = st.tabs(["원클릭", "커스텀", "고급", "결과"])

    with tab1:
        render_quick_tab(idea_manager, universe_manager, runner, current_cond)
    with tab2:
        render_custom_tab(idea_manager, universe_manager, runner, current_cond)
    with tab3:
        render_advanced_tab(idea_manager, universe_manager, runner)
    with tab4:
        render_results_tab()


def render_quick_tab(idea_manager, universe_manager, runner, current_cond):
    """원클릭 스크리닝"""

    # 유니버스 선택
    all_univ = universe_manager.list_all()
    univ_opts = {f"{u.name} ({u.symbol_count}종목)": u.id for u in all_univ if u.symbol_count and u.symbol_count > 0}

    col_univ, col_empty = st.columns([2, 3])
    with col_univ:
        if univ_opts:
            sel_univ = st.selectbox("유니버스", list(univ_opts.keys())[:10], key="q_univ", label_visibility="collapsed")
            univ_id = univ_opts.get(sel_univ)
        else:
            st.warning("유니버스가 없습니다")
            univ_id = None

    st.markdown("")

    # 전략 목록
    all_ideas = idea_manager.list_all()
    ideas = sorted(all_ideas, key=lambda i: (0 if current_cond in i.suitable_conditions else 1, i.name))

    # 2열 그리드로 표시
    cols = st.columns(2)
    for i, idea in enumerate(ideas[:12]):
        with cols[i % 2]:
            # 카드 컨테이너
            card_col, btn_col = st.columns([5, 1])
            with card_col:
                st.markdown(f'''
                <div style="background:white; border:1px solid #e5e7eb; border-radius:8px; padding:0.875rem; height:100%;">
                    <div style="font-weight:600; color:#111827; font-size:0.9rem; margin-bottom:0.25rem;">{idea.name}</div>
                    <div style="font-size:0.8rem; color:#6b7280; line-height:1.4;">{idea.description.strip()[:80]}{"..." if len(idea.description.strip()) > 80 else ""}</div>
                    <div style="font-size:0.7rem; color:#9ca3af; margin-top:0.375rem;">{idea.expected_holding_period} · {idea.risk_level}</div>
                </div>
                ''', unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                if st.button("▶", key=f"q_run_{idea.id}", help="스크리닝 실행"):
                    if univ_id:
                        run_screening(runner, idea.id, univ_id)
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)


def render_custom_tab(idea_manager, universe_manager, runner, current_cond):
    """커스텀 설정 - 전략 기반 필터 조정"""
    from screener.ideas import COMMON_FILTERS, FILTER_CATEGORIES, FILTER_BY_CATEGORY

    # 상단: 전략 + 유니버스 선택
    col1, col2 = st.columns(2)

    with col1:
        all_ideas = idea_manager.list_all()
        ideas = sorted(all_ideas, key=lambda i: (0 if current_cond in i.suitable_conditions else 1, i.name))
        idea_opts = {i.name: i.id for i in ideas}
        sel_idea_name = st.selectbox("전략 선택", list(idea_opts.keys()), key="c_idea")
        idea_id = idea_opts.get(sel_idea_name)
        idea = idea_manager.get(idea_id) if idea_id else None

    with col2:
        all_univ = universe_manager.list_all()
        univ_opts = {f"{u.name} ({u.symbol_count}종목)": u.id for u in all_univ if u.symbol_count}
        sel_univ = st.selectbox("유니버스 선택", list(univ_opts.keys()), key="c_univ")
        univ_id = univ_opts.get(sel_univ) if univ_opts else None

    # 전략 설명
    if idea:
        st.markdown(f'''
        <div class="card">
            <div class="card-desc">{idea.description.strip()}</div>
            <div class="card-meta">{idea.expected_holding_period} · {idea.risk_level} · {idea.strategy_type or "일반"}</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("---")

    # 필터 수정 영역
    if idea:
        filter_key = f"filters_{idea_id}"
        if filter_key not in st.session_state:
            st.session_state[filter_key] = dict(idea.filters)

        filters = st.session_state[filter_key]

        # 현재 적용된 필터를 카테고리별로 그룹핑
        st.markdown('<div class="section-title">적용 필터 (클릭하여 수정)</div>', unsafe_allow_html=True)

        # 현재 필터 태그 표시
        filter_tags = []
        for k, v in filters.items():
            f_def = COMMON_FILTERS.get(k)
            if f_def:
                if f_def.type == "bool":
                    filter_tags.append(f_def.display_name if v else f"❌{f_def.display_name}")
                else:
                    filter_tags.append(f"{f_def.display_name}: {v}{f_def.unit or ''}")
        st.markdown(" ".join([f'<span class="tag">{t}</span>' for t in filter_tags]), unsafe_allow_html=True)

        st.markdown("")

        # 카테고리별 필터 편집
        filter_cats = {}
        for k in filters.keys():
            for cat_key, cat_filters in FILTER_BY_CATEGORY.items():
                if k in cat_filters:
                    if cat_key not in filter_cats:
                        filter_cats[cat_key] = []
                    filter_cats[cat_key].append(k)
                    break

        # 2열 레이아웃으로 카테고리 표시
        cat_keys = list(filter_cats.keys())
        mid = (len(cat_keys) + 1) // 2
        col_l, col_r = st.columns(2)

        def render_filter_group(cat_key, filter_list, container):
            with container:
                cat_name = FILTER_CATEGORIES.get(cat_key, cat_key)
                with st.expander(cat_name, expanded=True):
                    for k in filter_list:
                        f_def = COMMON_FILTERS.get(k)
                        if not f_def:
                            continue
                        v = filters.get(k)
                        col_a, col_b = st.columns([3, 2])
                        with col_a:
                            st.markdown(f"**{f_def.display_name}**", help=f_def.description if f_def.description else None)
                        with col_b:
                            if f_def.type == "bool":
                                filters[k] = st.checkbox("활성화", value=bool(v), key=f"cf_{idea_id}_{k}", label_visibility="collapsed")
                            else:
                                filters[k] = st.number_input(
                                    f_def.unit or "값",
                                    value=float(v) if v is not None else 0.0,
                                    step=float(f_def.step) if f_def.step else 1.0,
                                    key=f"cf_{idea_id}_{k}",
                                    label_visibility="collapsed"
                                )

        for i, cat_key in enumerate(cat_keys[:mid]):
            render_filter_group(cat_key, filter_cats[cat_key], col_l)
        for i, cat_key in enumerate(cat_keys[mid:]):
            render_filter_group(cat_key, filter_cats[cat_key], col_r)

        st.session_state[filter_key] = filters

        # 추가 필터 섹션
        with st.expander("필터 추가"):
            st.caption("전략에 없는 필터를 추가할 수 있습니다")
            add_cols = st.columns([3, 2, 1])

            # 아직 적용되지 않은 필터 목록
            available = [k for k in COMMON_FILTERS.keys() if k not in filters]
            with add_cols[0]:
                new_filter = st.selectbox(
                    "필터",
                    available,
                    format_func=lambda x: COMMON_FILTERS[x].display_name,
                    key="c_add_filter",
                    label_visibility="collapsed"
                )
            with add_cols[1]:
                if new_filter:
                    f_def = COMMON_FILTERS[new_filter]
                    if f_def.type == "bool":
                        new_val = st.checkbox("활성화", value=True, key="c_add_val", label_visibility="collapsed")
                    else:
                        new_val = st.number_input(
                            "값",
                            value=float(f_def.default) if f_def.default is not None else 0.0,
                            step=float(f_def.step) if f_def.step else 1.0,
                            key="c_add_val",
                            label_visibility="collapsed"
                        )
            with add_cols[2]:
                if st.button("추가", key="c_add_btn"):
                    if new_filter:
                        filters[new_filter] = new_val
                        st.session_state[filter_key] = filters
                        st.rerun()

    # 실행 옵션
    st.markdown("---")
    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        days = st.selectbox("기간", [90, 180, 365, 730], index=2, format_func=lambda x: f"{x}일", key="c_days")
    with col_b:
        workers = st.selectbox("워커", [5, 10, 15, 20], index=1, key="c_workers")
    with col_c:
        if st.button("스크리닝 실행", type="primary", width="stretch", key="c_run"):
            if idea and univ_id:
                run_screening(runner, idea_id, univ_id, days, workers, True, st.session_state.get(filter_key, {}))
            else:
                st.error("전략과 유니버스를 선택하세요")


def render_advanced_tab(idea_manager, universe_manager, runner):
    """고급 필터 - Finviz 스타일"""
    from screener.ideas import COMMON_FILTERS, FILTER_CATEGORIES, FILTER_BY_CATEGORY

    if "adv_filters" not in st.session_state:
        st.session_state.adv_filters = {}

    # 상단 컨트롤
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    with c1:
        all_univ = universe_manager.list_all()
        univ_opts = {f"{u.name} ({u.symbol_count}종목)": u.id for u in all_univ if u.symbol_count}
        sel_univ = st.selectbox("유니버스", list(univ_opts.keys()), key="a_univ", label_visibility="collapsed")
        univ_id = univ_opts.get(sel_univ)
    with c2:
        days = st.selectbox("기간", [90, 180, 365, 730], index=2, format_func=lambda x: f"{x}일", key="a_days", label_visibility="collapsed")
    with c3:
        if st.button("초기화", width="stretch", key="a_reset"):
            st.session_state.adv_filters = {}
            st.rerun()
    with c4:
        cnt = len(st.session_state.adv_filters)
        if st.button(f"실행 ({cnt})", type="primary", width="stretch", key="a_run", disabled=cnt == 0):
            run_screening(runner, "quick_momentum", univ_id, days, 10, True, st.session_state.adv_filters)

    st.markdown("")

    # 좌우 2열
    left_cats = ["descriptive", "valuation", "profitability", "growth", "dividend", "financial"]
    right_cats = ["performance", "price_position", "moving_average", "momentum", "volume", "volatility"]

    col_l, col_r = st.columns(2)

    def render_filter_row(k: str, f_def):
        """단일 필터 행 렌더링"""
        is_active = k in st.session_state.adv_filters
        default_val = f_def.default if f_def.default is not None else 0

        # 체크박스 | 필터명 | 값입력 - 고정 비율
        cols = st.columns([0.8, 4, 2.5])

        with cols[0]:
            checked = st.checkbox("v", value=is_active, key=f"a_chk_{k}", label_visibility="collapsed")

        with cols[1]:
            label_color = "#111827" if checked else "#9ca3af"
            st.markdown(f"<div style='font-size:0.85rem; color:{label_color}; padding-top:5px;'>{f_def.display_name}</div>", unsafe_allow_html=True)

        with cols[2]:
            if f_def.type == "bool":
                if checked:
                    curr = st.session_state.adv_filters.get(k, True)
                    val = st.toggle("켜기", value=bool(curr), key=f"a_val_{k}", label_visibility="collapsed")
                    st.session_state.adv_filters[k] = val
                else:
                    st.markdown("<div style='color:#d1d5db; font-size:0.8rem; padding-top:5px;'>-</div>", unsafe_allow_html=True)
                    if k in st.session_state.adv_filters:
                        del st.session_state.adv_filters[k]
            else:
                # 숫자 필터 - 항상 입력창 표시
                curr = st.session_state.adv_filters.get(k, default_val) if checked else default_val
                val = st.text_input(
                    "값",
                    value=str(curr),
                    key=f"a_val_{k}",
                    label_visibility="collapsed",
                    disabled=not checked
                )
                if checked:
                    try:
                        st.session_state.adv_filters[k] = float(val)
                    except ValueError:
                        st.session_state.adv_filters[k] = default_val
                else:
                    if k in st.session_state.adv_filters:
                        del st.session_state.adv_filters[k]

    def render_category(cat_key: str, container):
        cat_name = FILTER_CATEGORIES.get(cat_key, cat_key)
        filter_keys = FILTER_BY_CATEGORY.get(cat_key, [])
        active_cnt = sum(1 for fk in filter_keys if fk in st.session_state.adv_filters)
        title = f"{cat_name} ({active_cnt})" if active_cnt else cat_name

        with container:
            with st.expander(title, expanded=False):
                for k in filter_keys:
                    if k in COMMON_FILTERS:
                        render_filter_row(k, COMMON_FILTERS[k])

    for cat in left_cats:
        render_category(cat, col_l)
    for cat in right_cats:
        render_category(cat, col_r)


def render_results_tab():
    """결과 탭"""

    if not st.session_state.screening_results:
        st.info("스크리닝을 실행하면 결과가 여기에 표시됩니다")
        return

    result = st.session_state.screening_results

    # 메트릭
    cols = st.columns(5)
    for col, (label, val) in zip(cols, [
        ("검색", f"{result.meta.universe_size:,}"),
        ("분석", f"{result.meta.screened_count:,}"),
        ("통과", f"{result.meta.passed_count:,}"),
        ("시간", f"{result.meta.execution_time_sec:.1f}s"),
        ("품질", f"{result.meta.avg_data_quality:.0f}%"),
    ]):
        with col:
            st.markdown(render_metric(label, val), unsafe_allow_html=True)

    stats = result.meta.metadata.get("fetch_stats", {})
    if stats:
        cached = stats.get("cached", 0)
        total = stats.get("total", 1)
        st.caption(f"캐시: {cached}/{total} ({cached/total*100:.0f}%)")

    st.markdown("---")

    if not result.candidates:
        st.warning("통과 종목이 없습니다. 필터를 완화해 보세요.")
        return

    t1, t2, t3 = st.tabs(["순위", "차트", "상세"])

    with t1:
        render_ranking(result)
    with t2:
        render_charts(result)
    with t3:
        render_detail(result)


def render_ranking(result):
    """순위 표시"""

    st.markdown('<div class="section-title">Top 3</div>', unsafe_allow_html=True)
    top_cols = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]

    for i, (col, c) in enumerate(zip(top_cols, result.candidates[:3])):
        with col:
            md = c.metadata.get("momentum_data", {})
            ret_1m = md.get("return_1m", 0)
            st.markdown(f'''
            <div class="top-card">
                <div class="top-rank">{medals[i]}</div>
                <div class="top-ticker">{c.symbol.ticker}</div>
                <div class="top-name">{c.symbol.name or ""}</div>
                {render_score(c.final_score)}
                <div class="text-sm" style="margin-top:0.5rem;">1M: {ret_1m:+.1f}%</div>
            </div>
            ''', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-title">전체 순위</div>', unsafe_allow_html=True)

    df = result.to_dataframe()

    def color_score(v):
        if v >= 70: return 'background-color: #dcfce7'
        elif v >= 50: return 'background-color: #fef3c7'
        return 'background-color: #fee2e2'

    styled = df.style.map(color_score, subset=['score'])
    st.dataframe(styled, width='stretch', height=350)

    csv = df.to_csv(index=False)
    st.download_button("CSV 다운로드", csv, f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")


def render_charts(result):
    """차트"""
    import plotly.express as px

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-title">점수 분포</div>', unsafe_allow_html=True)
        scores = [c.final_score for c in result.candidates]
        fig = px.histogram(x=scores, nbins=10, labels={'x': '점수', 'y': '종목수'})
        fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown('<div class="section-title">Top 10 비교</div>', unsafe_allow_html=True)
        top10 = result.candidates[:10]
        if top10 and top10[0].scores:
            data = [{"종목": c.symbol.ticker, "항목": k, "점수": v} for c in top10 for k, v in c.scores.items()]
            if data:
                df = pd.DataFrame(data)
                fig2 = px.bar(df, x="종목", y="점수", color="항목", barmode="group")
                fig2.update_layout(legend=dict(orientation="h", y=1.1), margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig2, width='stretch')


def render_detail(result):
    """상세"""
    col1, col2 = st.columns([1, 2])

    with col1:
        tickers = [f"{c.symbol.ticker} ({c.final_score:.0f}점)" for c in result.candidates]
        sel = st.selectbox("종목", tickers, key="detail_sel", label_visibility="collapsed")

        if sel:
            ticker = sel.split(" ")[0]
            cand = next((c for c in result.candidates if c.symbol.ticker == ticker), None)

            if cand:
                st.markdown(f'''
                <div class="card" style="text-align:center;">
                    {render_score(cand.final_score)}
                    <div style="margin-top:0.5rem; font-weight:600;">{cand.symbol.ticker}</div>
                    <div class="text-sm">{cand.symbol.name or ""}</div>
                </div>
                ''', unsafe_allow_html=True)

                for k, v in cand.scores.items():
                    st.progress(v / 100, text=f"{k}: {v:.0f}")

    with col2:
        if sel:
            ticker = sel.split(" ")[0]
            cand = next((c for c in result.candidates if c.symbol.ticker == ticker), None)

            if cand:
                md = cand.metadata.get("momentum_data", {})
                if md:
                    st.markdown('<div class="section-title">수익률</div>', unsafe_allow_html=True)
                    m_cols = st.columns(4)
                    for col, (label, key) in zip(m_cols, [("1M", "return_1m"), ("3M", "return_3m"), ("6M", "return_6m"), ("12M", "return_12m")]):
                        val = md.get(key)
                        with col:
                            if val is not None:
                                st.markdown(render_metric(label, f"{val:+.1f}%"), unsafe_allow_html=True)

                dm = result.data_metas.get(ticker)
                if dm:
                    st.markdown('<div class="section-title">데이터 품질</div>', unsafe_allow_html=True)
                    q_cols = st.columns(3)
                    q_cols[0].metric("기간", dm.period_str)
                    q_cols[1].metric("신선도", dm.freshness.value)
                    q_cols[2].metric("품질", f"{dm.quality_score:.0f}%")


# === 스크리닝 실행 ===

def run_screening(runner, idea_id, univ_id, days=365, workers=10, use_cache=True, filters=None):
    progress = st.progress(0)
    status = st.empty()

    def callback(cur, tot, sym, stat):
        progress.progress(cur / tot if tot > 0 else 0)
        status.caption(f"[{cur}/{tot}] {sym}")

    try:
        result = runner.run(idea_id, univ_id, data_source=None, days=days, workers=workers, use_cache=use_cache, progress_callback=callback, filter_overrides=filters)
        st.session_state.screening_results = result
        progress.progress(1.0)
        status.empty()

        stats = result.meta.metadata.get("fetch_stats", {})
        cached = stats.get("cached", 0)
        st.success(f"완료! {result.meta.passed_count}개 발견 | 캐시: {cached}/{result.meta.screened_count} | {result.meta.execution_time_sec:.1f}s")
        st.rerun()

    except Exception as e:
        status.empty()
        st.error(f"오류: {e}")


# === 유니버스 페이지 ===

def render_universe_page(universe_manager):
    st.markdown("## 🌐 유니버스 관리")
    st.caption("스크리닝 대상 종목 그룹")

    tab1, tab2 = st.tabs(["목록", "생성"])

    with tab1:
        universes = universe_manager.list_all()
        cols = st.columns(3)
        for i, u in enumerate(universes):
            with cols[i % 3]:
                icons = {"kospi": "🇰🇷", "kosdaq": "🇰🇷", "nasdaq": "🇺🇸", "nyse": "🇺🇸", "crypto": "₿"}
                icon = icons.get(u.market.value if u.market else "", "📊")
                st.markdown(f'''
                <div class="card">
                    <div class="card-title">{icon} {u.name}</div>
                    <div class="card-desc">{u.symbol_count or 0}종목 · {u.description or ""}</div>
                </div>
                ''', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="section-title">새 워치리스트</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름", placeholder="내 워치리스트")
            desc = st.text_input("설명", placeholder="관심 종목")
        with col2:
            symbols = st.text_area("종목 (쉼표 구분)", placeholder="AAPL, NVDA, MSFT", height=108)

        if st.button("생성", type="primary"):
            if name and symbols:
                sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
                wl = universe_manager.create_watchlist(name, sym_list, desc)
                st.success(f"'{wl.name}' 생성 완료")
                st.rerun()


# === 설정 페이지 ===

def render_settings_page(runner):
    st.markdown("## ⚙️ 설정")

    tab1, tab2, tab3 = st.tabs(["캐시", "데이터 레이어", "시스템"])

    with tab1:
        st.markdown('<div class="section-title">OHLCV 캐시</div>', unsafe_allow_html=True)

        try:
            stats = runner.get_cache_stats()
            cols = st.columns(4)
            cols[0].metric("종목", stats['total_symbols'])
            cols[1].metric("데이터", f"{stats['total_rows']:,}행")
            cols[2].metric("크기", f"{stats['cache_size_mb']:.1f}MB")
            cols[3].metric("히트율", f"{stats.get('hit_rate', 0):.0f}%")
        except Exception as e:
            st.warning(f"통계 로드 실패: {e}")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            hours = st.number_input("시간", min_value=1, value=24, key="cache_hours")
            if st.button("오래된 캐시 정리", width="stretch"):
                runner.clear_cache(older_than_hours=hours)
                st.success("정리 완료")
        with col_b:
            st.write("")
            st.write("")
            if st.button("전체 캐시 삭제", width="stretch", type="secondary"):
                runner.clear_cache()
                st.success("삭제 완료")

    with tab2:
        render_data_layer_tab()

    with tab3:
        st.markdown('<div class="section-title">실행 기록</div>', unsafe_allow_html=True)
        history = runner.get_history(limit=5)
        if history:
            for h in history:
                st.markdown(f'''
                <div class="card">
                    <div class="card-title">{h['strategy']}</div>
                    <div class="card-desc">{h['market']} | {h['passed']}/{h['universe_size']} | {h['execution_time']}</div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.info("기록 없음")


def render_data_layer_tab():
    """데이터 레이어 관리 탭"""
    try:
        from data.data_layer import get_data_layer_manager, PrefetchConfig
        dlm = get_data_layer_manager()
    except Exception as e:
        st.error(f"데이터 레이어 로드 실패: {e}")
        return

    # 통계
    st.markdown('<div class="section-title">데이터 레이어 통계</div>', unsafe_allow_html=True)
    stats = dlm.get_stats()

    cols = st.columns(4)
    cols[0].metric("캐시 크기", f"{stats['cache_size_mb']:.1f}MB")
    cols[1].metric("지표 캐시", f"{stats['indicator_cache_count']}개")
    cols[2].metric("캐시 히트율", f"{stats['hit_rate']:.1f}%")
    cols[3].metric("프리페치 수", f"{stats['prefetch_count']:,}")

    # 프리페치 상태
    st.markdown("---")
    st.markdown('<div class="section-title">프리페치 상태</div>', unsafe_allow_html=True)

    prefetch_status = stats.get("prefetch_status", {})
    if prefetch_status:
        for uid, info in prefetch_status.items():
            last = info.get("last_prefetch", "N/A")
            if last != "N/A":
                try:
                    last_dt = datetime.fromisoformat(last)
                    last = last_dt.strftime("%m/%d %H:%M")
                except Exception:
                    pass

            st.markdown(f'''
            <div class="card">
                <div class="card-title">{uid}</div>
                <div class="card-desc">{info.get("success_count", 0)}/{info.get("symbol_count", 0)} 종목 · {info.get("duration_sec", 0):.1f}초 · 마지막: {last}</div>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("프리페치 기록 없음")

    # 워밍업
    st.markdown("---")
    st.markdown('<div class="section-title">캐시 워밍업</div>', unsafe_allow_html=True)

    warmup_cols = st.columns([2, 1, 1])
    with warmup_cols[0]:
        universe_options = ["sp500", "nasdaq100", "kospi200", "kosdaq150"]
        selected_universe = st.selectbox("유니버스", universe_options, key="warmup_univ", label_visibility="collapsed")
    with warmup_cols[1]:
        compute_indicators = st.checkbox("지표 계산", value=True, key="warmup_indicators")
    with warmup_cols[2]:
        if st.button("워밍업 시작", type="primary", width="stretch", key="warmup_btn"):
            run_warmup(dlm, selected_universe, compute_indicators)

    # 백그라운드 작업
    st.markdown("---")
    st.markdown('<div class="section-title">백그라운드 작업</div>', unsafe_allow_html=True)

    bg_cols = st.columns([3, 1])
    with bg_cols[0]:
        status_text = "실행 중" if stats.get("background_running") else "중지됨"
        status_color = "#059669" if stats.get("background_running") else "#dc2626"
        st.markdown(f'<span style="color:{status_color}; font-weight:600;">● {status_text}</span>', unsafe_allow_html=True)
        st.caption("자동 프리페치 및 캐시 정리")
    with bg_cols[1]:
        if stats.get("background_running"):
            if st.button("중지", width="stretch"):
                dlm.stop_background_tasks()
                st.rerun()
        else:
            if st.button("시작", type="primary", width="stretch"):
                dlm.start_background_tasks()
                st.rerun()

    # 자주 접근하는 종목
    st.markdown("---")
    st.markdown('<div class="section-title">자주 접근하는 종목 Top 10</div>', unsafe_allow_html=True)

    top_symbols = dlm.get_top_accessed_symbols(10)
    if top_symbols:
        data = []
        for s in top_symbols:
            data.append({
                "종목": s["symbol"],
                "접근수": s["access_count"],
                "평균응답(ms)": f"{s['avg_response_ms']:.1f}" if s['avg_response_ms'] else "-",
            })
        st.dataframe(pd.DataFrame(data), width="stretch", hide_index=True)
    else:
        st.info("접근 기록 없음")


def run_warmup(dlm, universe_id: str, compute_indicators: bool):
    """캐시 워밍업 실행"""
    progress = st.progress(0)
    status = st.empty()

    def callback(cur, tot, sym, stat):
        progress.progress(cur / tot if tot > 0 else 0)
        status.caption(f"[{cur}/{tot}] {sym} - {stat}")

    try:
        result = dlm.prefetch_universe(
            universe_id=universe_id,
            compute_indicators=compute_indicators,
            progress_callback=callback,
        )

        progress.progress(1.0)
        status.empty()

        if result["success"]:
            st.success(f"완료! {result['fetched']}/{result['total']}개 로드 (캐시: {result['cached']}, {result['duration_sec']:.1f}초)")
        else:
            st.error(f"실패: {result.get('error', 'Unknown error')}")

    except Exception as e:
        status.empty()
        st.error(f"워밍업 오류: {e}")


# === Chart 페이지 ===

def render_chart_page():
    """개별 종목 차트 페이지"""
    st.markdown("## 📈 기술적 분석 차트")
    st.caption("종목별 OHLCV 차트 및 기술적 지표")

    from dashboard.charts import create_candlestick_chart, create_technical_summary, get_signal_color

    # 상단 입력 - 정렬 개선
    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        symbol = st.text_input(
            "종목 심볼",
            value=st.session_state.get("chart_symbol", "AAPL"),
            placeholder="AAPL, MSFT, 005930.KS...",
            key="chart_symbol_input",
            label_visibility="collapsed"
        ).strip().upper()

    with col2:
        period = st.selectbox(
            "기간",
            ["1M", "3M", "6M", "1Y", "2Y"],
            index=2,
            key="chart_period",
            label_visibility="collapsed"
        )
        period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "2Y": 730}
        days = period_days.get(period, 180)

    with col3:
        if st.button("차트 로드", type="primary", use_container_width=True):
            st.session_state["chart_symbol"] = symbol

    if not symbol:
        st.info("종목 심볼을 입력하세요")
        return

    # 데이터 로드
    try:
        from data.data_layer import get_data_layer_manager
        dlm = get_data_layer_manager()
        df = dlm.get_data(symbol, days=days, with_indicators=True)

        if df is None or df.empty:
            st.warning(f"'{symbol}' 데이터를 찾을 수 없습니다")
            return

        st.session_state["chart_symbol"] = symbol

    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return

    # 차트 옵션 - 정렬 개선
    st.markdown("---")

    # 첫 번째 행: 이동평균선 (전체 너비)
    show_ma = st.multiselect(
        "이동평균선",
        [5, 10, 20, 50, 100, 200],
        default=[20, 50, 200],
        key="chart_ma"
    )

    # 두 번째 행: 지표 옵션들 (균등 분할)
    opt_col1, opt_col2, opt_col3, opt_col4 = st.columns(4)
    with opt_col1:
        show_bb = st.checkbox("볼린저 밴드", value=True, key="chart_bb")
    with opt_col2:
        show_macd = st.checkbox("MACD", value=True, key="chart_macd")
    with opt_col3:
        show_rsi = st.checkbox("RSI", value=True, key="chart_rsi")
    with opt_col4:
        show_signals = st.checkbox("📍 시그널", value=True, key="chart_signals")

    # 시그널 데이터 확인 (세션에서 가져오기)
    signal_data = None
    if show_signals:
        signal_data = st.session_state.get("chart_signal_data")
        # 심볼이 다르면 시그널 데이터 무효화
        if signal_data and signal_data.get("symbol") != symbol:
            signal_data = None

    # 차트 생성
    from dashboard.charts import add_signal_overlay

    fig = create_candlestick_chart(
        df,
        symbol=symbol,
        show_ma=show_ma,
        show_bb=show_bb,
        show_volume=True,
        show_macd=show_macd,
        show_rsi=show_rsi,
        height=650,
    )

    # 시그널 오버레이 추가
    if signal_data:
        fig = add_signal_overlay(fig, df, signal_data, row=1)

        # 시그널 정보 표시
        direction = "🟢 롱" if signal_data.get('direction') == 'bullish' else "🔴 숏"
        pattern = signal_data.get('pattern_type', '')
        st.success(f"**{direction} 시그널 표시 중** - {pattern}")

    st.plotly_chart(fig, width="stretch")

    # 기술적 분석 요약
    st.markdown("---")
    st.markdown("### 기술적 분석 요약")

    summary = create_technical_summary(df)
    if not summary:
        return

    cols = st.columns(5)

    # 가격 정보
    with cols[0]:
        change_color = "#26a69a" if summary.get("change_1d", 0) >= 0 else "#ef5350"
        st.markdown(f"""
        <div style="text-align:center; padding:0.5rem; background:#f9fafb; border-radius:8px;">
            <div style="font-size:0.75rem; color:#6b7280;">현재가</div>
            <div style="font-size:1.25rem; font-weight:600;">{summary['price']:,.2f}</div>
            <div style="font-size:0.875rem; color:{change_color};">{summary.get('change_1d', 0):+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # MA 상태
    with cols[1]:
        ma_html = ""
        for ma in summary.get("ma_status", []):
            color = "#26a69a" if ma["above"] else "#ef5350"
            icon = "▲" if ma["above"] else "▼"
            ma_html += f'<div style="font-size:0.8rem;"><span style="color:{color}">{icon}</span> MA{ma["period"]}: {ma["distance"]:+.1f}%</div>'
        st.markdown(f"""
        <div style="padding:0.5rem; background:#f9fafb; border-radius:8px;">
            <div style="font-size:0.75rem; color:#6b7280; margin-bottom:0.25rem;">이동평균</div>
            {ma_html or '<div style="color:#6b7280;">-</div>'}
        </div>
        """, unsafe_allow_html=True)

    # RSI
    with cols[2]:
        rsi_data = summary.get("rsi", {})
        rsi_val = rsi_data.get("value", 50)
        rsi_sig = rsi_data.get("signal", "중립")
        rsi_color = get_signal_color(rsi_sig)
        st.markdown(f"""
        <div style="text-align:center; padding:0.5rem; background:#f9fafb; border-radius:8px;">
            <div style="font-size:0.75rem; color:#6b7280;">RSI</div>
            <div style="font-size:1.25rem; font-weight:600;">{rsi_val:.1f}</div>
            <div style="font-size:0.8rem; color:{rsi_color};">{rsi_sig}</div>
        </div>
        """, unsafe_allow_html=True)

    # MACD
    with cols[3]:
        macd_data = summary.get("macd", {})
        macd_trend = macd_data.get("trend", "-")
        macd_color = get_signal_color(macd_trend)
        st.markdown(f"""
        <div style="text-align:center; padding:0.5rem; background:#f9fafb; border-radius:8px;">
            <div style="font-size:0.75rem; color:#6b7280;">MACD</div>
            <div style="font-size:1.25rem; font-weight:600; color:{macd_color};">{macd_trend}</div>
            <div style="font-size:0.75rem; color:#6b7280;">Hist: {macd_data.get('hist', 0):.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    # 거래량
    with cols[4]:
        vol_data = summary.get("volume", {})
        vol_ratio = vol_data.get("ratio", 1.0)
        vol_sig = vol_data.get("signal", "보통")
        vol_color = get_signal_color(vol_sig)
        st.markdown(f"""
        <div style="text-align:center; padding:0.5rem; background:#f9fafb; border-radius:8px;">
            <div style="font-size:0.75rem; color:#6b7280;">거래량</div>
            <div style="font-size:1.25rem; font-weight:600;">{vol_ratio:.1f}x</div>
            <div style="font-size:0.8rem; color:{vol_color};">{vol_sig}</div>
        </div>
        """, unsafe_allow_html=True)

    # 데이터 정보
    st.markdown("---")
    st.caption(f"데이터: {len(df)}일 | {df['timestamp'].min().strftime('%Y-%m-%d')} ~ {df['timestamp'].max().strftime('%Y-%m-%d')}")


# === Market Overview 페이지 ===

def render_market_overview_page():
    """시장 현황 페이지 - 시계열 흐름 기반"""
    st.markdown("## 📊 시장 현황")
    st.caption("시계열 흐름 기반의 시장 분석")

    # 시장 선택
    col_market, col_refresh = st.columns([3, 1])
    with col_market:
        market_options = {"미국": "us", "한국": "korea", "크립토": "crypto"}
        selected_market = st.selectbox(
            "시장",
            list(market_options.keys()),
            key="overview_market",
            label_visibility="collapsed"
        )
        market_code = market_options[selected_market]

    with col_refresh:
        refresh = st.button("새로고침", width="stretch", key="overview_refresh")

    # 캐시된 데이터 또는 새로 로드
    cache_key = f"market_overview_{market_code}"
    if refresh or cache_key not in st.session_state:
        with st.spinner("시장 데이터 분석 중..."):
            try:
                from analysis.market_overview import MarketOverviewAnalyzer
                analyzer = MarketOverviewAnalyzer()

                progress = st.progress(0)
                status = st.empty()

                def callback(cur, tot, sym, stat):
                    progress.progress(cur / tot if tot > 0 else 0)
                    status.caption(f"[{cur}/{tot}] {sym}")

                overview = analyzer.get_overview(
                    market=market_code,
                    top_n=15,
                    progress_callback=callback,
                )
                st.session_state[cache_key] = overview
                progress.empty()
                status.empty()
            except Exception as e:
                st.error(f"분석 오류: {e}")
                import traceback
                st.code(traceback.format_exc())
                return

    overview = st.session_state.get(cache_key)
    if not overview:
        st.info("데이터를 로드하려면 새로고침을 클릭하세요")
        return

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "트렌드", "시그널", "섹터"])

    with tab1:
        render_overview_tab(overview)
    with tab2:
        render_trend_tab(overview)
    with tab3:
        render_signal_tab(overview)
    with tab4:
        render_sector_tab(overview)


def render_overview_tab(overview):
    """Overview 탭 - 지수 + 브레드스"""

    # 시장 요약
    trend_label = get_trend_label(overview.market_trend)
    score_tooltip = tooltip("trend_score", f"점수: {overview.market_score:+.0f}")

    st.markdown(f'''
    <div class="market-box">
        <div class="market-header">
            <span class="market-title">시장 추세: {trend_label}</span>
            {score_tooltip}
        </div>
        <div class="market-detail">{overview.summary}</div>
    </div>
    ''', unsafe_allow_html=True)

    # 지수 카드
    st.markdown(section_title_with_tooltip("주요 지수 트렌드", "trend_score"), unsafe_allow_html=True)

    if overview.indices:
        cols = st.columns(len(overview.indices))
        for col, idx in zip(cols, overview.indices):
            with col:
                render_index_card(idx)
    else:
        st.info("지수 데이터 없음")

    st.markdown("---")

    # 브레드스
    st.markdown(section_title_with_tooltip("시장 브레드스", "market_breadth"), unsafe_allow_html=True)

    if overview.current_breadth:
        render_breadth_section(overview.current_breadth)
    else:
        st.info("브레드스 데이터 없음")


def render_index_card(idx):
    """지수 카드 렌더링"""
    from analysis.market_overview import TrendStrength

    # 색상 결정
    if idx.trend_score >= 30:
        border_color = "#059669"
        bg_color = "#f0fdf4"
    elif idx.trend_score <= -30:
        border_color = "#dc2626"
        bg_color = "#fef2f2"
    else:
        border_color = "#d97706"
        bg_color = "#fffbeb"

    # 추세 아이콘
    trend_icons = {
        TrendStrength.STRONG_UP: "🔥",
        TrendStrength.MODERATE_UP: "📈",
        TrendStrength.WEAK_UP: "↗",
        TrendStrength.NEUTRAL: "➡",
        TrendStrength.WEAK_DOWN: "↘",
        TrendStrength.MODERATE_DOWN: "📉",
        TrendStrength.STRONG_DOWN: "💧",
    }
    icon = trend_icons.get(idx.trend_strength, "➡")

    st.markdown(f'''
    <div style="background:{bg_color}; border:2px solid {border_color}; border-radius:8px; padding:1rem; text-align:center;">
        <div style="font-size:1.5rem; margin-bottom:0.25rem;">{icon}</div>
        <div style="font-weight:700; font-size:1rem; color:#111827;">{idx.name}</div>
        <div style="font-size:0.8rem; color:#6b7280; margin:0.25rem 0;">{idx.price:,.2f}</div>
        <div style="font-size:0.9rem; font-weight:600; color:{border_color};">{idx.change_1d:+.2f}%</div>
        <div style="margin-top:0.5rem; font-size:0.75rem; color:#6b7280;">
            1W: {idx.return_1w:+.1f}% | 1M: {idx.return_1m:+.1f}%
        </div>
        <div style="font-size:0.7rem; color:#9ca3af; margin-top:0.25rem;">
            추세점수: {idx.trend_score:+.0f}
        </div>
    </div>
    ''', unsafe_allow_html=True)


def render_breadth_section(breadth):
    """브레드스 섹션"""
    col1, col2 = st.columns(2)

    with col1:
        # 상승/하락 비율
        total = breadth.advancing + breadth.declining + breadth.unchanged
        if total > 0:
            adv_pct = breadth.advancing / total * 100
            dec_pct = breadth.declining / total * 100

            st.markdown("**상승/하락**")
            st.progress(adv_pct / 100)
            st.markdown(f'''
            <div style="display:flex; justify-content:space-between; font-size:0.8rem;">
                <span style="color:#059669;">상승 {breadth.advancing} ({adv_pct:.0f}%)</span>
                <span style="color:#dc2626;">하락 {breadth.declining} ({dec_pct:.0f}%)</span>
            </div>
            ''', unsafe_allow_html=True)

            st.markdown("")
            ad_label = f"A/D Ratio: {breadth.advance_decline_ratio:.2f}"
            st.markdown(tooltip("ad_ratio", ad_label), unsafe_allow_html=True)

    with col2:
        # MA 기준
        st.markdown(tooltip("ma200_ratio", "이동평균 상향 비율"), unsafe_allow_html=True)

        metrics = [
            ("MA20↑", breadth.above_ma20_pct),
            ("MA50↑", breadth.above_ma50_pct),
            ("MA200↑", breadth.above_ma200_pct),
        ]

        for label, pct in metrics:
            color = "#059669" if pct >= 50 else "#dc2626"
            st.markdown(f'''
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                <span style="width:60px; font-size:0.8rem;">{label}</span>
                <div style="flex:1; background:#e5e7eb; height:8px; border-radius:4px;">
                    <div style="width:{pct}%; background:{color}; height:100%; border-radius:4px;"></div>
                </div>
                <span style="font-size:0.8rem; color:{color}; width:40px;">{pct:.0f}%</span>
            </div>
            ''', unsafe_allow_html=True)

    st.markdown("---")

    # 신고/신저
    high_tooltip = tooltip("52w_high", "52주 신고가")
    low_tooltip = tooltip("52w_low", "52주 신저가")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f'''
        <div class="metric-box">
            <div class="metric-value" style="color:#059669;">{breadth.new_high_52w}</div>
            <div class="metric-label">{high_tooltip}</div>
        </div>
        ''', unsafe_allow_html=True)
    with col4:
        st.markdown(f'''
        <div class="metric-box">
            <div class="metric-value" style="color:#dc2626;">{breadth.new_low_52w}</div>
            <div class="metric-label">{low_tooltip}</div>
        </div>
        ''', unsafe_allow_html=True)


def render_trend_tab(overview):
    """트렌드 탭 - 추세 강한 종목들"""

    # 상승 추세 vs 하락 추세
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(section_title_with_tooltip("🔥 상승 추세 강한 종목", "trend_score"), unsafe_allow_html=True)
        if overview.trending_up:
            render_trend_list(overview.trending_up, is_positive=True)
        else:
            st.info("해당 종목 없음")

    with col2:
        st.markdown(section_title_with_tooltip("💧 하락 추세 강한 종목", "trend_score"), unsafe_allow_html=True)
        if overview.trending_down:
            render_trend_list(overview.trending_down, is_positive=False)
        else:
            st.info("해당 종목 없음")

    st.markdown("---")

    # 모멘텀 리더 vs 래거드
    col3, col4 = st.columns(2)

    with col3:
        st.markdown(section_title_with_tooltip("📈 1개월 모멘텀 상위", "momentum"), unsafe_allow_html=True)
        if overview.momentum_leaders:
            render_momentum_list(overview.momentum_leaders)
        else:
            st.info("해당 종목 없음")

    with col4:
        st.markdown(section_title_with_tooltip("📉 1개월 모멘텀 하위", "momentum"), unsafe_allow_html=True)
        if overview.momentum_laggards:
            render_momentum_list(overview.momentum_laggards)
        else:
            st.info("해당 종목 없음")


def render_trend_list(items, is_positive=True):
    """추세 종목 리스트"""
    from analysis.market_overview import TrendStrength

    for item in items[:10]:
        color = "#059669" if is_positive else "#dc2626"
        bg = "#f0fdf4" if is_positive else "#fef2f2"

        # MA 상태 표시
        ma_status = []
        if item.above_ma20:
            ma_status.append("MA20↑")
        if item.above_ma50:
            ma_status.append("MA50↑")
        if item.above_ma200:
            ma_status.append("MA200↑")
        ma_str = " ".join(ma_status) if ma_status else "MA↓"

        st.markdown(f'''
        <div style="background:{bg}; border-radius:6px; padding:0.75rem; margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-weight:600; color:#111827;">{item.symbol}</div>
                <div style="font-size:0.75rem; color:#6b7280;">
                    1W: {item.return_1w:+.1f}% | 1M: {item.return_1m:+.1f}% | 3M: {item.return_3m:+.1f}%
                </div>
                <div style="font-size:0.7rem; color:#9ca3af;">{ma_str}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.25rem; font-weight:700; color:{color};">{item.trend_score:+.0f}</div>
                <div style="font-size:0.7rem; color:#6b7280;">추세점수</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)


def render_momentum_list(items):
    """모멘텀 종목 리스트"""
    for item in items[:10]:
        color = "#059669" if item.return_1m >= 0 else "#dc2626"

        st.markdown(f'''
        <div style="background:#f9fafb; border-radius:6px; padding:0.75rem; margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-weight:600; color:#111827;">{item.symbol}</div>
                <div style="font-size:0.75rem; color:#6b7280;">
                    RSI: {item.rsi:.0f} | Vol: {item.volume_ratio:.1f}x
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.1rem; font-weight:700; color:{color};">{item.return_1m:+.1f}%</div>
                <div style="font-size:0.7rem; color:#6b7280;">1개월</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)


def render_signal_tab(overview):
    """시그널 탭 - 기술적 시그널"""
    from analysis.market_overview import TrendSignal

    st.markdown("**시계열 기반 기술적 시그널**")
    st.caption("최근 5일 내 발생한 시그널")

    # 툴팁 미리 생성
    tip_52w_high = tooltip("52w_high", "52주 신고가 돌파")
    tip_golden = tooltip("golden_cross", "골든크로스")
    tip_volume = tooltip("volume_spike", "거래량 급증")
    tip_52w_low = tooltip("52w_low", "52주 신저가 이탈")
    tip_death = tooltip("death_cross", "데드크로스")

    # 2x3 그리드
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"##### 🚀 {tip_52w_high}", unsafe_allow_html=True)
        if overview.breakouts:
            for item in overview.breakouts[:8]:
                st.markdown(f"**{item.symbol}** +{item.return_1m:.1f}% (1M)")
        else:
            st.caption("해당 없음")

    with col2:
        st.markdown(f"##### ⚡ {tip_golden}", unsafe_allow_html=True)
        if overview.golden_crosses:
            for item in overview.golden_crosses[:8]:
                st.markdown(f"**{item.symbol}** +{item.return_1w:.1f}% (1W)")
        else:
            st.caption("해당 없음")

    with col3:
        st.markdown(f"##### 📊 {tip_volume}", unsafe_allow_html=True)
        if overview.volume_spikes:
            for item in overview.volume_spikes[:8]:
                st.markdown(f"**{item.symbol}** {item.volume_ratio:.1f}x")
        else:
            st.caption("해당 없음")

    st.markdown("---")

    col4, col5, col6 = st.columns(3)

    with col4:
        st.markdown(f"##### 🔻 {tip_52w_low}", unsafe_allow_html=True)
        if overview.breakdowns:
            for item in overview.breakdowns[:8]:
                st.markdown(f"**{item.symbol}** {item.return_1m:.1f}% (1M)")
        else:
            st.caption("해당 없음")

    with col5:
        st.markdown(f"##### ☠️ {tip_death}", unsafe_allow_html=True)
        if overview.death_crosses:
            for item in overview.death_crosses[:8]:
                st.markdown(f"**{item.symbol}** {item.return_1w:.1f}% (1W)")
        else:
            st.caption("해당 없음")

    with col6:
        st.markdown("##### 📉 추세 전환 가능")
        # 중립 근처에서 방향 전환 중인 종목
        reversals = [item for item in overview.trending_up[:5] if -20 < item.trend_score < 40 and item.return_1w > 0]
        if reversals:
            for item in reversals[:8]:
                st.markdown(f"**{item.symbol}** 점수: {item.trend_score:+.0f}")
        else:
            st.caption("해당 없음")


def render_sector_tab(overview):
    """섹터 탭 - 섹터 히트맵"""

    if not overview.sectors:
        st.info("섹터 데이터 없음 (미국 시장에서만 지원)")
        return

    st.markdown(section_title_with_tooltip("섹터 트렌드 히트맵", "sector_rotation"), unsafe_allow_html=True)

    # Plotly 트리맵
    try:
        import plotly.express as px

        # 데이터 준비 (소수점 1자리로 반올림)
        data = []
        for s in overview.sectors:
            ret_1m = round(s.return_1m, 1)
            data.append({
                "sector": s.sector,
                "trend_score": round(s.trend_score, 1),
                "return_1m": ret_1m,
                "return_3m": round(s.return_3m, 1),
                "size": abs(s.trend_score) + 10,
                "display_text": f"{s.sector}\n{ret_1m:+.1f}%",
            })

        df = pd.DataFrame(data)

        # 색상 스케일
        fig = px.treemap(
            df,
            path=["sector"],
            values="size",
            color="return_1m",
            color_continuous_scale=["#dc2626", "#fbbf24", "#059669"],
            color_continuous_midpoint=0,
            custom_data=["trend_score", "return_1m", "return_3m"],
        )

        fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[1]:+}%",
            textposition="middle center",
            textfont=dict(size=14),
            hovertemplate="<b>%{label}</b><br>추세점수: %{customdata[0]:+}<br>1M: %{customdata[1]:+}%<br>3M: %{customdata[2]:+}%<extra></extra>",
        )

        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=350,
            coloraxis_showscale=False,
        )

        st.plotly_chart(fig, width="stretch")

    except ImportError:
        st.warning("Plotly가 필요합니다: pip install plotly")

    # 섹터 테이블
    st.markdown("---")
    st.markdown('<div class="section-title">섹터 상세</div>', unsafe_allow_html=True)

    sector_data = []
    for s in overview.sectors:
        color = "#059669" if s.trend_score > 0 else "#dc2626" if s.trend_score < 0 else "#6b7280"
        sector_data.append({
            "섹터": s.sector,
            "추세점수": round(s.trend_score, 1),
            "1W": f"{s.return_1w:+.1f}%",
            "1M": f"{s.return_1m:+.1f}%",
            "3M": f"{s.return_3m:+.1f}%",
            "추세": get_trend_label(s.trend_strength),
        })

    df_sectors = pd.DataFrame(sector_data)

    # 컬러 함수
    def color_trend_score(val):
        if val > 30:
            return 'background-color: #dcfce7; color: #059669'
        elif val > 0:
            return 'background-color: #f0fdf4; color: #059669'
        elif val < -30:
            return 'background-color: #fee2e2; color: #dc2626'
        elif val < 0:
            return 'background-color: #fef2f2; color: #dc2626'
        return ''

    styled = df_sectors.style.map(color_trend_score, subset=['추세점수'])
    st.dataframe(styled, width="stretch", hide_index=True)


def get_trend_label(trend_strength):
    """추세 강도 라벨"""
    from analysis.market_overview import TrendStrength

    labels = {
        TrendStrength.STRONG_UP: "🔥 강한 상승",
        TrendStrength.MODERATE_UP: "📈 상승",
        TrendStrength.WEAK_UP: "↗ 약한 상승",
        TrendStrength.NEUTRAL: "➡ 횡보",
        TrendStrength.WEAK_DOWN: "↘ 약한 하락",
        TrendStrength.MODERATE_DOWN: "📉 하락",
        TrendStrength.STRONG_DOWN: "💧 강한 하락",
    }
    return labels.get(trend_strength, "중립")


# === TA 스크리너 페이지 ===

def render_ta_screener_page():
    """기술적 분석 패턴 스크리너 페이지"""
    st.markdown("## 🔬 TA 패턴 스크리너")

    # 탭 선택
    tab1, tab2 = st.tabs(["🎯 컨플루언스 스크리너", "📊 개별 패턴 스크리너"])

    with tab1:
        _render_confluence_tab()

    with tab2:
        _render_pattern_tab()


def _render_confluence_guide():
    """컨플루언스 스크리너 가이드"""
    with st.expander("📖 용어 설명 및 해석 가이드", expanded=False):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 점수 시스템", "🎯 시그널 해석", "🌍 컨텍스트", "📍 용어 사전", "💡 활용 팁"])

        with tab1:
            st.markdown("""
### 점수 시스템 (총 100점)

컨플루언스 점수는 5개 항목의 합계에서 위험 페널티를 뺀 값입니다.

| 항목 | 최대 점수 | 설명 |
|------|----------|------|
| **존 접근** | 20점 | 현재가가 POI(존)에 얼마나 가까운지 |
| **존 품질** | 25점 | 존 자체의 신뢰도 (등급, 골든존, CHOCH 등) |
| **트리거 캔들** | 20점 | 반전 확인 캔들 강도 (IBFB > PIN/ENG > DOJI) |
| **추가 확인** | 25점 | Price Action, Double Pattern, Liquidity 시그널 |
| **HTF 정렬** | 10점 | 상위 타임프레임 추세와 일치 여부 |
| **위험 페널티** | -10점 | 반대 존이 가까울 경우 감점 |

---

#### 등급 기준
- **S등급 (75점+)**: 최상의 셋업, 높은 확률
- **A등급 (60-74점)**: 좋은 셋업, 신뢰 가능
- **B등급 (45-59점)**: 보통 셋업, 추가 확인 권장
- **C등급 (45점 미만)**: 약한 셋업, 주의 필요
            """)

        with tab2:
            st.markdown("""
### 시그널 상태

| 상태 | 아이콘 | 의미 | 액션 |
|------|--------|------|------|
| **GO** | 🔥 / ✓ | 존 진입 + 트리거 확인 완료 | 진입 고려 가능 |
| **WAIT** | ⏳ | 존 근처, 트리거 대기 중 | 트리거 캔들 출현 대기 |
| **NONE** | - | 존 접근 중 (아직 멀음) | 관찰 |

---

### 트리거 캔들 강도

트리거 캔들은 반전을 확인하는 캔들 패턴입니다.

| 트리거 | 강도 | 점수 | 설명 |
|--------|------|------|------|
| **◆ IBFB** | 최강 | 20점 | Inside Bar False Breakout - 가장 강력한 반전 신호 |
| **▲ PIN** | 강 | 15점 | 핀바/해머 - 긴 꼬리로 거부 신호 |
| **▲ ENG** | 강 | 15점 | 잉걸핑 - 이전 캔들을 완전히 감싸는 반전 |
| **● DOJI** | 약 | 8점 | 도지 후 확인봉 - 방향 전환 힌트 |

---

### 추가 확인 시그널

| 카테고리 | 패턴 | 점수 | 설명 |
|----------|------|------|------|
| **[PA]** | 핀바, 잉걸핑, 스타, 삼병 | 5~10점 | Price Action 패턴 |
| **[DP]** | 쌍바닥, 쌍봉 | 8~12점 | Double Bottom/Top 패턴 |
| **[LIQ]** | 유동성 스윕 | 10~15점 | 스탑헌팅 후 반전 |
            """)

        with tab3:
            st.markdown("""
### 🌍 컨텍스트 분석 (신규)

컨텍스트 분석은 **장기적인 시장 환경**을 평가하여 애매한 종목을 걸러냅니다.

---

#### 1. 장기 추세 (Weekly Trend)
주봉 기준 추세를 분석합니다.

| 아이콘 | 상태 | 설명 |
|--------|------|------|
| 📈📈 | 강한 상승 | MA 상승 + HH/HL 패턴 |
| 📈 | 상승 | MA 위, 상승 구조 |
| ➡️ | 횡보 | 방향성 없음 |
| 📉 | 하락 | MA 아래, 하락 구조 |
| 📉📉 | 강한 하락 | MA 하락 + LH/LL 패턴 |

**⚠️ 주의**: 하락 추세에서 롱, 상승 추세에서 숏은 위험합니다.

---

#### 2. 박스권 감지 (Range Bound)
장기 횡보 구간을 감지합니다.

| 아이콘 | 의미 |
|--------|------|
| 📦 | 박스권 (60일+) |

- **박스권 특징**: 방향성 없이 상하 반복
- **위험**: 돌파 실패 가능성, 추세 매매 비효율
- **필터**: "박스권 제외" 옵션으로 필터링 가능

---

#### 3. 하락폭/위치 (Drawdown)
고점 대비 현재 위치를 분석합니다.

| 하락폭 | 의미 | 위험 |
|--------|------|------|
| -10% 미만 | 고점 근처 | 낮음 |
| -10~25% | 조정 구간 | 보통 |
| -25~40% | 큰 조정 | 높음 (매물대 존재) |
| -40% 이상 | 급락 | 매우 높음 |

**⚠️ 주의**: 큰 하락 후 반등 시 위에 매물대가 많아 상승이 어려울 수 있습니다.

---

#### 4. 저항 밀집도 (Resistance Density)
Entry부터 TP까지 경로에 있는 저항 개수입니다.

| 아이콘 | 밀집도 | 의미 |
|--------|--------|------|
| 🧱3 | 높음 | TP까지 저항 3개 이상 |
| 🧱1 | 낮음 | 저항 적음, 상승 여력 |

---

#### 컨텍스트 등급 (CTX)
종합적인 시장 환경 평가입니다.

| 등급 | 점수 | 의미 |
|------|------|------|
| **S** | 70+ | 최적의 환경 |
| **A** | 55-69 | 좋은 환경 |
| **B** | 40-54 | 보통 (주의 필요) |
| **C** | 40 미만 | 불리한 환경 |

**권장**: 점수가 높아도 CTX가 C면 재검토하세요.
            """)

        with tab4:
            st.markdown("""
### 핵심 용어 사전

#### POI (Point of Interest)
가격이 반응할 가능성이 높은 핵심 가격대. Order Block이나 Supply/Demand Zone이 해당됩니다.

#### Order Block (오더블록)
기관의 대량 주문이 발생한 것으로 추정되는 영역. 가격이 돌아올 때 지지/저항으로 작용합니다.
- **Bullish OB**: 상승 전 마지막 하락 캔들 영역 → 지지 역할
- **Bearish OB**: 하락 전 마지막 상승 캔들 영역 → 저항 역할

#### 골든존 (Golden Zone)
피보나치 되돌림의 핵심 영역 (38.2% ~ 61.8%). 존이 이 영역과 겹치면 신뢰도가 높아집니다.
- **Lv3 (61.8%)**: 최적의 되돌림, 가장 높은 신뢰도
- **Lv2 (50%)**: 좋은 되돌림
- **Lv1 (38.2%)**: 얕은 되돌림

#### CHOCH (Change of Character)
시장 구조의 변화. 상승 추세에서 저점이 깨지거나, 하락 추세에서 고점이 깨지는 것.
CHOCH와 함께 형성된 존은 더 강력한 반전 신호입니다.

#### BOS (Break of Structure)
기존 추세의 연장. 상승 추세에서 고점 갱신, 하락 추세에서 저점 갱신.

#### IBFB (Inside Bar False Breakout)
Inside Bar(전봉 범위 안에 있는 봉) 형성 후, 한쪽으로 가짜 돌파 후 반대로 마감.
가장 강력한 반전 신호 중 하나입니다.

#### 유동성 스윕 (Liquidity Sweep)
이전 고점/저점을 일시적으로 돌파한 뒤 빠르게 되돌아오는 움직임.
스탑로스를 청산시킨 후 진짜 방향으로 움직이는 기관의 전형적인 패턴입니다.

#### HTF 정렬 (Higher Timeframe Alignment)
상위 타임프레임의 추세와 현재 시그널 방향이 일치하는지 여부.
MA50 위에서 롱, MA50 아래에서 숏이 정렬된 것으로 판단합니다.

#### 미터치 존 (Fresh Zone)
가격이 아직 한 번도 터치하지 않은 존. 첫 터치에서 더 강한 반응이 예상됩니다.
            """)

        with tab5:
            st.markdown("""
### 활용 팁

#### 1. 높은 점수 시그널 우선
- **70점 이상**: 높은 확률의 셋업, 적극적 진입 고려
- **50-70점**: 괜찮은 셋업, 추가 확인 후 진입
- **50점 미만**: 약한 셋업, 관망 또는 소량 진입

#### 2. GO vs WAIT 활용
- **GO 시그널**: 바로 진입 검토 가능
- **WAIT 시그널**: 워치리스트에 추가하고 트리거 대기

#### 3. 컨플루언스 확인
여러 확인 시그널이 겹칠수록 신뢰도가 높아집니다:
- 존 진입 + IBFB + Liquidity Sweep = 최고 조합
- 존 진입 + Double Bottom + HTF 정렬 = 강력한 조합

#### 4. 위험 관리
- **⚠️ 표시**: 반대 존이 가까워 수익 실현이 제한될 수 있음
- 항상 제시된 SL(손절가) 준수
- TP1에서 일부 수익 실현 권장

#### 5. 시간대 고려
- 일봉 기준 스크리닝이므로 스윙 트레이딩에 적합
- 단타(데이트레이딩)는 더 낮은 타임프레임 확인 필요

#### 6. 추천 워크플로우
1. **스캔**: 전체 유니버스 스캔
2. **필터**: GO 시그널 또는 60점 이상 필터
3. **검토**: 상세 분석에서 점수 구성 확인
4. **차트 확인**: 실제 차트에서 시각적 검증
5. **진입 결정**: 리스크/리워드 비율 검토 후 결정
            """)


def _render_confluence_tab():
    """컨플루언스 기반 스크리너 탭 v2"""
    st.caption("POI(Order Block) 접근 + 확인 캔들(IBFB/PIN/ENG) 조합으로 스크리닝")

    from analysis.confluence_screener import ConfluenceScreener, ConfluenceConfig, SignalState
    from analysis.patterns.price_action import PatternDirection
    from data.data_layer import get_data_layer_manager

    # 가이드
    _render_confluence_guide()

    # 설정 - 레이아웃 개선
    with st.expander("스크리닝 설정", expanded=True):
        # 첫 번째 행: 기본 필터 (슬라이더들)
        st.markdown('<p style="font-size:0.75rem; color:var(--text-muted); margin-bottom:0.5rem;">기본 필터</p>', unsafe_allow_html=True)
        row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)

        with row1_col1:
            max_dist = st.slider("최대 거리 (%)", 1.0, 10.0, 5.0, 0.5, key="cf_max_dist")
        with row1_col2:
            min_score = st.slider("최소 총점", 20, 80, 35, 5, key="cf_min_score")
        with row1_col3:
            min_grade = st.selectbox("최소 존 등급", ["C", "B", "A", "S"], index=0, key="cf_min_grade")
        with row1_col4:
            direction = st.radio(
                "방향",
                ["전체", "롱", "숏"],
                horizontal=True,
                key="cf_direction"
            )
            direction_map = {"전체": "all", "롱": "long", "숏": "short"}

        st.markdown("---")

        # 두 번째 행: 체크박스 필터들
        st.markdown('<p style="font-size:0.75rem; color:var(--text-muted); margin-bottom:0.5rem;">상세 필터</p>', unsafe_allow_html=True)
        row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)

        with row2_col1:
            only_fresh = st.checkbox("미터치 존만", value=False, key="cf_fresh")
            only_golden = st.checkbox("골든존만", value=False, key="cf_golden")

        with row2_col2:
            require_trigger = st.checkbox("GO 시그널만", value=False, key="cf_require_trigger", help="트리거 캔들 확인된 시그널만")
            use_htf = st.checkbox("HTF 정렬 필터", value=True, key="cf_htf")

        with row2_col3:
            use_context = st.checkbox("컨텍스트 분석", value=True, key="cf_use_context", help="장기추세, 매물대, 박스권, 하락폭 분석")
            exclude_range = st.checkbox("박스권 제외", value=False, key="cf_exclude_range")

        with row2_col4:
            exclude_drawdown = st.checkbox("급락 종목 제외", value=False, key="cf_exclude_dd", help="고점 대비 30% 이상 하락")
            exclude_dense = st.checkbox("저항 밀집 제외", value=False, key="cf_exclude_dense")

    # 유니버스 선택
    st.markdown("---")
    from data.universe import get_universe_manager, Universe, Market, UNIVERSE_INFO

    um = get_universe_manager()

    col_u1, col_u2 = st.columns([3, 1])

    with col_u1:
        # 시장 선택
        market_options = {
            "🇺🇸 미국": Market.US,
            "🇰🇷 한국": Market.KOREA,
            "₿ 크립토": Market.CRYPTO,
        }
        selected_market = st.radio("시장", list(market_options.keys()), horizontal=True, key="cf_market")
        market = market_options[selected_market]

    with col_u2:
        lookback = st.selectbox("확인 시그널 범위", ["최근 5봉", "최근 10봉", "최근 20봉"], index=1, key="cf_lookback")
        lookback_bars = {"최근 5봉": 5, "최근 10봉": 10, "최근 20봉": 20}[lookback]

    # 시장별 유니버스 옵션
    universe_options = {
        Market.US: {
            "S&P 500 (전체 ~500)": Universe.SP500,
            "NASDAQ 100 (전체 ~100)": Universe.NASDAQ100,
            "Dow Jones 30": Universe.DOW30,
            "Russell 2000 (상위 50)": Universe.RUSSELL2000,
            "직접 입력": None,
        },
        Market.KOREA: {
            "KOSPI 200": Universe.KOSPI200,
            "KOSDAQ 150": Universe.KOSDAQ150,
            "KOSPI 전체": Universe.KOSPI_ALL,
            "KOSDAQ 전체": Universe.KOSDAQ_ALL,
            "직접 입력": None,
        },
        Market.CRYPTO: {
            "Crypto Top 100": Universe.CRYPTO_TOP100,
            "Crypto Top 50": Universe.CRYPTO_TOP50,
            "직접 입력": None,
        },
    }

    col_v1, col_v2, col_v3 = st.columns([2, 1, 1])

    with col_v1:
        options = universe_options[market]
        universe_choice = st.selectbox("유니버스", list(options.keys()), key="cf_universe_choice")
        selected_universe = options[universe_choice]

    with col_v2:
        # 종목 수 제한 (대량 스캔 시 속도 조절)
        limit_options = {
            "전체": None,
            "상위 50개": 50,
            "상위 100개": 100,
            "상위 200개": 200,
        }
        limit_choice = st.selectbox("종목 수 제한", list(limit_options.keys()), key="cf_limit")
        symbol_limit = limit_options[limit_choice]

    with col_v3:
        workers = st.selectbox("병렬 처리", [3, 5, 10], index=1, key="cf_workers")

    # 종목 리스트 가져오기
    if selected_universe is None:  # 직접 입력
        default_symbols = "AAPL, MSFT, GOOGL, AMZN, NVDA"
        if market == Market.KOREA:
            default_symbols = "005930.KS, 000660.KS, 373220.KS"
        elif market == Market.CRYPTO:
            default_symbols = "BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT"

        symbols_input = st.text_area(
            "종목 심볼 (쉼표로 구분)",
            value=default_symbols,
            key="cf_symbols_input"
        )
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    else:
        # 유니버스에서 종목 가져오기 (캐시 사용)
        with st.spinner(f"{universe_choice} 종목 로딩 중..."):
            symbols = um.get_symbols(selected_universe, limit=symbol_limit)

    st.caption(f"총 {len(symbols)}개 종목 스캔 예정")

    # 스캔 실행
    if st.button("🎯 컨플루언스 스캔 실행", type="primary", width="stretch"):
        config = ConfluenceConfig(
            max_distance_pct=max_dist,
            min_zone_grade=min_grade,
            min_total_score=min_score,
            direction_filter=direction_map[direction],
            only_fresh_zones=only_fresh,
            only_golden_zones=only_golden,
            require_trigger=require_trigger,
            use_htf_filter=use_htf,
            lookback_bars=lookback_bars,
            # 컨텍스트 필터
            use_context_filter=use_context,
            exclude_range_bound=exclude_range,
            exclude_high_drawdown=exclude_drawdown,
            exclude_dense_resistance=exclude_dense,
        )

        screener = ConfluenceScreener(config)

        def data_fetcher(symbol):
            return fetch_ohlcv_cached(symbol, days=180)

        progress = st.progress(0)
        status = st.empty()

        def update_progress(current, total, symbol, stat):
            progress.progress(current / total)
            status.text(f"스캔 중: {symbol} ({current}/{total}) - {stat}")

        with st.spinner("컨플루언스 스캔 중..."):
            signals = screener.screen_universe(
                symbols=symbols,
                data_fetcher=data_fetcher,
                workers=workers,
                progress_callback=update_progress,
            )

        progress.empty()
        status.empty()

        st.session_state["cf_signals"] = signals
        st.session_state["cf_summary"] = screener.get_summary(signals)

    # 결과 표시
    if "cf_signals" in st.session_state and st.session_state["cf_signals"]:
        signals = st.session_state["cf_signals"]
        summary = st.session_state.get("cf_summary", {})

        st.markdown("### 스캔 결과")

        # 요약 메트릭
        mcols = st.columns(6)
        mcols[0].metric("🔥 GO 시그널", f"{summary.get('go_signals', 0)}개", help="존+트리거 확인 완료")
        mcols[1].metric("⏳ WAIT 시그널", f"{summary.get('wait_signals', 0)}개", help="존 진입, 트리거 대기")
        mcols[2].metric("🟢 롱", f"{summary.get('long_signals', 0)}개")
        mcols[3].metric("🔴 숏", f"{summary.get('short_signals', 0)}개")
        mcols[4].metric("평균 점수", f"{summary.get('avg_score', 0):.0f}점")
        mcols[5].metric("최고 점수", f"{summary.get('top_score', 0):.0f}점")

        st.markdown("---")

        # 간결한 요약
        grade_dist = summary.get("grade_distribution", {})
        grade_text = f"S:{grade_dist.get('S', 0)} A:{grade_dist.get('A', 0)} B:{grade_dist.get('B', 0)} C:{grade_dist.get('C', 0)}"
        st.markdown(f"**{len(signals)}개 시그널** · {grade_text}")

        st.markdown("---")

        # 전체 데이터 (상단, 접힌 상태)
        _render_confluence_full_data(signals)

        # 2단 레이아웃
        col_list, col_detail = st.columns([1, 2])
        with col_list:
            _render_confluence_table(signals)
        with col_detail:
            _render_confluence_detail(signals)

    elif "cf_signals" in st.session_state:
        st.info("조건에 맞는 시그널이 없습니다. 필터를 완화해보세요.")


def _render_confluence_table(signals):
    """컨플루언스 시그널 테이블 - 깔끔한 디자인"""
    from analysis.patterns.price_action import PatternDirection
    from analysis.confluence_screener import SignalState
    from data.universe import get_stock_name

    if not signals:
        return

    # 종목별로 그룹화 (최고 점수 시그널만)
    stock_best = {}
    for sig in signals:
        symbol = sig.symbol
        if symbol not in stock_best or sig.total_score > stock_best[symbol].total_score:
            stock_best[symbol] = sig

    # 점수순 정렬
    sorted_signals = sorted(stock_best.values(), key=lambda x: x.total_score, reverse=True)

    # GO/WAIT 분리
    go_signals = [s for s in sorted_signals if s.state == SignalState.GO]
    wait_signals = [s for s in sorted_signals if s.state == SignalState.WAIT]

    def render_signal_list(sigs, prefix):
        for i, sig in enumerate(sigs):
            stock_name = get_stock_name(sig.symbol)
            display_name = stock_name if stock_name != sig.symbol else sig.symbol
            is_bullish = sig.direction == PatternDirection.BULLISH
            dir_label = "L" if is_bullish else "S"
            dir_color = "#22c55e" if is_bullish else "#ef4444"

            # 컴팩트한 행
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:8px; padding:6px 0;">
                    <span style="background:{dir_color}; color:white; padding:2px 6px; border-radius:3px; font-size:11px; font-weight:600;">{dir_label}</span>
                    <span style="font-weight:500;">{display_name}</span>
                    <span style="color:#9ca3af; font-size:12px;">{sig.poi.grade}</span>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button(f"{sig.total_score}점", key=f"{prefix}_{i}", width="stretch"):
                    st.session_state["cf_selected_symbol"] = sig.symbol
                    st.rerun()

    # GO 시그널
    if go_signals:
        st.markdown(f"**진입 가능** ({len(go_signals)})")
        render_signal_list(go_signals, "cf_go")

    # WAIT 시그널
    if wait_signals:
        st.markdown(f"**대기** ({len(wait_signals)})")
        render_signal_list(wait_signals, "cf_wait")


def _render_confluence_full_data(signals):
    """전체 데이터 테이블 (전체 너비, 상세 정보 포함)"""
    from analysis.patterns.price_action import PatternDirection
    from analysis.confluence_screener import SignalState, TrendDirection, MarketRegime
    from data.universe import get_stock_name

    with st.expander("전체 데이터", expanded=False):
        rows = []
        for sig in signals:
            stock_name = get_stock_name(sig.symbol)
            display_name = stock_name if stock_name != sig.symbol else sig.symbol

            # 아이콘
            state_icon = "🔥" if sig.state == SignalState.GO else "⏳"
            dir_icon = "🟢" if sig.direction == PatternDirection.BULLISH else "🔴"
            golden_text = f"Lv{sig.poi.golden_level}" if sig.poi.is_golden else "-"

            # 확인 시그널 요약
            conf_summary = sig.confirmation_summary if hasattr(sig, 'confirmation_summary') else "-"

            # 컨텍스트 요약
            ctx_text = "-"
            ctx_grade = "-"
            if sig.context:
                ctx_grade = sig.context.context_grade
                parts = []
                trend_icons = {
                    TrendDirection.STRONG_UP: "📈📈",
                    TrendDirection.UP: "📈",
                    TrendDirection.NEUTRAL: "➡️",
                    TrendDirection.DOWN: "📉",
                    TrendDirection.STRONG_DOWN: "📉📉",
                }
                parts.append(trend_icons.get(sig.context.weekly_trend, "?"))
                if sig.context.market_regime == MarketRegime.RANGE_BOUND:
                    parts.append("📦")
                if sig.context.drawdown_from_high > 25:
                    parts.append(f"-{sig.context.drawdown_from_high:.0f}%")
                ctx_text = "".join(parts)

            rows.append({
                "": f"{state_icon}{dir_icon}",
                "종목": display_name,
                "존": sig.poi.grade,
                "골든": golden_text,
                "거리": f"{sig.distance_to_zone_pct:.1f}%",
                "트리거": sig.trigger_label if sig.trigger_label else "-",
                "확인": conf_summary,
                "점수": sig.total_score,
                "등급": sig.grade,
                "CTX": f"{ctx_text} {ctx_grade}",
                "Entry": format_price(sig.entry_price, sig.symbol),
                "TP1": format_price(sig.take_profit_1, sig.symbol),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("CSV 다운로드", csv, "confluence_signals.csv", "text/csv", key="dl_cf_csv")


def _render_confluence_detail(signals):
    """컨플루언스 상세 분석 - 깔끔한 디자인"""
    from analysis.patterns.price_action import PatternDirection
    from analysis.confluence_screener import SignalState
    from data.universe import get_stock_name, get_symbol_with_name

    if not signals:
        return

    # 종목 선택
    symbol_list = list(set([s.symbol for s in signals]))
    symbol_options = {get_symbol_with_name(s): s for s in symbol_list}
    display_options = list(symbol_options.keys())

    pre_selected = st.session_state.get("cf_selected_symbol")
    default_idx = 0
    if pre_selected and pre_selected in symbol_list:
        for i, opt in enumerate(display_options):
            if symbol_options[opt] == pre_selected:
                default_idx = i
                break

    selected_display = st.selectbox("종목 선택", display_options, index=default_idx, key="cf_detail_symbol_v3")
    selected = symbol_options[selected_display]
    st.session_state["cf_selected_symbol"] = selected

    symbol_signals = [s for s in signals if s.symbol == selected]
    is_kr = is_korean_stock(selected)

    for idx, sig in enumerate(symbol_signals):
        is_long = sig.direction == PatternDirection.BULLISH
        dir_color = "#22c55e" if is_long else "#ef4444"
        dir_label = "LONG" if is_long else "SHORT"
        state_label = "GO" if sig.state == SignalState.GO else "WAIT"
        state_color = "#f97316" if sig.state == SignalState.GO else "#6b7280"

        # 헤더: 방향 + 상태 + 점수
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; margin:16px 0 12px 0;">
            <span style="background:{dir_color}; color:white; padding:4px 12px; border-radius:4px; font-weight:600;">{dir_label}</span>
            <span style="background:{state_color}; color:white; padding:4px 8px; border-radius:4px; font-size:12px;">{state_label}</span>
            <span style="font-size:18px; font-weight:600;">{sig.total_score}점</span>
            <span style="color:#6b7280; font-size:13px;">{sig.grade}</span>
        </div>
        """, unsafe_allow_html=True)

        # 가격 정보 (2x3 그리드)
        st.markdown("""<style>
        .cf-grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; margin:8px 0; }
        .cf-box { background:#f8fafc; padding:10px 12px; border-radius:6px; }
        .cf-label { font-size:11px; color:#6b7280; }
        .cf-value { font-size:14px; font-weight:600; }
        </style>""", unsafe_allow_html=True)

        entry_str = format_price(sig.entry_price, is_korean=is_kr)
        sl_str = format_price(sig.stop_loss, is_korean=is_kr)
        tp1_str = format_price(sig.take_profit_1, is_korean=is_kr)
        tp2_str = format_price(sig.take_profit_2, is_korean=is_kr)
        current_str = format_price(sig.current_price, is_korean=is_kr)

        st.markdown(f"""
        <div class="cf-grid">
            <div class="cf-box"><div class="cf-label">현재가</div><div class="cf-value">{current_str}</div></div>
            <div class="cf-box"><div class="cf-label">Entry</div><div class="cf-value">{entry_str}</div></div>
            <div class="cf-box"><div class="cf-label">Stop Loss</div><div class="cf-value" style="color:#ef4444;">{sl_str}</div></div>
            <div class="cf-box"><div class="cf-label">TP1 (1:1.5)</div><div class="cf-value" style="color:#22c55e;">{tp1_str}</div></div>
            <div class="cf-box"><div class="cf-label">TP2 (1:2.5)</div><div class="cf-value" style="color:#22c55e;">{tp2_str}</div></div>
            <div class="cf-box"><div class="cf-label">존 거리</div><div class="cf-value">{sig.distance_to_zone_pct:.1f}%</div></div>
        </div>
        """, unsafe_allow_html=True)

        # POI + 트리거 요약 (한 줄)
        poi_info = f"{sig.poi.poi_type.value} {sig.poi.grade}"
        if sig.poi.is_golden:
            poi_info += f" · Golden Lv{sig.poi.golden_level}"
        trigger_info = sig.trigger.trigger_type.upper() if sig.trigger else "대기중"

        st.markdown(f"""
        <div style="display:flex; gap:20px; font-size:13px; color:#4b5563; margin:8px 0;">
            <span><b>POI:</b> {poi_info}</span>
            <span><b>트리거:</b> {trigger_info}</span>
        </div>
        """, unsafe_allow_html=True)

        # 점수 breakdown (접기)
        with st.expander("점수 상세"):
            score_data = {
                "항목": ["존 접근", "존 품질", "트리거", "추가확인", "HTF정렬", "페널티"],
                "점수": [sig.zone_proximity_score, sig.zone_quality_score, sig.trigger_score,
                       sig.confirmation_score, sig.htf_alignment_score, sig.risk_penalty]
            }
            st.dataframe(pd.DataFrame(score_data), width="stretch", hide_index=True)

            # 확인 시그널
            if sig.confirmations:
                conf_text = ", ".join([f"{c.pattern_type}(+{c.score})" for c in sig.confirmations])
                st.caption(f"확인: {conf_text}")

        # 컨텍스트 (접기)
        if sig.context:
            from analysis.confluence_screener import TrendDirection, MarketRegime
            ctx = sig.context
            with st.expander(f"컨텍스트 ({ctx.context_grade})"):
                trend_map = {TrendDirection.STRONG_UP: "강한상승", TrendDirection.UP: "상승",
                           TrendDirection.NEUTRAL: "횡보", TrendDirection.DOWN: "하락",
                           TrendDirection.STRONG_DOWN: "강한하락"}
                regime_map = {MarketRegime.TRENDING_UP: "상승추세", MarketRegime.TRENDING_DOWN: "하락추세",
                            MarketRegime.RANGE_BOUND: "박스권", MarketRegime.VOLATILE: "고변동"}
                st.caption(f"추세: {trend_map.get(ctx.weekly_trend, '?')} | 레짐: {regime_map.get(ctx.market_regime, '?')} | 고점대비: -{ctx.drawdown_from_high:.1f}%")
                if ctx.warnings:
                    for w in ctx.warnings:
                        st.caption(f"⚠ {w}")

        # 차트 버튼
        if st.button("차트 보기", key=f"cf_chart_{selected}_{idx}"):
            st.session_state["chart_signal_data"] = {
                "symbol": selected,
                "direction": "bullish" if is_long else "bearish",
                "zone_high": sig.poi.top if sig.poi else None,
                "zone_low": sig.poi.bottom if sig.poi else None,
                "entry_price": sig.entry_price,
                "stop_loss": sig.stop_loss,
                "take_profit_1": sig.take_profit_1,
                "take_profit_2": sig.take_profit_2,
                "pattern_type": sig.poi.poi_type.value if sig.poi else "POI",
            }
            st.session_state["chart_symbol"] = selected
            st.session_state["_nav_to"] = "📈 차트"
            st.rerun()

        if idx < len(symbol_signals) - 1:
            st.markdown("<hr style='margin:16px 0; border:none; border-top:1px solid #e5e7eb;'>", unsafe_allow_html=True)


def _render_pattern_tab():
    """개별 패턴 스크리너 탭 (기존 기능)"""
    st.caption("Price Action, SMC, Double Pattern, Liquidity Sweep 개별 패턴 스크리닝")

    from analysis.ta_screener import TAScreener, ScreenerConfig
    from analysis.patterns.price_action import PatternDirection, PatternStrength
    from data.data_layer import get_data_layer_manager

    # 필터 설정
    with st.expander("스크리닝 설정", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**패턴 선택**")
            enable_pa = st.checkbox("Price Action", value=True, key="ta_pa")
            enable_smc = st.checkbox("SMC (Order Block)", value=True, key="ta_smc")
            enable_dp = st.checkbox("Double Pattern", value=True, key="ta_dp")
            enable_liq = st.checkbox("Liquidity Sweep", value=True, key="ta_liq")

        with col2:
            st.markdown("**방향 필터**")
            direction = st.radio(
                "방향",
                ["전체", "롱 (매수)", "숏 (매도)"],
                horizontal=False,
                label_visibility="collapsed",
                key="ta_direction"
            )
            direction_map = {"전체": "all", "롱 (매수)": "long", "숏 (매도)": "short"}

        with col3:
            st.markdown("**신뢰도**")
            min_conf = st.slider("최소 신뢰도", 30, 90, 50, 5, key="ta_conf")
            st.caption(f"현재: {min_conf}% 이상")

        with col4:
            st.markdown("**RR 비율**")
            min_rr = st.slider("최소 RR", 0.5, 3.0, 1.0, 0.5, key="ta_rr")
            st.caption(f"현재: 1:{min_rr:.1f} 이상")

        # Price Action 세부 설정
        if enable_pa:
            st.markdown("---")
            st.markdown("**Price Action 패턴**")
            pa_cols = st.columns(4)
            pa_patterns = []
            if pa_cols[0].checkbox("핀바 (Pinbar)", value=True, key="ta_pinbar"):
                pa_patterns.append("pinbar")
            if pa_cols[1].checkbox("잉걸핑 (Engulfing)", value=True, key="ta_engulfing"):
                pa_patterns.append("engulfing")
            if pa_cols[2].checkbox("스타 (Star)", value=True, key="ta_star"):
                pa_patterns.append("star")
            if pa_cols[3].checkbox("삼병 (Three Soldiers)", value=True, key="ta_soldiers"):
                pa_patterns.append("three_soldiers")

    # 유니버스 선택
    st.markdown("---")
    col_uni1, col_uni2, col_uni3 = st.columns([2, 1, 1])

    with col_uni1:
        universe_type = st.selectbox(
            "유니버스",
            ["S&P 500 주요 종목", "NASDAQ 100", "직접 입력"],
            key="ta_universe"
        )

    with col_uni2:
        lookback = st.selectbox("검색 범위", ["최근 5봉", "최근 10봉", "최근 20봉"], index=1, key="ta_lookback")
        lookback_bars = {"최근 5봉": 5, "최근 10봉": 10, "최근 20봉": 20}[lookback]

    with col_uni3:
        workers = st.selectbox("병렬 처리", [3, 5, 10], index=1, key="ta_workers")

    # 직접 입력 시
    if universe_type == "직접 입력":
        symbols_input = st.text_area(
            "종목 심볼 (쉼표로 구분)",
            value="AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA",
            key="ta_symbols_input"
        )
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    else:
        # 기본 종목 리스트
        sp500_top = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
                     "V", "XOM", "JPM", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "PEP",
                     "KO", "COST", "AVGO", "LLY", "WMT", "MCD", "CSCO", "TMO", "ABT", "ACN"]
        nasdaq_top = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "PEP",
                      "ADBE", "CMCSA", "NFLX", "CSCO", "AMD", "INTC", "QCOM", "TXN", "INTU", "AMGN",
                      "HON", "AMAT", "SBUX", "ISRG", "BKNG", "ADI", "GILD", "MDLZ", "VRTX", "REGN"]
        symbols = sp500_top if universe_type == "S&P 500 주요 종목" else nasdaq_top

    st.caption(f"총 {len(symbols)}개 종목 스캔 예정")

    # 스크리닝 실행 버튼
    if st.button("🔍 패턴 스캔 실행", type="primary", width="stretch"):
        # 설정 생성
        config = ScreenerConfig(
            enable_price_action=enable_pa,
            enable_smc=enable_smc,
            enable_double_patterns=enable_dp,
            enable_liquidity=enable_liq,
            pa_patterns=pa_patterns if enable_pa else [],
            min_confidence=min_conf,
            min_rr_ratio=min_rr,
            direction_filter=direction_map[direction],
            lookback_bars=lookback_bars,
        )

        screener = TAScreener(config)
        dlm = get_data_layer_manager()

        def data_fetcher(symbol):
            return dlm.get_data(symbol, days=180, with_indicators=True)

        # 진행률 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_placeholder = st.empty()

        def update_progress(current, total, symbol, status):
            progress_bar.progress(current / total)
            status_text.text(f"스캔 중: {symbol} ({current}/{total}) - {status}")

        # 스크리닝 실행
        with st.spinner("패턴 스캔 중..."):
            results = screener.screen_universe(
                symbols=symbols,
                data_fetcher=data_fetcher,
                workers=workers,
                progress_callback=update_progress,
            )

        progress_bar.empty()
        status_text.empty()

        # 결과 저장
        st.session_state["ta_results"] = results
        st.session_state["ta_summary"] = screener.get_summary(results)

    # 결과 표시
    if "ta_results" in st.session_state and st.session_state["ta_results"]:
        results = st.session_state["ta_results"]
        summary = st.session_state.get("ta_summary", {})

        # 간결한 요약
        total = summary.get('total_signals', 0)
        longs = summary.get('long_signals', 0)
        shorts = summary.get('short_signals', 0)
        st.markdown(f"**{len(results)}개 종목** · {total}개 시그널 (Long {longs} / Short {shorts})")

        st.markdown("---")

        # 전체 데이터 (상단, 접힌 상태)
        _render_ta_full_data(results)

        # 2단 레이아웃: 좌측 종목 선택, 우측 상세
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            _render_ta_signals_table(results)

        with col_detail:
            _render_ta_detail_view(results)

    elif "ta_results" in st.session_state:
        st.info("시그널이 발견되지 않았습니다. 필터 조건을 완화해보세요.")


def _render_ta_signals_table(results):
    """시그널 테이블 - 심플하고 정돈된 디자인"""
    from analysis.patterns.price_action import PatternDirection
    from data.universe import get_stock_name

    rows = []
    for result in results:
        stock_name = get_stock_name(result.symbol)
        display_name = stock_name if stock_name != result.symbol else result.symbol

        for signal in result.signals:
            is_bullish = signal.direction == PatternDirection.BULLISH
            rr1 = signal.risk_reward_1 if hasattr(signal, 'risk_reward_1') else (
                abs(signal.take_profit_1 - signal.entry_price) / signal.risk_amount if signal.risk_amount > 0 else 0
            )

            rows.append({
                "_symbol": result.symbol,
                "_bullish": is_bullish,
                "종목": display_name,
                "패턴": signal.pattern_type,
                "방향": "Long" if is_bullish else "Short",
                "RR": f"1:{rr1:.1f}",
                "신뢰도": f"{signal.confidence:.0f}%",
                "진입가": format_price(signal.entry_price, result.symbol),
            })

    if not rows:
        return

    # 종목 선택 영역
    st.markdown("##### 종목 선택")

    # 롱/숏 분리 표시
    long_rows = [r for r in rows if r["_bullish"]]
    short_rows = [r for r in rows if not r["_bullish"]]

    col1, col2 = st.columns(2)

    with col1:
        if long_rows:
            st.markdown(f"**Long** ({len(long_rows)})")
            for i, row in enumerate(long_rows):
                label = f"{row['종목']} · {row['패턴']} · {row['RR']}"
                if st.button(label, key=f"ta_long_{i}", width="stretch"):
                    st.session_state["ta_selected_symbol"] = row["_symbol"]
                    st.rerun()

    with col2:
        if short_rows:
            st.markdown(f"**Short** ({len(short_rows)})")
            for i, row in enumerate(short_rows):
                label = f"{row['종목']} · {row['패턴']} · {row['RR']}"
                if st.button(label, key=f"ta_short_{i}", width="stretch"):
                    st.session_state["ta_selected_symbol"] = row["_symbol"]
                    st.rerun()



def _render_ta_full_data(results):
    """TA 전체 데이터 테이블 (전체 너비, 상세 정보 포함)"""
    from analysis.patterns.price_action import PatternDirection
    from data.universe import get_stock_name

    with st.expander("전체 데이터", expanded=False):
        rows = []
        for result in results:
            stock_name = get_stock_name(result.symbol)
            display_name = stock_name if stock_name != result.symbol else result.symbol
            for signal in result.signals:
                is_bullish = signal.direction == PatternDirection.BULLISH
                dir_icon = "🟢" if is_bullish else "🔴"
                rr1 = signal.risk_reward_1 if hasattr(signal, 'risk_reward_1') else (
                    abs(signal.take_profit_1 - signal.entry_price) / signal.risk_amount if signal.risk_amount > 0 else 0
                )
                rows.append({
                    "": dir_icon,
                    "종목": display_name,
                    "패턴": signal.pattern_type,
                    "RR": f"1:{rr1:.1f}",
                    "신뢰도": f"{signal.confidence:.0f}%",
                    "진입가": format_price(signal.entry_price, result.symbol),
                    "손절가": format_price(signal.stop_loss, result.symbol),
                    "TP1": format_price(signal.take_profit_1, result.symbol),
                    "TP2": format_price(signal.take_profit_2, result.symbol),
                    "근거": signal.rationale[:40] + "..." if len(signal.rationale) > 40 else signal.rationale,
                })
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("CSV 다운로드", csv, "ta_signals.csv", "text/csv", key="dl_ta_csv")


def _render_ta_detail_view(results):
    """상세 분석 뷰 - 심플하고 정돈된 디자인"""
    from analysis.patterns.price_action import PatternDirection, PatternStrength
    from data.universe import get_stock_name, get_symbol_with_name

    if not results:
        st.info("표시할 시그널이 없습니다")
        return

    # 종목 선택
    symbol_list = [r.symbol for r in results]
    symbol_options = {get_symbol_with_name(s): s for s in symbol_list}
    display_options = list(symbol_options.keys())

    default_idx = 0
    if "ta_selected_symbol" in st.session_state:
        clicked_symbol = st.session_state["ta_selected_symbol"]
        for i, display in enumerate(display_options):
            if symbol_options[display] == clicked_symbol:
                default_idx = i
                break

    selected_display = st.selectbox("종목 선택", display_options, index=default_idx, key="ta_detail_symbol_v4")
    selected_symbol = symbol_options[selected_display]

    result = next((r for r in results if r.symbol == selected_symbol), None)
    if not result:
        return

    is_kr = is_korean_stock(selected_symbol)

    # 시그널 카드
    for i, signal in enumerate(result.signals):
        is_bullish = signal.direction == PatternDirection.BULLISH
        rr1 = abs(signal.take_profit_1 - signal.entry_price) / signal.risk_amount if signal.risk_amount > 0 else 0
        rr2 = abs(signal.take_profit_2 - signal.entry_price) / signal.risk_amount if signal.risk_amount > 0 else 0
        rr3 = abs(signal.take_profit_3 - signal.entry_price) / signal.risk_amount if signal.risk_amount > 0 else 0

        dir_color = "#22c55e" if is_bullish else "#ef4444"
        dir_text = "LONG" if is_bullish else "SHORT"

        # 카드 헤더
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin:16px 0 8px 0;">
            <span style="background:{dir_color}; color:white; padding:4px 12px; border-radius:4px; font-weight:600; font-size:13px;">{dir_text}</span>
            <span style="font-size:16px; font-weight:600;">{signal.pattern_type}</span>
            <span style="color:#6b7280; font-size:13px;">신뢰도 {signal.confidence:.0f}%</span>
        </div>
        """, unsafe_allow_html=True)

        # 가격 그리드 (2행 3열)
        st.markdown("""
        <style>
        .price-grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; margin:8px 0; }
        .price-box { background:#f8fafc; padding:12px; border-radius:6px; }
        .price-label { font-size:11px; color:#6b7280; margin-bottom:2px; }
        .price-value { font-size:15px; font-weight:600; }
        .price-sub { font-size:11px; color:#9ca3af; }
        </style>
        """, unsafe_allow_html=True)

        entry_str = format_price(signal.entry_price, is_korean=is_kr)
        sl_str = format_price(signal.stop_loss, is_korean=is_kr)
        tp1_str = format_price(signal.take_profit_1, is_korean=is_kr)
        tp2_str = format_price(signal.take_profit_2, is_korean=is_kr)
        tp3_str = format_price(signal.take_profit_3, is_korean=is_kr)
        risk_str = format_price(signal.risk_amount, is_korean=is_kr)

        st.markdown(f"""
        <div class="price-grid">
            <div class="price-box">
                <div class="price-label">Entry</div>
                <div class="price-value">{entry_str}</div>
            </div>
            <div class="price-box">
                <div class="price-label">Stop Loss</div>
                <div class="price-value" style="color:#ef4444;">{sl_str}</div>
                <div class="price-sub">Risk: {risk_str}</div>
            </div>
            <div class="price-box">
                <div class="price-label">TP1</div>
                <div class="price-value" style="color:#22c55e;">{tp1_str}</div>
                <div class="price-sub">RR 1:{rr1:.1f}</div>
            </div>
            <div class="price-box">
                <div class="price-label">TP2</div>
                <div class="price-value" style="color:#22c55e;">{tp2_str}</div>
                <div class="price-sub">RR 1:{rr2:.1f}</div>
            </div>
            <div class="price-box">
                <div class="price-label">TP3</div>
                <div class="price-value" style="color:#22c55e;">{tp3_str}</div>
                <div class="price-sub">RR 1:{rr3:.1f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 진입 근거 (간결하게)
        st.markdown(f"<div style='background:#f0f9ff; padding:10px 14px; border-radius:6px; font-size:13px; color:#0369a1; margin:8px 0;'>{signal.rationale}</div>", unsafe_allow_html=True)

        # 차트 버튼
        if st.button("차트 보기", key=f"goto_chart_{selected_symbol}_{i}"):
            st.session_state["chart_signal_data"] = {
                "symbol": selected_symbol,
                "direction": "bullish" if is_bullish else "bearish",
                "zone_high": signal.entry_price * 1.02,
                "zone_low": signal.entry_price * 0.98,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit_1": signal.take_profit_1,
                "take_profit_2": signal.take_profit_2,
                "pattern_type": signal.pattern_type,
            }
            st.session_state["chart_symbol"] = selected_symbol
            st.session_state["_nav_to"] = "📈 차트"
            st.rerun()

        if i < len(result.signals) - 1:
            st.markdown("<hr style='margin:20px 0; border:none; border-top:1px solid #e5e7eb;'>", unsafe_allow_html=True)


# === 메인 ===

def main():
    init_session_state()

    try:
        idea_manager, universe_manager, runner, MarketCondition = load_managers()
    except Exception as e:
        st.error(f"시스템 로드 실패: {e}")
        return

    menu, market_cond = render_sidebar()

    if menu == "📊 마켓":
        render_market_overview_page()
    elif menu == "📈 차트":
        render_chart_page()
    elif menu == "🔬 TA 스크리너":
        render_ta_screener_page()
    elif menu == "🎯 스크리너":
        render_screening_page(idea_manager, universe_manager, runner, market_cond, MarketCondition)
    elif menu == "🌐 유니버스":
        render_universe_page(universe_manager)
    elif menu == "⚙️ 설정":
        render_settings_page(runner)


if __name__ == "__main__":
    main()
