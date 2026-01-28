"""
Screener Ideas - 스크리닝 아이디어 및 시나리오 관리

다양한 시장 상황과 투자 스타일에 맞는 스크리닝 아이디어를 제공
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class IdeaCategory(Enum):
    """아이디어 카테고리"""
    # 투자 기간
    SWING = "swing"              # 스윙 (며칠~몇주)
    POSITION = "position"        # 포지션 (몇주~몇달)
    LONG_TERM = "long_term"      # 장기 (몇달~몇년)

    # 스타일
    MOMENTUM = "momentum"        # 모멘텀
    VALUE = "value"              # 가치
    GROWTH = "growth"            # 성장
    QUALITY = "quality"          # 퀄리티
    CONTRARIAN = "contrarian"    # 역발상

    # 특수 상황
    TURNAROUND = "turnaround"    # 턴어라운드
    BREAKOUT = "breakout"        # 돌파
    PULLBACK = "pullback"        # 눌림목
    DIVIDEND = "dividend"        # 배당


class MarketCondition(Enum):
    """시장 상황"""
    BULL = "bull"                # 강세장
    BEAR = "bear"                # 약세장
    SIDEWAYS = "sideways"        # 횡보장
    VOLATILE = "volatile"        # 변동성 장
    RATE_CUT = "rate_cut"        # 금리 인하기
    RATE_HIKE = "rate_hike"      # 금리 인상기
    RECOVERY = "recovery"        # 회복기
    CORRECTION = "correction"    # 조정기


@dataclass
class FilterDefinition:
    """필터 정의"""
    name: str
    display_name: str
    type: str  # int, float, bool, str, range
    default: Any
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    step: Optional[float] = None
    description: str = ""
    unit: str = ""  # %, 원, 배 등


# === 필터 카테고리 정의 (Finviz/TradingView 스타일) ===
FILTER_CATEGORIES = {
    "descriptive": "기본 정보",
    "valuation": "밸류에이션",
    "profitability": "수익성",
    "growth": "성장성",
    "dividend": "배당",
    "financial": "재무건전성",
    "performance": "수익률",
    "price_position": "가격 위치",
    "moving_average": "이동평균",
    "momentum": "모멘텀 지표",
    "volume": "거래량",
    "volatility": "변동성",
}

# 공통 필터 정의 (Finviz/TradingView 수준 확장)
COMMON_FILTERS: Dict[str, FilterDefinition] = {
    # =========================================================================
    # 📊 기본 정보 (Descriptive)
    # =========================================================================
    "min_market_cap": FilterDefinition("min_market_cap", "최소 시가총액", "float", 100000000000, 0, None, 10000000000, "시가총액 하한", "원"),
    "max_market_cap": FilterDefinition("max_market_cap", "최대 시가총액", "float", None, 0, None, 10000000000, "시가총액 상한", "원"),
    "min_price": FilterDefinition("min_price", "최소 주가", "float", 1000, 0, None, 100, "주가 하한", "원"),
    "max_price": FilterDefinition("max_price", "최대 주가", "float", None, 0, None, 1000, "주가 상한", "원"),
    "min_avg_volume": FilterDefinition("min_avg_volume", "최소 평균거래량", "float", 100000, 0, 100000000, 10000, "20일 평균 거래량 하한", "주"),
    "max_avg_volume": FilterDefinition("max_avg_volume", "최대 평균거래량", "float", None, 0, 100000000, 100000, "20일 평균 거래량 상한", "주"),
    "min_shares_outstanding": FilterDefinition("min_shares_outstanding", "최소 발행주식수", "float", None, 0, None, 1000000, "발행주식수 하한", "주"),
    "max_shares_outstanding": FilterDefinition("max_shares_outstanding", "최대 발행주식수", "float", None, 0, None, 1000000, "발행주식수 상한", "주"),
    "min_float_shares": FilterDefinition("min_float_shares", "최소 유통주식수", "float", None, 0, None, 1000000, "유통주식수 하한", "주"),

    # =========================================================================
    # 💰 밸류에이션 (Valuation)
    # =========================================================================
    "min_per": FilterDefinition("min_per", "최소 PER", "float", 0, -100, 500, 1, "PER 하한", "배"),
    "max_per": FilterDefinition("max_per", "최대 PER", "float", 20, -100, 500, 1, "PER 상한", "배"),
    "min_forward_per": FilterDefinition("min_forward_per", "최소 Forward PER", "float", 0, -100, 500, 1, "예상 PER 하한", "배"),
    "max_forward_per": FilterDefinition("max_forward_per", "최대 Forward PER", "float", 25, -100, 500, 1, "예상 PER 상한", "배"),
    "min_peg": FilterDefinition("min_peg", "최소 PEG", "float", 0, -10, 10, 0.1, "PEG 하한", ""),
    "max_peg": FilterDefinition("max_peg", "최대 PEG", "float", 2, -10, 10, 0.1, "PEG 상한 (1 미만 저평가)", ""),
    "min_pbr": FilterDefinition("min_pbr", "최소 PBR", "float", 0, 0, 50, 0.1, "PBR 하한", "배"),
    "max_pbr": FilterDefinition("max_pbr", "최대 PBR", "float", 5, 0, 50, 0.1, "PBR 상한", "배"),
    "min_psr": FilterDefinition("min_psr", "최소 PSR", "float", 0, 0, 100, 0.5, "PSR 하한", "배"),
    "max_psr": FilterDefinition("max_psr", "최대 PSR", "float", 10, 0, 100, 0.5, "PSR 상한", "배"),
    "min_pcr": FilterDefinition("min_pcr", "최소 PCR", "float", 0, 0, 100, 1, "Price/Cash 하한", "배"),
    "max_pcr": FilterDefinition("max_pcr", "최대 PCR", "float", 20, 0, 100, 1, "Price/Cash 상한", "배"),
    "min_pfcf": FilterDefinition("min_pfcf", "최소 P/FCF", "float", 0, 0, 200, 1, "Price/FCF 하한", "배"),
    "max_pfcf": FilterDefinition("max_pfcf", "최대 P/FCF", "float", 30, 0, 200, 1, "Price/FCF 상한", "배"),
    "min_ev_ebitda": FilterDefinition("min_ev_ebitda", "최소 EV/EBITDA", "float", 0, 0, 100, 1, "EV/EBITDA 하한", "배"),
    "max_ev_ebitda": FilterDefinition("max_ev_ebitda", "최대 EV/EBITDA", "float", 15, 0, 100, 1, "EV/EBITDA 상한", "배"),
    "min_ev_sales": FilterDefinition("min_ev_sales", "최소 EV/Sales", "float", 0, 0, 50, 0.5, "EV/Sales 하한", "배"),
    "max_ev_sales": FilterDefinition("max_ev_sales", "최대 EV/Sales", "float", 10, 0, 50, 0.5, "EV/Sales 상한", "배"),

    # =========================================================================
    # 📈 수익성 (Profitability)
    # =========================================================================
    "min_roe": FilterDefinition("min_roe", "최소 ROE", "float", 10, -100, 200, 1, "자기자본수익률 하한", "%"),
    "max_roe": FilterDefinition("max_roe", "최대 ROE", "float", None, -100, 200, 5, "ROE 상한", "%"),
    "min_roa": FilterDefinition("min_roa", "최소 ROA", "float", 5, -50, 100, 1, "총자산수익률 하한", "%"),
    "max_roa": FilterDefinition("max_roa", "최대 ROA", "float", None, -50, 100, 5, "ROA 상한", "%"),
    "min_roi": FilterDefinition("min_roi", "최소 ROI", "float", 10, -100, 200, 1, "투자수익률 하한", "%"),
    "min_roic": FilterDefinition("min_roic", "최소 ROIC", "float", 10, -50, 100, 1, "투하자본수익률 하한", "%"),
    "min_gross_margin": FilterDefinition("min_gross_margin", "최소 매출총이익률", "float", 20, -50, 100, 5, "Gross Margin 하한", "%"),
    "max_gross_margin": FilterDefinition("max_gross_margin", "최대 매출총이익률", "float", None, 0, 100, 5, "Gross Margin 상한", "%"),
    "min_operating_margin": FilterDefinition("min_operating_margin", "최소 영업이익률", "float", 10, -100, 100, 1, "Operating Margin 하한", "%"),
    "max_operating_margin": FilterDefinition("max_operating_margin", "최대 영업이익률", "float", None, -100, 100, 5, "Operating Margin 상한", "%"),
    "min_net_margin": FilterDefinition("min_net_margin", "최소 순이익률", "float", 5, -100, 100, 1, "Net Margin 하한", "%"),
    "max_net_margin": FilterDefinition("max_net_margin", "최대 순이익률", "float", None, -100, 100, 5, "Net Margin 상한", "%"),
    "min_fcf_margin": FilterDefinition("min_fcf_margin", "최소 FCF 마진", "float", 5, -100, 100, 1, "FCF Margin 하한", "%"),
    "min_fcf_yield": FilterDefinition("min_fcf_yield", "최소 FCF Yield", "float", 3, 0, 50, 0.5, "잉여현금흐름수익률 하한", "%"),

    # =========================================================================
    # 🚀 성장성 (Growth)
    # =========================================================================
    "min_revenue_growth": FilterDefinition("min_revenue_growth", "최소 매출성장률(YoY)", "float", 5, -100, 500, 5, "연간 매출성장률 하한", "%"),
    "max_revenue_growth": FilterDefinition("max_revenue_growth", "최대 매출성장률(YoY)", "float", None, -100, 500, 10, "연간 매출성장률 상한", "%"),
    "min_revenue_growth_qoq": FilterDefinition("min_revenue_growth_qoq", "최소 매출성장률(QoQ)", "float", 0, -100, 300, 5, "분기 매출성장률 하한", "%"),
    "min_eps_growth": FilterDefinition("min_eps_growth", "최소 EPS 성장률(YoY)", "float", 10, -100, 500, 5, "연간 EPS 성장률 하한", "%"),
    "max_eps_growth": FilterDefinition("max_eps_growth", "최대 EPS 성장률(YoY)", "float", None, -100, 500, 10, "연간 EPS 성장률 상한", "%"),
    "min_eps_growth_qoq": FilterDefinition("min_eps_growth_qoq", "최소 EPS 성장률(QoQ)", "float", 0, -100, 300, 5, "분기 EPS 성장률 하한", "%"),
    "min_ebitda_growth": FilterDefinition("min_ebitda_growth", "최소 EBITDA 성장률", "float", 10, -100, 500, 5, "연간 EBITDA 성장률 하한", "%"),
    "min_eps_growth_5y": FilterDefinition("min_eps_growth_5y", "최소 EPS 5년 성장률", "float", 10, -50, 200, 5, "5년 EPS CAGR 하한", "%"),
    "min_revenue_growth_5y": FilterDefinition("min_revenue_growth_5y", "최소 매출 5년 성장률", "float", 5, -50, 200, 5, "5년 매출 CAGR 하한", "%"),
    "min_eps_growth_next_5y": FilterDefinition("min_eps_growth_next_5y", "최소 예상 EPS 5년 성장률", "float", 10, -50, 200, 5, "향후 5년 EPS 예상 성장률", "%"),

    # =========================================================================
    # 💵 배당 (Dividend)
    # =========================================================================
    "min_dividend_yield": FilterDefinition("min_dividend_yield", "최소 배당수익률", "float", 2, 0, 30, 0.5, "배당수익률 하한", "%"),
    "max_dividend_yield": FilterDefinition("max_dividend_yield", "최대 배당수익률", "float", 10, 0, 30, 0.5, "배당수익률 상한 (너무 높으면 위험)", "%"),
    "min_payout_ratio": FilterDefinition("min_payout_ratio", "최소 배당성향", "float", 0, 0, 200, 5, "배당성향 하한", "%"),
    "max_payout_ratio": FilterDefinition("max_payout_ratio", "최대 배당성향", "float", 80, 0, 200, 5, "배당성향 상한 (80% 이하 안정)", "%"),
    "min_dividend_growth_5y": FilterDefinition("min_dividend_growth_5y", "최소 배당 5년 성장률", "float", 5, -50, 100, 5, "5년 배당성장률 하한", "%"),
    "consecutive_dividend_years": FilterDefinition("consecutive_dividend_years", "연속 배당 연수", "float", 5, 0, 50, 1, "연속 배당 지급 연수", "년"),

    # =========================================================================
    # 🏦 재무건전성 (Financial Health)
    # =========================================================================
    "min_current_ratio": FilterDefinition("min_current_ratio", "최소 유동비율", "float", 1.5, 0, 10, 0.1, "Current Ratio 하한", "배"),
    "max_current_ratio": FilterDefinition("max_current_ratio", "최대 유동비율", "float", None, 0, 20, 0.5, "Current Ratio 상한", "배"),
    "min_quick_ratio": FilterDefinition("min_quick_ratio", "최소 당좌비율", "float", 1, 0, 10, 0.1, "Quick Ratio 하한", "배"),
    "max_debt_equity": FilterDefinition("max_debt_equity", "최대 부채비율", "float", 100, 0, 500, 10, "Debt/Equity 상한", "%"),
    "min_debt_equity": FilterDefinition("min_debt_equity", "최소 부채비율", "float", 0, 0, 500, 10, "Debt/Equity 하한", "%"),
    "max_lt_debt_equity": FilterDefinition("max_lt_debt_equity", "최대 장기부채비율", "float", 50, 0, 300, 5, "LT Debt/Equity 상한", "%"),
    "min_interest_coverage": FilterDefinition("min_interest_coverage", "최소 이자보상배율", "float", 3, 0, 100, 1, "Interest Coverage 하한", "배"),
    "max_debt_ebitda": FilterDefinition("max_debt_ebitda", "최대 Debt/EBITDA", "float", 3, 0, 20, 0.5, "Debt/EBITDA 상한", "배"),

    # =========================================================================
    # 📊 수익률 (Performance)
    # =========================================================================
    "min_return_1w": FilterDefinition("min_return_1w", "최소 1주 수익률", "float", 0, -50, 100, 1, "1주 수익률 하한", "%"),
    "max_return_1w": FilterDefinition("max_return_1w", "최대 1주 수익률", "float", 15, -50, 100, 1, "1주 수익률 상한", "%"),
    "min_return_1m": FilterDefinition("min_return_1m", "최소 1개월 수익률", "float", 0, -100, 200, 1, "1개월 수익률 하한", "%"),
    "max_return_1m": FilterDefinition("max_return_1m", "최대 1개월 수익률", "float", 30, -100, 200, 1, "1개월 수익률 상한", "%"),
    "min_return_3m": FilterDefinition("min_return_3m", "최소 3개월 수익률", "float", 5, -100, 300, 5, "3개월 수익률 하한", "%"),
    "max_return_3m": FilterDefinition("max_return_3m", "최대 3개월 수익률", "float", 50, -100, 300, 5, "3개월 수익률 상한", "%"),
    "min_return_6m": FilterDefinition("min_return_6m", "최소 6개월 수익률", "float", 10, -100, 500, 5, "6개월 수익률 하한", "%"),
    "max_return_6m": FilterDefinition("max_return_6m", "최대 6개월 수익률", "float", 100, -100, 500, 10, "6개월 수익률 상한", "%"),
    "min_return_ytd": FilterDefinition("min_return_ytd", "최소 YTD 수익률", "float", 0, -100, 500, 5, "연초대비 수익률 하한", "%"),
    "max_return_ytd": FilterDefinition("max_return_ytd", "최대 YTD 수익률", "float", None, -100, 500, 10, "연초대비 수익률 상한", "%"),
    "min_return_12m": FilterDefinition("min_return_12m", "최소 12개월 수익률", "float", 15, -100, 1000, 10, "12개월 수익률 하한", "%"),
    "max_return_12m": FilterDefinition("max_return_12m", "최대 12개월 수익률", "float", 200, -100, 1000, 20, "12개월 수익률 상한", "%"),

    # =========================================================================
    # 📍 가격 위치 (Price Position)
    # =========================================================================
    "min_from_52w_low": FilterDefinition("min_from_52w_low", "52주 저점 대비 최소", "float", 20, 0, 1000, 5, "52주 저점 대비 최소 상승률", "%"),
    "max_from_52w_low": FilterDefinition("max_from_52w_low", "52주 저점 대비 최대", "float", 100, 0, 1000, 10, "52주 저점 대비 최대 상승률", "%"),
    "min_from_52w_high": FilterDefinition("min_from_52w_high", "52주 고점 대비 최소", "float", 0, 0, 100, 5, "52주 고점 대비 최소 하락률", "%"),
    "max_from_52w_high": FilterDefinition("max_from_52w_high", "52주 고점 대비 최대", "float", 30, 0, 100, 5, "52주 고점 대비 최대 하락률", "%"),
    "near_52w_high": FilterDefinition("near_52w_high", "52주 신고가 근접", "bool", False, description="52주 고점 대비 5% 이내"),
    "near_52w_low": FilterDefinition("near_52w_low", "52주 신저가 근접", "bool", False, description="52주 저점 대비 5% 이내"),
    "new_52w_high": FilterDefinition("new_52w_high", "52주 신고가", "bool", False, description="오늘 52주 신고가 갱신"),
    "new_52w_low": FilterDefinition("new_52w_low", "52주 신저가", "bool", False, description="오늘 52주 신저가 갱신"),
    "min_from_ath": FilterDefinition("min_from_ath", "ATH 대비 최소", "float", 0, 0, 100, 5, "역대최고가 대비 최소 하락률", "%"),
    "max_from_ath": FilterDefinition("max_from_ath", "ATH 대비 최대", "float", 50, 0, 100, 5, "역대최고가 대비 최대 하락률", "%"),

    # =========================================================================
    # 📈 이동평균 (Moving Average)
    # =========================================================================
    "price_above_ma5": FilterDefinition("price_above_ma5", "가격 > 5일 MA", "bool", False, description="현재가가 5일 이동평균 위"),
    "price_above_ma10": FilterDefinition("price_above_ma10", "가격 > 10일 MA", "bool", False, description="현재가가 10일 이동평균 위"),
    "price_above_ma20": FilterDefinition("price_above_ma20", "가격 > 20일 MA", "bool", True, description="현재가가 20일 이동평균 위"),
    "price_above_ma50": FilterDefinition("price_above_ma50", "가격 > 50일 MA", "bool", True, description="현재가가 50일 이동평균 위"),
    "price_above_ma100": FilterDefinition("price_above_ma100", "가격 > 100일 MA", "bool", False, description="현재가가 100일 이동평균 위"),
    "price_above_ma200": FilterDefinition("price_above_ma200", "가격 > 200일 MA", "bool", True, description="현재가가 200일 이동평균 위"),
    "price_below_ma20": FilterDefinition("price_below_ma20", "가격 < 20일 MA", "bool", False, description="현재가가 20일 이동평균 아래"),
    "price_below_ma50": FilterDefinition("price_below_ma50", "가격 < 50일 MA", "bool", False, description="현재가가 50일 이동평균 아래"),
    "price_below_ma200": FilterDefinition("price_below_ma200", "가격 < 200일 MA", "bool", False, description="현재가가 200일 이동평균 아래"),
    "ma5_above_ma20": FilterDefinition("ma5_above_ma20", "5MA > 20MA", "bool", False, description="5일선이 20일선 위"),
    "ma20_above_ma50": FilterDefinition("ma20_above_ma50", "20MA > 50MA", "bool", True, description="20일선이 50일선 위"),
    "ma50_above_ma150": FilterDefinition("ma50_above_ma150", "50MA > 150MA", "bool", True, description="50일선이 150일선 위"),
    "ma50_above_ma200": FilterDefinition("ma50_above_ma200", "50MA > 200MA", "bool", True, description="50일선이 200일선 위"),
    "ma150_above_ma200": FilterDefinition("ma150_above_ma200", "150MA > 200MA", "bool", True, description="150일선이 200일선 위"),
    "golden_cross": FilterDefinition("golden_cross", "골든크로스", "bool", False, description="최근 50일선이 200일선 상향돌파"),
    "death_cross": FilterDefinition("death_cross", "데드크로스", "bool", False, description="최근 50일선이 200일선 하향돌파"),
    "ma20_rising": FilterDefinition("ma20_rising", "20일선 상승", "bool", False, description="20일 이동평균이 상승 중"),
    "ma50_rising": FilterDefinition("ma50_rising", "50일선 상승", "bool", False, description="50일 이동평균이 상승 중"),
    "ma200_rising": FilterDefinition("ma200_rising", "200일선 상승", "bool", False, description="200일 이동평균이 상승 중"),

    # =========================================================================
    # 📉 모멘텀 지표 (Momentum Indicators)
    # =========================================================================
    "min_rsi": FilterDefinition("min_rsi", "최소 RSI(14)", "float", 30, 0, 100, 5, "RSI 하한", ""),
    "max_rsi": FilterDefinition("max_rsi", "최대 RSI(14)", "float", 70, 0, 100, 5, "RSI 상한", ""),
    "rsi_oversold": FilterDefinition("rsi_oversold", "RSI 과매도", "bool", False, description="RSI < 30"),
    "rsi_overbought": FilterDefinition("rsi_overbought", "RSI 과매수", "bool", False, description="RSI > 70"),
    "macd_bullish": FilterDefinition("macd_bullish", "MACD 매수신호", "bool", False, description="MACD > Signal"),
    "macd_bearish": FilterDefinition("macd_bearish", "MACD 매도신호", "bool", False, description="MACD < Signal"),
    "macd_cross_up": FilterDefinition("macd_cross_up", "MACD 골든크로스", "bool", False, description="MACD가 시그널 상향돌파"),
    "macd_cross_down": FilterDefinition("macd_cross_down", "MACD 데드크로스", "bool", False, description="MACD가 시그널 하향돌파"),
    "min_stochastic_k": FilterDefinition("min_stochastic_k", "최소 스토캐스틱 %K", "float", 0, 0, 100, 5, "Stochastic %K 하한", ""),
    "max_stochastic_k": FilterDefinition("max_stochastic_k", "최대 스토캐스틱 %K", "float", 100, 0, 100, 5, "Stochastic %K 상한", ""),
    "min_cci": FilterDefinition("min_cci", "최소 CCI", "float", -100, -300, 300, 20, "CCI 하한", ""),
    "max_cci": FilterDefinition("max_cci", "최대 CCI", "float", 100, -300, 300, 20, "CCI 상한", ""),
    "min_adx": FilterDefinition("min_adx", "최소 ADX", "float", 20, 0, 100, 5, "ADX 하한 (추세강도)", ""),
    "max_adx": FilterDefinition("max_adx", "최대 ADX", "float", 50, 0, 100, 5, "ADX 상한", ""),
    "min_williams_r": FilterDefinition("min_williams_r", "최소 Williams %R", "float", -80, -100, 0, 5, "Williams %R 하한", ""),
    "max_williams_r": FilterDefinition("max_williams_r", "최대 Williams %R", "float", -20, -100, 0, 5, "Williams %R 상한", ""),
    "min_roc": FilterDefinition("min_roc", "최소 ROC(12)", "float", 0, -100, 200, 5, "Rate of Change 하한", "%"),
    "max_roc": FilterDefinition("max_roc", "최대 ROC(12)", "float", 50, -100, 200, 5, "Rate of Change 상한", "%"),

    # =========================================================================
    # 📊 거래량 (Volume)
    # =========================================================================
    "min_volume_change": FilterDefinition("min_volume_change", "최소 거래량 변화", "float", 0, -100, 1000, 10, "전일대비 거래량 변화 하한", "%"),
    "max_volume_change": FilterDefinition("max_volume_change", "최대 거래량 변화", "float", 500, -100, 1000, 50, "전일대비 거래량 변화 상한", "%"),
    "min_relative_volume": FilterDefinition("min_relative_volume", "최소 상대거래량", "float", 1, 0, 20, 0.5, "20일 평균 대비 거래량 비율 하한", "배"),
    "max_relative_volume": FilterDefinition("max_relative_volume", "최대 상대거래량", "float", 10, 0, 50, 1, "20일 평균 대비 거래량 비율 상한", "배"),
    "volume_spike": FilterDefinition("volume_spike", "거래량 급증", "bool", False, description="거래량이 평균의 2배 이상"),
    "volume_dry_up": FilterDefinition("volume_dry_up", "거래량 감소", "bool", False, description="거래량이 평균의 50% 미만"),
    "price_up_volume_up": FilterDefinition("price_up_volume_up", "가격↑ 거래량↑", "bool", False, description="가격 상승 + 거래량 증가"),
    "price_down_volume_up": FilterDefinition("price_down_volume_up", "가격↓ 거래량↑", "bool", False, description="가격 하락 + 거래량 증가 (매도압력)"),

    # =========================================================================
    # 📈 변동성 (Volatility)
    # =========================================================================
    "min_beta": FilterDefinition("min_beta", "최소 베타", "float", 0, -2, 5, 0.1, "베타 하한", ""),
    "max_beta": FilterDefinition("max_beta", "최대 베타", "float", 2, -2, 5, 0.1, "베타 상한", ""),
    "min_atr_percent": FilterDefinition("min_atr_percent", "최소 ATR%", "float", 1, 0, 30, 0.5, "ATR 비율 하한", "%"),
    "max_atr_percent": FilterDefinition("max_atr_percent", "최대 ATR%", "float", 10, 0, 30, 1, "ATR 비율 상한", "%"),
    "min_volatility_1m": FilterDefinition("min_volatility_1m", "최소 1개월 변동성", "float", 5, 0, 100, 5, "1개월 변동성 하한", "%"),
    "max_volatility_1m": FilterDefinition("max_volatility_1m", "최대 1개월 변동성", "float", 50, 0, 100, 5, "1개월 변동성 상한", "%"),
    "min_volatility_1w": FilterDefinition("min_volatility_1w", "최소 1주 변동성", "float", 2, 0, 50, 1, "1주 변동성 하한", "%"),
    "max_volatility_1w": FilterDefinition("max_volatility_1w", "최대 1주 변동성", "float", 20, 0, 50, 2, "1주 변동성 상한", "%"),
    "high_volatility": FilterDefinition("high_volatility", "고변동성", "bool", False, description="변동성이 평균보다 높음"),
    "low_volatility": FilterDefinition("low_volatility", "저변동성", "bool", False, description="변동성이 평균보다 낮음"),

    # =========================================================================
    # 🎯 종합 점수
    # =========================================================================
    "min_total_score": FilterDefinition("min_total_score", "최소 종합점수", "float", 50, 0, 100, 5, "통과 기준 점수", "점"),
}

# 필터를 카테고리별로 그룹화
FILTER_BY_CATEGORY: Dict[str, List[str]] = {
    "descriptive": ["min_market_cap", "max_market_cap", "min_price", "max_price", "min_avg_volume", "max_avg_volume", "min_shares_outstanding", "max_shares_outstanding", "min_float_shares"],
    "valuation": ["min_per", "max_per", "min_forward_per", "max_forward_per", "min_peg", "max_peg", "min_pbr", "max_pbr", "min_psr", "max_psr", "min_pcr", "max_pcr", "min_pfcf", "max_pfcf", "min_ev_ebitda", "max_ev_ebitda", "min_ev_sales", "max_ev_sales"],
    "profitability": ["min_roe", "max_roe", "min_roa", "max_roa", "min_roi", "min_roic", "min_gross_margin", "max_gross_margin", "min_operating_margin", "max_operating_margin", "min_net_margin", "max_net_margin", "min_fcf_margin", "min_fcf_yield"],
    "growth": ["min_revenue_growth", "max_revenue_growth", "min_revenue_growth_qoq", "min_eps_growth", "max_eps_growth", "min_eps_growth_qoq", "min_ebitda_growth", "min_eps_growth_5y", "min_revenue_growth_5y", "min_eps_growth_next_5y"],
    "dividend": ["min_dividend_yield", "max_dividend_yield", "min_payout_ratio", "max_payout_ratio", "min_dividend_growth_5y", "consecutive_dividend_years"],
    "financial": ["min_current_ratio", "max_current_ratio", "min_quick_ratio", "max_debt_equity", "min_debt_equity", "max_lt_debt_equity", "min_interest_coverage", "max_debt_ebitda"],
    "performance": ["min_return_1w", "max_return_1w", "min_return_1m", "max_return_1m", "min_return_3m", "max_return_3m", "min_return_6m", "max_return_6m", "min_return_ytd", "max_return_ytd", "min_return_12m", "max_return_12m"],
    "price_position": ["min_from_52w_low", "max_from_52w_low", "min_from_52w_high", "max_from_52w_high", "near_52w_high", "near_52w_low", "new_52w_high", "new_52w_low", "min_from_ath", "max_from_ath"],
    "moving_average": ["price_above_ma5", "price_above_ma10", "price_above_ma20", "price_above_ma50", "price_above_ma100", "price_above_ma200", "price_below_ma20", "price_below_ma50", "price_below_ma200", "ma5_above_ma20", "ma20_above_ma50", "ma50_above_ma150", "ma50_above_ma200", "ma150_above_ma200", "golden_cross", "death_cross", "ma20_rising", "ma50_rising", "ma200_rising"],
    "momentum": ["min_rsi", "max_rsi", "rsi_oversold", "rsi_overbought", "macd_bullish", "macd_bearish", "macd_cross_up", "macd_cross_down", "min_stochastic_k", "max_stochastic_k", "min_cci", "max_cci", "min_adx", "max_adx", "min_williams_r", "max_williams_r", "min_roc", "max_roc"],
    "volume": ["min_volume_change", "max_volume_change", "min_relative_volume", "max_relative_volume", "volume_spike", "volume_dry_up", "price_up_volume_up", "price_down_volume_up"],
    "volatility": ["min_beta", "max_beta", "min_atr_percent", "max_atr_percent", "min_volatility_1m", "max_volatility_1m", "min_volatility_1w", "max_volatility_1w", "high_volatility", "low_volatility"],
}


@dataclass
class ScreenerIdea:
    """스크리닝 아이디어"""
    id: str
    name: str
    description: str

    # 분류
    category: IdeaCategory
    suitable_conditions: List[MarketCondition]

    # 대상 시장/유니버스
    markets: List[str]           # kospi, nasdaq, crypto 등
    sectors: List[str] = field(default_factory=list)  # 특정 섹터
    exclude_sectors: List[str] = field(default_factory=list)

    # 전략/필터
    strategy_type: str = ""      # quant_screener, swing_screener 등
    filters: Dict[str, Any] = field(default_factory=dict)
    indicators: List[str] = field(default_factory=list)

    # 기대
    expected_holding_period: str = ""  # "1-2주", "1-3개월" 등
    risk_level: str = "medium"   # low, medium, high
    expected_win_rate: str = ""  # "40-50%" 등

    # 메타
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    # 커스텀 여부
    is_custom: bool = False
    base_idea_id: Optional[str] = None  # 기반이 된 아이디어

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "markets": self.markets,
            "strategy_type": self.strategy_type,
            "filters": self.filters,
            "expected_holding_period": self.expected_holding_period,
            "risk_level": self.risk_level,
            "is_custom": self.is_custom,
        }

    def clone_with_filters(self, new_filters: Dict[str, Any], new_name: str = None) -> "ScreenerIdea":
        """필터를 변경한 복제본 생성"""
        import copy
        cloned = copy.deepcopy(self)
        cloned.id = f"{self.id}_custom_{datetime.now().strftime('%H%M%S')}"
        cloned.name = new_name or f"{self.name} (커스텀)"
        cloned.filters.update(new_filters)
        cloned.is_custom = True
        cloned.base_idea_id = self.id
        cloned.created_at = datetime.now()
        return cloned

    def get_filter_definitions(self) -> Dict[str, FilterDefinition]:
        """이 아이디어에서 사용하는 필터 정의 반환"""
        return {k: COMMON_FILTERS[k] for k in self.filters.keys() if k in COMMON_FILTERS}

    @staticmethod
    def get_available_filters() -> Dict[str, FilterDefinition]:
        """사용 가능한 모든 필터 정의"""
        return COMMON_FILTERS


# ============================================================================
# 사전 정의된 스크리닝 아이디어
# ============================================================================

BUILT_IN_IDEAS: List[ScreenerIdea] = [
    # =========================================================================
    # 🚀 퀵 스타트 아이디어 (가격 데이터만으로 즉시 실행 가능)
    # =========================================================================
    ScreenerIdea(
        id="quick_momentum",
        name="⚡ 퀵 모멘텀 (즉시 실행)",
        description="""
        가격 데이터만으로 바로 실행 가능한 모멘텀 전략.
        상승 추세 + 적정 수익률 종목 발굴.
        강세장에서 가장 효과적.
        """,
        category=IdeaCategory.MOMENTUM,
        suitable_conditions=[MarketCondition.BULL, MarketCondition.RECOVERY],
        markets=["kospi", "kosdaq", "nasdaq", "nyse", "crypto"],
        strategy_type="quant_screener",
        filters={
            # 핵심: 가격 데이터만으로 계산
            "min_return_1m": 3,        # 최근 1개월 양호
            "min_return_3m": 10,       # 3개월 상승세
            "max_return_1m": 25,       # 과열 방지
            "price_above_ma50": True,  # 50일선 위
            "max_from_52w_high": 20,   # 고점 대비 20% 이내
            "min_total_score": 50,
        },
        expected_holding_period="2-8주",
        risk_level="medium",
        expected_win_rate="45-55%",
        tags=["momentum", "quick-start", "trend"],
    ),

    ScreenerIdea(
        id="quick_value",
        name="💎 퀵 가치주 (저평가 반등)",
        description="""
        최근 하락 후 반등 조짐.
        과매도 구간에서 회복 시작.
        저점 매수 기회.
        """,
        category=IdeaCategory.VALUE,
        suitable_conditions=[MarketCondition.CORRECTION, MarketCondition.BEAR, MarketCondition.RECOVERY],
        markets=["kospi", "kosdaq", "nasdaq", "nyse"],
        strategy_type="quant_screener",
        filters={
            "max_return_3m": 0,        # 3개월 조정
            "min_return_1m": 0,        # 최근 반등 시작
            "min_from_52w_low": 5,     # 저점에서 어느정도 상승
            "max_from_52w_high": 50,   # 고점 대비 크게 하락
            "price_above_ma20": True,  # 단기 반등
            "min_total_score": 45,
        },
        expected_holding_period="1-3개월",
        risk_level="medium",
        expected_win_rate="40-50%",
        tags=["value", "quick-start", "reversal"],
    ),

    # =========================================================================
    # 📈 모멘텀 전략
    # =========================================================================
    ScreenerIdea(
        id="strong_momentum",
        name="🔥 강세 모멘텀",
        description="""
        강한 상승 추세에 있는 종목.
        정배열 + 신고가 근처.
        추세 추종 전략.
        """,
        category=IdeaCategory.MOMENTUM,
        suitable_conditions=[MarketCondition.BULL],
        markets=["kospi", "kosdaq", "nasdaq", "nyse", "crypto"],
        strategy_type="quant_screener",
        filters={
            "min_return_3m": 15,       # 3개월 15%+ (기존 20%에서 완화)
            "min_return_6m": 25,       # 6개월 25%+ (기존 40%에서 완화)
            "max_from_52w_high": 15,   # 고점 근처
            "price_above_ma50": True,
            "price_above_ma200": True,
            "min_total_score": 55,
        },
        expected_holding_period="1-3개월",
        risk_level="medium",
        expected_win_rate="45-55%",
        tags=["momentum", "trend", "bull-market"],
    ),

    ScreenerIdea(
        id="minervini_trend",
        name="📈 추세 템플릿 (미너비니)",
        description="""
        마크 미너비니 스타일 추세 추종.
        이동평균 정배열 + 건강한 조정.
        슈퍼 퍼포머 패턴.
        """,
        category=IdeaCategory.MOMENTUM,
        suitable_conditions=[MarketCondition.BULL, MarketCondition.RECOVERY],
        markets=["nasdaq", "nyse", "kospi", "kosdaq"],
        strategy_type="quant_screener",
        filters={
            "price_above_ma50": True,
            "price_above_ma200": True,
            "ma50_above_ma150": True,
            "ma150_above_ma200": True,
            "min_from_52w_low": 25,    # 저점 대비 25%+ 상승
            "max_from_52w_high": 25,   # 고점 대비 25% 이내
            "min_return_6m": 10,       # 6개월 양호
            "min_total_score": 55,
        },
        expected_holding_period="2-8주",
        risk_level="medium",
        expected_win_rate="40-50%",
        tags=["momentum", "minervini", "trend-template"],
    ),

    # =========================================================================
    # 📉 눌림목 / 조정 매수
    # =========================================================================
    ScreenerIdea(
        id="pullback_buy",
        name="📉 눌림목 매수",
        description="""
        상승 추세에서 일시적 조정.
        6개월 강세 후 단기 조정 종목.
        추세 지속 기대.
        """,
        category=IdeaCategory.PULLBACK,
        suitable_conditions=[MarketCondition.BULL, MarketCondition.CORRECTION],
        markets=["nasdaq", "kospi", "kosdaq", "nyse"],
        strategy_type="quant_screener",
        filters={
            "min_return_6m": 15,       # 6개월 상승 (기존 20%에서 완화)
            "max_return_1m": 0,        # 최근 1개월 조정
            "min_return_1m": -15,      # 너무 큰 하락은 제외
            "price_above_ma200": True, # 장기 추세 유지
            "min_total_score": 50,
        },
        expected_holding_period="2-6주",
        risk_level="medium",
        expected_win_rate="45-55%",
        tags=["pullback", "dip-buying", "momentum"],
    ),

    ScreenerIdea(
        id="oversold_bounce",
        name="🔄 과매도 반등",
        description="""
        RSI 과매도 구간 후 반등.
        단기 급락 후 회복 시작.
        빠른 스윙 트레이딩.
        """,
        category=IdeaCategory.CONTRARIAN,
        suitable_conditions=[MarketCondition.CORRECTION, MarketCondition.SIDEWAYS],
        markets=["nasdaq", "kospi", "crypto"],
        strategy_type="quant_screener",
        filters={
            "max_return_1m": -10,      # 최근 하락
            "min_return_1m": -30,      # 너무 큰 하락 제외
            "min_rsi": 25,             # 과매도
            "max_rsi": 45,             # 아직 과매수 아님
            "price_above_ma200": True, # 장기 추세는 유지
            "min_total_score": 45,
        },
        expected_holding_period="1-2주",
        risk_level="high",
        expected_win_rate="40-50%",
        tags=["oversold", "bounce", "swing"],
    ),

    # =========================================================================
    # 🚀 돌파 전략
    # =========================================================================
    ScreenerIdea(
        id="breakout_setup",
        name="🚀 돌파 셋업",
        description="""
        52주 신고가 근처 + 변동성 축소.
        돌파 준비 완료 종목.
        거래량 급증 시 진입.
        """,
        category=IdeaCategory.BREAKOUT,
        suitable_conditions=[MarketCondition.BULL],
        markets=["nasdaq", "kospi", "kosdaq", "nyse"],
        strategy_type="quant_screener",
        filters={
            "max_from_52w_high": 10,   # 고점 대비 10% 이내
            "min_from_52w_low": 30,    # 저점 대비 30%+ 상승
            "price_above_ma50": True,
            "ma50_above_ma150": True,
            "min_total_score": 55,
        },
        expected_holding_period="1-4주",
        risk_level="high",
        expected_win_rate="35-45%",
        tags=["breakout", "new-high", "momentum"],
    ),

    # =========================================================================
    # 💰 가치 투자
    # =========================================================================
    ScreenerIdea(
        id="deep_value",
        name="💰 딥 밸류",
        description="""
        극도로 저평가된 종목.
        가격 기준 저평가 + 하락 후 안정.
        인내심 필요.
        """,
        category=IdeaCategory.VALUE,
        suitable_conditions=[MarketCondition.BEAR, MarketCondition.CORRECTION],
        markets=["kospi", "nyse", "kosdaq"],
        strategy_type="quant_screener",
        filters={
            "max_from_52w_high": 50,   # 고점 대비 50%+ 하락
            "min_from_52w_low": 10,    # 저점에서 소폭 반등
            "min_return_1m": -5,       # 안정화
            "max_return_1m": 10,
            "price_above_ma20": True,  # 단기 바닥 확인
            "min_total_score": 45,
        },
        expected_holding_period="3-12개월",
        risk_level="high",
        expected_win_rate="40-50%",
        tags=["deep-value", "contrarian", "turnaround"],
    ),

    ScreenerIdea(
        id="quality_stable",
        name="🏛️ 안정 우량주",
        description="""
        안정적 상승 + 낮은 변동성.
        대형 우량주 중심.
        보수적 투자자용.
        """,
        category=IdeaCategory.QUALITY,
        suitable_conditions=[MarketCondition.BULL, MarketCondition.SIDEWAYS, MarketCondition.RATE_HIKE],
        markets=["kospi", "nyse", "nasdaq"],
        strategy_type="quant_screener",
        filters={
            "min_return_6m": 5,        # 완만한 상승
            "max_return_6m": 30,       # 과열 아님
            "min_return_12m": 10,      # 연간 양호
            "price_above_ma200": True,
            "max_from_52w_high": 15,
            "min_total_score": 55,
        },
        expected_holding_period="6개월-1년",
        risk_level="low",
        expected_win_rate="55-65%",
        tags=["quality", "stable", "blue-chip"],
    ),

    # =========================================================================
    # ₿ 암호화폐
    # =========================================================================
    ScreenerIdea(
        id="crypto_momentum",
        name="₿ 크립토 모멘텀",
        description="""
        상승 추세 암호화폐.
        BTC 강세 시 알트코인 순환.
        높은 변동성 주의.
        """,
        category=IdeaCategory.MOMENTUM,
        suitable_conditions=[MarketCondition.BULL],
        markets=["crypto"],
        strategy_type="quant_screener",
        filters={
            "min_return_1m": 5,        # 최근 상승
            "min_return_3m": 15,       # 3개월 강세
            "max_return_1m": 50,       # 과열 방지
            "price_above_ma20": True,
            "min_total_score": 50,
        },
        expected_holding_period="1-4주",
        risk_level="high",
        expected_win_rate="40-50%",
        tags=["crypto", "momentum", "altcoin"],
    ),

    ScreenerIdea(
        id="crypto_dip",
        name="₿ 크립토 조정 매수",
        description="""
        상승 추세 내 조정 매수.
        Fear & Greed 공포 구간.
        BTC 연동 하락 시 기회.
        """,
        category=IdeaCategory.CONTRARIAN,
        suitable_conditions=[MarketCondition.CORRECTION, MarketCondition.SIDEWAYS],
        markets=["crypto"],
        strategy_type="quant_screener",
        filters={
            "max_return_1m": -5,       # 최근 조정
            "min_return_3m": -30,      # 패닉 셀 아님
            "min_from_52w_low": 10,    # 저점 아님
            "min_total_score": 45,
        },
        expected_holding_period="1-2주",
        risk_level="high",
        expected_win_rate="40-50%",
        tags=["crypto", "dip", "contrarian"],
    ),

    # =========================================================================
    # 📊 기타 전략
    # =========================================================================
    ScreenerIdea(
        id="sideways_range",
        name="↔️ 박스권 스윙",
        description="""
        횡보장에서 박스권 매매.
        지지선 근처 매수, 저항선 매도.
        레인지 트레이딩.
        """,
        category=IdeaCategory.SWING,
        suitable_conditions=[MarketCondition.SIDEWAYS],
        markets=["kospi", "nasdaq", "crypto"],
        strategy_type="quant_screener",
        filters={
            "min_return_3m": -10,
            "max_return_3m": 10,       # 횡보
            "min_from_52w_low": 15,    # 지지선 위
            "max_from_52w_high": 20,   # 저항선 아래
            "min_total_score": 50,
        },
        expected_holding_period="1-3주",
        risk_level="medium",
        expected_win_rate="50-55%",
        tags=["swing", "range", "sideways"],
    ),

    ScreenerIdea(
        id="sector_leader",
        name="🏆 섹터 리더",
        description="""
        각 섹터 내 최강 종목.
        업종 대비 상대 강도 우수.
        섹터 로테이션 활용.
        """,
        category=IdeaCategory.MOMENTUM,
        suitable_conditions=[MarketCondition.BULL, MarketCondition.RECOVERY],
        markets=["kospi", "nasdaq", "nyse"],
        strategy_type="quant_screener",
        filters={
            "min_return_3m": 10,
            "min_return_6m": 15,
            "price_above_ma50": True,
            "price_above_ma200": True,
            "max_from_52w_high": 15,
            "min_total_score": 55,
        },
        expected_holding_period="1-3개월",
        risk_level="medium",
        expected_win_rate="45-55%",
        tags=["sector", "leader", "momentum"],
    ),
]


class IdeaManager:
    """스크리닝 아이디어 관리자"""

    def __init__(self, custom_ideas_file: str = None):
        self.ideas: Dict[str, ScreenerIdea] = {}
        self.custom_ideas: Dict[str, ScreenerIdea] = {}
        self.custom_ideas_file = custom_ideas_file or "data/custom_ideas.json"
        self._load_built_in()
        self._load_custom_ideas()

    def _load_built_in(self):
        """기본 아이디어 로드"""
        for idea in BUILT_IN_IDEAS:
            self.ideas[idea.id] = idea

    def _load_custom_ideas(self):
        """커스텀 아이디어 로드"""
        from pathlib import Path
        filepath = Path(self.custom_ideas_file)
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                for item in data:
                    idea = self._dict_to_idea(item)
                    self.custom_ideas[idea.id] = idea
                    self.ideas[idea.id] = idea
            except Exception as e:
                pass  # 파일 로드 실패시 무시

    def _dict_to_idea(self, data: Dict) -> ScreenerIdea:
        """딕셔너리를 ScreenerIdea로 변환"""
        return ScreenerIdea(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            category=IdeaCategory(data.get("category", "momentum")),
            suitable_conditions=[MarketCondition(c) for c in data.get("suitable_conditions", [])],
            markets=data.get("markets", []),
            strategy_type=data.get("strategy_type", "quant_screener"),
            filters=data.get("filters", {}),
            expected_holding_period=data.get("expected_holding_period", ""),
            risk_level=data.get("risk_level", "medium"),
            is_custom=True,
            base_idea_id=data.get("base_idea_id"),
        )

    def _save_custom_ideas(self):
        """커스텀 아이디어 저장"""
        from pathlib import Path
        filepath = Path(self.custom_ideas_file)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = [i.to_dict() for i in self.custom_ideas.values()]
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def get(self, idea_id: str) -> Optional[ScreenerIdea]:
        """아이디어 조회"""
        return self.ideas.get(idea_id)

    def list_all(self) -> List[ScreenerIdea]:
        """전체 목록"""
        return list(self.ideas.values())

    def list_built_in(self) -> List[ScreenerIdea]:
        """기본 아이디어만"""
        return [i for i in self.ideas.values() if not i.is_custom]

    def list_custom(self) -> List[ScreenerIdea]:
        """커스텀 아이디어만"""
        return [i for i in self.ideas.values() if i.is_custom]

    def list_by_category(self, category: IdeaCategory) -> List[ScreenerIdea]:
        """카테고리별 조회"""
        return [i for i in self.ideas.values() if i.category == category]

    def list_by_market(self, market: str) -> List[ScreenerIdea]:
        """시장별 조회"""
        return [i for i in self.ideas.values() if market in i.markets]

    def list_by_condition(self, condition: MarketCondition) -> List[ScreenerIdea]:
        """시장 상황별 조회"""
        return [i for i in self.ideas.values() if condition in i.suitable_conditions]

    def search(self, query: str) -> List[ScreenerIdea]:
        """키워드 검색"""
        query = query.lower()
        results = []
        for idea in self.ideas.values():
            if (query in idea.name.lower() or
                query in idea.description.lower() or
                query in [t.lower() for t in idea.tags]):
                results.append(idea)
        return results

    def add_custom(self, idea: ScreenerIdea):
        """커스텀 아이디어 추가"""
        idea.is_custom = True
        self.ideas[idea.id] = idea
        self.custom_ideas[idea.id] = idea
        self._save_custom_ideas()

    def create_custom_from_base(
        self,
        base_idea_id: str,
        new_name: str,
        modified_filters: Dict[str, Any],
    ) -> ScreenerIdea:
        """기존 아이디어 기반 커스텀 생성"""
        base = self.get(base_idea_id)
        if not base:
            raise ValueError(f"Unknown idea: {base_idea_id}")

        custom = base.clone_with_filters(modified_filters, new_name)
        self.add_custom(custom)
        return custom

    def delete_custom(self, idea_id: str) -> bool:
        """커스텀 아이디어 삭제"""
        if idea_id in self.custom_ideas:
            del self.custom_ideas[idea_id]
            del self.ideas[idea_id]
            self._save_custom_ideas()
            return True
        return False

    def export_to_json(self, filepath: str):
        """JSON 내보내기"""
        data = [i.to_dict() for i in self.ideas.values()]
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_recommendations(
        self,
        market: Optional[str] = None,
        condition: Optional[MarketCondition] = None,
        risk_level: Optional[str] = None,
    ) -> List[ScreenerIdea]:
        """조건에 맞는 아이디어 추천"""
        results = list(self.ideas.values())

        if market:
            results = [i for i in results if market in i.markets]

        if condition:
            results = [i for i in results if condition in i.suitable_conditions]

        if risk_level:
            results = [i for i in results if i.risk_level == risk_level]

        return results

    @staticmethod
    def get_filter_definitions() -> Dict[str, FilterDefinition]:
        """사용 가능한 필터 정의"""
        return COMMON_FILTERS
