"""
Market Overview - 시장 전체 현황 분석

시계열 흐름 기반의 시장 분석:
- 지수 트렌드 (단순 일봉이 아닌 추세 강도)
- 시장 브레드스 (상승/하락 종목 비율의 시계열)
- 섹터 트렌드 (섹터별 상대 강도 흐름)
- 트렌드 시그널 (추세 전환, 모멘텀 이상)
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class TrendStrength(Enum):
    """추세 강도"""
    STRONG_UP = "strong_up"      # 강한 상승 추세
    MODERATE_UP = "moderate_up"  # 완만한 상승
    WEAK_UP = "weak_up"          # 약한 상승
    NEUTRAL = "neutral"          # 중립/횡보
    WEAK_DOWN = "weak_down"      # 약한 하락
    MODERATE_DOWN = "moderate_down"  # 완만한 하락
    STRONG_DOWN = "strong_down"  # 강한 하락 추세


class TrendSignal(Enum):
    """트렌드 시그널"""
    BREAKOUT = "breakout"              # 신고가 돌파
    BREAKDOWN = "breakdown"            # 신저가 이탈
    GOLDEN_CROSS = "golden_cross"      # 골든크로스 (MA20 > MA50)
    DEATH_CROSS = "death_cross"        # 데드크로스 (MA20 < MA50)
    MOMENTUM_SURGE = "momentum_surge"  # 모멘텀 급등
    MOMENTUM_FADE = "momentum_fade"    # 모멘텀 급락
    VOLUME_SPIKE = "volume_spike"      # 거래량 급증
    TREND_REVERSAL = "trend_reversal"  # 추세 전환


@dataclass
class TrendAnalysis:
    """단일 종목/지수 트렌드 분석"""
    symbol: str
    name: str

    # 현재 상태
    price: float
    change_1d: float  # 일간 변화율

    # 시계열 수익률
    return_1w: float
    return_1m: float
    return_3m: float
    return_6m: float = 0.0

    # 추세 분석
    trend_strength: TrendStrength = TrendStrength.NEUTRAL
    trend_score: float = 0.0  # -100 ~ +100
    trend_consistency: float = 0.0  # 추세 일관성 (0~100)

    # MA 상태
    above_ma20: bool = False
    above_ma50: bool = False
    above_ma200: bool = False
    ma_alignment: str = ""  # "perfect_bull", "bull", "mixed", "bear", "perfect_bear"

    # 시그널
    signals: List[TrendSignal] = field(default_factory=list)

    # 메타
    volume_ratio: float = 1.0  # 평균 대비 거래량
    rsi: float = 50.0
    from_52w_high: float = 0.0
    from_52w_low: float = 0.0


@dataclass
class SectorTrend:
    """섹터 트렌드"""
    sector: str

    # 트렌드 점수
    trend_score: float  # -100 ~ +100
    trend_strength: TrendStrength

    # 시계열 성과
    return_1w: float
    return_1m: float
    return_3m: float

    # 구성
    symbol_count: int
    advancing: int  # 상승 종목 수
    declining: int  # 하락 종목 수

    # 대표 종목
    top_performers: List[str] = field(default_factory=list)
    worst_performers: List[str] = field(default_factory=list)


@dataclass
class MarketBreadth:
    """시장 브레드스 (시계열)"""
    timestamp: datetime

    # 상승/하락
    advancing: int
    declining: int
    unchanged: int
    advance_decline_ratio: float

    # MA 기준
    above_ma20: int
    above_ma50: int
    above_ma200: int
    above_ma20_pct: float
    above_ma50_pct: float
    above_ma200_pct: float

    # 신고/신저
    new_high_52w: int
    new_low_52w: int
    new_high_20d: int
    new_low_20d: int


@dataclass
class MarketOverview:
    """시장 전체 현황"""
    timestamp: datetime
    market: str  # "us", "korea", "crypto"

    # 지수 트렌드
    indices: List[TrendAnalysis] = field(default_factory=list)

    # 시장 브레드스 (최근 N일)
    breadth_history: List[MarketBreadth] = field(default_factory=list)
    current_breadth: Optional[MarketBreadth] = None

    # 섹터 트렌드
    sectors: List[SectorTrend] = field(default_factory=list)

    # 트렌드 시그널 (종목별)
    trending_up: List[TrendAnalysis] = field(default_factory=list)  # 상승 추세 강한 종목
    trending_down: List[TrendAnalysis] = field(default_factory=list)  # 하락 추세 강한 종목
    momentum_leaders: List[TrendAnalysis] = field(default_factory=list)  # 모멘텀 상위
    momentum_laggards: List[TrendAnalysis] = field(default_factory=list)  # 모멘텀 하위

    # 시그널별 종목
    breakouts: List[TrendAnalysis] = field(default_factory=list)
    breakdowns: List[TrendAnalysis] = field(default_factory=list)
    golden_crosses: List[TrendAnalysis] = field(default_factory=list)
    death_crosses: List[TrendAnalysis] = field(default_factory=list)
    volume_spikes: List[TrendAnalysis] = field(default_factory=list)

    # 요약
    market_trend: TrendStrength = TrendStrength.NEUTRAL
    market_score: float = 0.0  # -100 ~ +100
    summary: str = ""


class TrendCalculator:
    """트렌드 계산기"""

    @staticmethod
    def calculate_trend_score(df: pd.DataFrame) -> float:
        """
        추세 점수 계산 (-100 ~ +100)

        가중치:
        - MA 정렬: 25점
        - 가격 위치: 20점
        - 모멘텀 (수익률): 30점
        - 추세 일관성: 15점
        - RSI 상태: 10점
        """
        if df is None or len(df) < 50:
            return 0.0

        score = 0.0
        latest = df.iloc[-1]

        # 1. MA 정렬 (25점)
        ma_score = 0
        if 'ma20' in df.columns and 'ma50' in df.columns:
            if latest['close'] > latest.get('ma20', 0):
                ma_score += 5
            if latest['close'] > latest.get('ma50', 0):
                ma_score += 5
            if latest['close'] > latest.get('ma200', latest['close']):
                ma_score += 5
            if latest.get('ma20', 0) > latest.get('ma50', 0):
                ma_score += 5
            if latest.get('ma50', 0) > latest.get('ma200', latest.get('ma50', 0)):
                ma_score += 5
        score += ma_score

        # 2. 가격 위치 (20점) - 52주 범위 내 위치
        if len(df) >= 252:
            high_52w = df['high'].rolling(252).max().iloc[-1]
            low_52w = df['low'].rolling(252).min().iloc[-1]
            if high_52w > low_52w:
                position = (latest['close'] - low_52w) / (high_52w - low_52w)
                score += (position - 0.5) * 40  # -20 ~ +20

        # 3. 모멘텀 (30점) - 다기간 수익률
        momentum_score = 0
        periods = [(5, 5), (20, 10), (60, 10), (120, 5)]  # (기간, 가중치)
        for period, weight in periods:
            if len(df) > period:
                ret = (latest['close'] / df.iloc[-period-1]['close'] - 1) * 100
                # -10% ~ +10%를 -weight ~ +weight로 매핑
                momentum_score += max(min(ret / 10, 1), -1) * weight
        score += momentum_score

        # 4. 추세 일관성 (15점) - 최근 20일 중 상승일 비율
        if len(df) >= 20:
            recent = df.tail(20)
            up_days = (recent['close'].diff() > 0).sum()
            consistency = (up_days / 20 - 0.5) * 2  # -1 ~ +1
            score += consistency * 15

        # 5. RSI 상태 (10점)
        if 'rsi' in df.columns:
            rsi = latest['rsi']
            if rsi > 70:
                score += 5  # 과매수지만 강세
            elif rsi > 50:
                score += 10 * (rsi - 50) / 20  # 50~70: 0~10
            elif rsi > 30:
                score -= 10 * (50 - rsi) / 20  # 30~50: -10~0
            else:
                score -= 10  # 과매도

        return max(min(score, 100), -100)

    @staticmethod
    def calculate_trend_strength(score: float) -> TrendStrength:
        """점수를 추세 강도로 변환"""
        if score >= 60:
            return TrendStrength.STRONG_UP
        elif score >= 30:
            return TrendStrength.MODERATE_UP
        elif score >= 10:
            return TrendStrength.WEAK_UP
        elif score >= -10:
            return TrendStrength.NEUTRAL
        elif score >= -30:
            return TrendStrength.WEAK_DOWN
        elif score >= -60:
            return TrendStrength.MODERATE_DOWN
        else:
            return TrendStrength.STRONG_DOWN

    @staticmethod
    def calculate_trend_consistency(df: pd.DataFrame, period: int = 20) -> float:
        """
        추세 일관성 계산 (0~100)
        높을수록 일관된 방향
        """
        if df is None or len(df) < period:
            return 50.0

        recent = df.tail(period)
        changes = recent['close'].pct_change().dropna()

        if len(changes) == 0:
            return 50.0

        # 같은 방향 비율
        positive = (changes > 0).sum()
        negative = (changes < 0).sum()

        consistency = max(positive, negative) / len(changes) * 100
        return consistency

    @staticmethod
    def detect_signals(df: pd.DataFrame, lookback: int = 5) -> List[TrendSignal]:
        """시그널 감지"""
        if df is None or len(df) < 50:
            return []

        signals = []
        latest = df.iloc[-1]

        # 신고가/신저가 (52주 또는 가능한 최대 기간)
        # 최소 60일 이상이면 분석
        if len(df) >= 60:
            # 252일 데이터가 없으면 가용한 전체 기간 사용
            window = min(252, len(df) - 1)
            high_period = df['high'].rolling(window).max()
            low_period = df['low'].rolling(window).min()

            # NaN 체크 후 비교
            if pd.notna(high_period.iloc[-2]) and latest['high'] >= high_period.iloc[-2]:
                signals.append(TrendSignal.BREAKOUT)
            if pd.notna(low_period.iloc[-2]) and latest['low'] <= low_period.iloc[-2]:
                signals.append(TrendSignal.BREAKDOWN)

        # 골든크로스/데드크로스 (50일 이상 필요)
        if len(df) >= 50 and 'ma20' in df.columns and 'ma50' in df.columns:
            ma20_series = df['ma20']
            ma50_series = df['ma50']

            # NaN이 아닌 값만 비교
            if pd.notna(ma20_series.iloc[-1]) and pd.notna(ma50_series.iloc[-1]):
                ma20_above = ma20_series > ma50_series
                if len(ma20_above) > lookback:
                    current_above = ma20_above.iloc[-1]
                    past_above = ma20_above.iloc[-lookback]
                    if pd.notna(past_above):
                        if current_above and not past_above:
                            signals.append(TrendSignal.GOLDEN_CROSS)
                        elif not current_above and past_above:
                            signals.append(TrendSignal.DEATH_CROSS)

        # 모멘텀 급변
        if len(df) >= 20:
            ret_5d = latest['close'] / df.iloc[-6]['close'] - 1
            pct_change_5d = df['close'].pct_change(5)
            avg_ret = pct_change_5d.rolling(20).std().iloc[-1]
            if pd.notna(avg_ret) and avg_ret > 0:
                if ret_5d > avg_ret * 2:
                    signals.append(TrendSignal.MOMENTUM_SURGE)
                elif ret_5d < -avg_ret * 2:
                    signals.append(TrendSignal.MOMENTUM_FADE)

        # 거래량 급증
        if 'volume' in df.columns:
            vol = latest.get('volume', 0)
            vol_ma20 = latest.get('volume_ma20', None)

            # volume_ma20가 없으면 직접 계산
            if vol_ma20 is None or pd.isna(vol_ma20):
                if len(df) >= 20:
                    vol_ma20 = df['volume'].tail(20).mean()

            if vol_ma20 is not None and vol_ma20 > 0:
                vol_ratio = vol / vol_ma20
                if vol_ratio > 2.5:
                    signals.append(TrendSignal.VOLUME_SPIKE)

        return signals

    @staticmethod
    def get_ma_alignment(df: pd.DataFrame) -> str:
        """MA 정렬 상태"""
        if df is None or len(df) < 200:
            return "unknown"

        latest = df.iloc[-1]
        close = latest['close']
        ma20 = latest.get('ma20', close)
        ma50 = latest.get('ma50', close)
        ma200 = latest.get('ma200', close)

        # Perfect Bull: Close > MA20 > MA50 > MA200
        if close > ma20 > ma50 > ma200:
            return "perfect_bull"
        # Bull: Close > MA50, MA20 > MA50
        elif close > ma50 and ma20 > ma50:
            return "bull"
        # Perfect Bear: Close < MA20 < MA50 < MA200
        elif close < ma20 < ma50 < ma200:
            return "perfect_bear"
        # Bear: Close < MA50, MA20 < MA50
        elif close < ma50 and ma20 < ma50:
            return "bear"
        else:
            return "mixed"


class MarketOverviewAnalyzer:
    """시장 전체 현황 분석기"""

    # 시장별 지수 정의
    INDICES = {
        "us": [
            ("SPY", "S&P 500"),
            ("QQQ", "NASDAQ 100"),
            ("IWM", "Russell 2000"),
            ("DIA", "Dow Jones"),
        ],
        "korea": [
            ("069500.KS", "KOSPI 200"),
            ("229200.KS", "KOSDAQ 150"),
            ("^KS11", "KOSPI"),
            ("^KQ11", "KOSDAQ"),
        ],
        "crypto": [
            ("BTC/USDT", "Bitcoin"),
            ("ETH/USDT", "Ethereum"),
            ("SOL/USDT", "Solana"),
        ],
    }

    # 섹터 ETF (US)
    SECTOR_ETFS = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financials": "XLF",
        "Consumer Disc.": "XLY",
        "Consumer Staples": "XLP",
        "Energy": "XLE",
        "Industrials": "XLI",
        "Materials": "XLB",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Communication": "XLC",
    }

    def __init__(self, data_source=None, cache_dir: str = "./data/cache"):
        """
        Args:
            data_source: 데이터 소스 (None이면 FastFetcher 사용)
            cache_dir: 캐시 디렉토리
        """
        self.data_source = data_source
        self.cache_dir = cache_dir
        self._fetcher = None
        self._data_layer = None

    @property
    def fetcher(self):
        if self._fetcher is None:
            from data.fast_fetcher import FastFetcher
            self._fetcher = FastFetcher(cache_dir=self.cache_dir)
        return self._fetcher

    @property
    def data_layer(self):
        if self._data_layer is None:
            try:
                from data.data_layer import get_data_layer_manager
                self._data_layer = get_data_layer_manager(cache_dir=self.cache_dir)
            except Exception as e:
                logger.warning(f"DataLayerManager not available: {e}")
        return self._data_layer

    def analyze_symbol(self, symbol: str, df: pd.DataFrame, name: str = "") -> TrendAnalysis:
        """단일 종목 트렌드 분석"""
        if df is None or df.empty:
            return TrendAnalysis(
                symbol=symbol, name=name or symbol,
                price=0, change_1d=0, return_1w=0, return_1m=0, return_3m=0
            )

        latest = df.iloc[-1]

        # 기본 수익률
        def safe_return(period: int) -> float:
            if len(df) <= period:
                return 0.0
            return (latest['close'] / df.iloc[-period-1]['close'] - 1) * 100

        change_1d = safe_return(1)
        return_1w = safe_return(5)
        return_1m = safe_return(20)
        return_3m = safe_return(60)
        return_6m = safe_return(120) if len(df) > 120 else 0

        # 추세 분석
        trend_score = TrendCalculator.calculate_trend_score(df)
        trend_strength = TrendCalculator.calculate_trend_strength(trend_score)
        trend_consistency = TrendCalculator.calculate_trend_consistency(df)

        # MA 상태
        above_ma20 = latest['close'] > latest.get('ma20', 0) if 'ma20' in df.columns else False
        above_ma50 = latest['close'] > latest.get('ma50', 0) if 'ma50' in df.columns else False
        above_ma200 = latest['close'] > latest.get('ma200', 0) if 'ma200' in df.columns else False
        ma_alignment = TrendCalculator.get_ma_alignment(df)

        # 시그널
        signals = TrendCalculator.detect_signals(df)

        # 기타 지표
        volume_ratio = 1.0
        if 'volume_ratio' in df.columns and pd.notna(latest.get('volume_ratio')):
            volume_ratio = latest['volume_ratio']
        elif 'volume' in df.columns and len(df) >= 20:
            vol_ma20 = df['volume'].tail(20).mean()
            if vol_ma20 > 0:
                volume_ratio = latest['volume'] / vol_ma20

        rsi = latest.get('rsi', 50.0) if 'rsi' in df.columns and pd.notna(latest.get('rsi')) else 50.0

        # 52주 고저 (또는 가용한 최대 기간)
        if len(df) >= 60:
            window = min(252, len(df) - 1)
            high_52w = df['high'].rolling(window).max().iloc[-1]
            low_52w = df['low'].rolling(window).min().iloc[-1]
            from_52w_high = (latest['close'] / high_52w - 1) * 100 if high_52w > 0 else 0
            from_52w_low = (latest['close'] / low_52w - 1) * 100 if low_52w > 0 else 0
        else:
            from_52w_high = 0
            from_52w_low = 0

        return TrendAnalysis(
            symbol=symbol,
            name=name or symbol,
            price=latest['close'],
            change_1d=change_1d,
            return_1w=return_1w,
            return_1m=return_1m,
            return_3m=return_3m,
            return_6m=return_6m,
            trend_strength=trend_strength,
            trend_score=trend_score,
            trend_consistency=trend_consistency,
            above_ma20=above_ma20,
            above_ma50=above_ma50,
            above_ma200=above_ma200,
            ma_alignment=ma_alignment,
            signals=signals,
            volume_ratio=volume_ratio,
            rsi=rsi,
            from_52w_high=from_52w_high,
            from_52w_low=from_52w_low,
        )

    def calculate_breadth(self, data: Dict[str, pd.DataFrame]) -> MarketBreadth:
        """시장 브레드스 계산"""
        advancing = 0
        declining = 0
        unchanged = 0
        above_ma20 = 0
        above_ma50 = 0
        above_ma200 = 0
        new_high_52w = 0
        new_low_52w = 0
        new_high_20d = 0
        new_low_20d = 0

        total = len(data)

        for symbol, df in data.items():
            if df is None or df.empty:
                continue

            latest = df.iloc[-1]

            # 상승/하락
            if len(df) > 1:
                change = latest['close'] - df.iloc[-2]['close']
                if change > 0:
                    advancing += 1
                elif change < 0:
                    declining += 1
                else:
                    unchanged += 1

            # MA 기준
            if 'ma20' in df.columns and latest['close'] > latest.get('ma20', 0):
                above_ma20 += 1
            if 'ma50' in df.columns and latest['close'] > latest.get('ma50', 0):
                above_ma50 += 1
            if 'ma200' in df.columns and latest['close'] > latest.get('ma200', 0):
                above_ma200 += 1

            # 신고/신저
            if len(df) >= 252:
                high_52w = df['high'].rolling(252).max()
                low_52w = df['low'].rolling(252).min()
                if latest['high'] >= high_52w.iloc[-2]:
                    new_high_52w += 1
                if latest['low'] <= low_52w.iloc[-2]:
                    new_low_52w += 1

            if len(df) >= 20:
                high_20d = df['high'].rolling(20).max()
                low_20d = df['low'].rolling(20).min()
                if latest['high'] >= high_20d.iloc[-2]:
                    new_high_20d += 1
                if latest['low'] <= low_20d.iloc[-2]:
                    new_low_20d += 1

        ad_ratio = advancing / declining if declining > 0 else (advancing if advancing > 0 else 1)

        return MarketBreadth(
            timestamp=datetime.now(),
            advancing=advancing,
            declining=declining,
            unchanged=unchanged,
            advance_decline_ratio=ad_ratio,
            above_ma20=above_ma20,
            above_ma50=above_ma50,
            above_ma200=above_ma200,
            above_ma20_pct=above_ma20 / total * 100 if total > 0 else 0,
            above_ma50_pct=above_ma50 / total * 100 if total > 0 else 0,
            above_ma200_pct=above_ma200 / total * 100 if total > 0 else 0,
            new_high_52w=new_high_52w,
            new_low_52w=new_low_52w,
            new_high_20d=new_high_20d,
            new_low_20d=new_low_20d,
        )

    def analyze_sectors(self, data: Dict[str, pd.DataFrame]) -> List[SectorTrend]:
        """섹터 트렌드 분석"""
        sectors = []

        for sector, etf in self.SECTOR_ETFS.items():
            if etf not in data:
                continue

            df = data[etf]
            if df is None or df.empty:
                continue

            analysis = self.analyze_symbol(etf, df, sector)

            sectors.append(SectorTrend(
                sector=sector,
                trend_score=analysis.trend_score,
                trend_strength=analysis.trend_strength,
                return_1w=analysis.return_1w,
                return_1m=analysis.return_1m,
                return_3m=analysis.return_3m,
                symbol_count=1,  # ETF 단일
                advancing=1 if analysis.change_1d > 0 else 0,
                declining=1 if analysis.change_1d < 0 else 0,
            ))

        # 점수순 정렬
        sectors.sort(key=lambda x: x.trend_score, reverse=True)
        return sectors

    def get_overview(
        self,
        market: str = "us",
        universe_symbols: List[str] = None,
        days: int = 365,
        workers: int = 10,
        top_n: int = 20,
        progress_callback=None,
    ) -> MarketOverview:
        """
        시장 전체 현황 분석

        Args:
            market: 시장 ("us", "korea", "crypto")
            universe_symbols: 분석할 종목 리스트 (None이면 기본 유니버스)
            days: 데이터 기간
            workers: 병렬 워커 수
            top_n: 각 카테고리 상위 N개
            progress_callback: fn(current, total, symbol, status)

        Returns:
            MarketOverview 객체
        """
        logger.info(f"Analyzing market overview: {market}")

        # 1. 분석 대상 심볼 수집
        symbols_to_fetch = []

        # 지수
        index_symbols = [(s, n) for s, n in self.INDICES.get(market, [])]
        symbols_to_fetch.extend([s for s, _ in index_symbols])

        # 섹터 ETF (미국만)
        if market == "us":
            symbols_to_fetch.extend(list(self.SECTOR_ETFS.values()))

        # 유니버스 종목
        if universe_symbols:
            symbols_to_fetch.extend(universe_symbols)
        else:
            # 기본 유니버스 로드
            default_symbols = self._get_default_universe(market)
            symbols_to_fetch.extend(default_symbols)

        symbols_to_fetch = list(set(symbols_to_fetch))

        # 2. 데이터 수집 (with indicators)
        logger.info(f"Fetching {len(symbols_to_fetch)} symbols...")

        if self.data_layer:
            data = self.data_layer.get_data_batch(
                symbols=symbols_to_fetch,
                days=days,
                with_indicators=True,
                workers=workers,
                progress_callback=progress_callback,
            )
        else:
            raw_data, _ = self.fetcher.fetch_many(
                symbols=symbols_to_fetch,
                days=days,
                workers=workers,
                progress_callback=progress_callback,
            )
            # 지표 계산
            from data.data_layer import IndicatorComputer
            data = {}
            for sym, df in raw_data.items():
                if df is not None and not df.empty:
                    data[sym] = IndicatorComputer.compute_all(df)

        # 3. 지수 분석
        indices = []
        for sym, name in index_symbols:
            if sym in data:
                indices.append(self.analyze_symbol(sym, data[sym], name))

        # 4. 브레드스 계산
        universe_data = {k: v for k, v in data.items() if k not in [s for s, _ in index_symbols]}
        current_breadth = self.calculate_breadth(universe_data)

        # 5. 섹터 분석
        sectors = self.analyze_sectors(data) if market == "us" else []

        # 6. 종목별 트렌드 분석
        all_analyses = []
        for sym, df in universe_data.items():
            if df is not None and not df.empty:
                analysis = self.analyze_symbol(sym, df)
                all_analyses.append(analysis)

        # 7. 카테고리별 정렬
        # 추세 강한 종목 (점수 기준)
        sorted_by_trend = sorted(all_analyses, key=lambda x: x.trend_score, reverse=True)
        trending_up = [a for a in sorted_by_trend if a.trend_score > 30][:top_n]
        trending_down = [a for a in sorted_by_trend if a.trend_score < -30][-top_n:][::-1]

        # 모멘텀 (1개월 수익률)
        sorted_by_momentum = sorted(all_analyses, key=lambda x: x.return_1m, reverse=True)
        momentum_leaders = sorted_by_momentum[:top_n]
        momentum_laggards = sorted_by_momentum[-top_n:][::-1]

        # 시그널별
        breakouts = [a for a in all_analyses if TrendSignal.BREAKOUT in a.signals][:top_n]
        breakdowns = [a for a in all_analyses if TrendSignal.BREAKDOWN in a.signals][:top_n]
        golden_crosses = [a for a in all_analyses if TrendSignal.GOLDEN_CROSS in a.signals][:top_n]
        death_crosses = [a for a in all_analyses if TrendSignal.DEATH_CROSS in a.signals][:top_n]
        volume_spikes = [a for a in all_analyses if TrendSignal.VOLUME_SPIKE in a.signals][:top_n]

        # 8. 시장 전체 점수
        if indices:
            market_score = sum(i.trend_score for i in indices) / len(indices)
        else:
            market_score = 0
        market_trend = TrendCalculator.calculate_trend_strength(market_score)

        # 9. 요약
        summary = self._generate_summary(indices, current_breadth, sectors, market_trend)

        return MarketOverview(
            timestamp=datetime.now(),
            market=market,
            indices=indices,
            breadth_history=[],
            current_breadth=current_breadth,
            sectors=sectors,
            trending_up=trending_up,
            trending_down=trending_down,
            momentum_leaders=momentum_leaders,
            momentum_laggards=momentum_laggards,
            breakouts=breakouts,
            breakdowns=breakdowns,
            golden_crosses=golden_crosses,
            death_crosses=death_crosses,
            volume_spikes=volume_spikes,
            market_trend=market_trend,
            market_score=market_score,
            summary=summary,
        )

    def _get_default_universe(self, market: str) -> List[str]:
        """기본 유니버스 로드"""
        try:
            import json
            from pathlib import Path

            universe_file = Path(__file__).parent.parent / "data" / "universe_symbols.json"
            if universe_file.exists():
                with open(universe_file) as f:
                    universes = json.load(f)

                if market == "us":
                    return universes.get("us", {}).get("sp500", [])[:100]
                elif market == "korea":
                    return universes.get("korea", {}).get("kospi200", [])[:100]
                elif market == "crypto":
                    return universes.get("crypto", {}).get("top50", [])[:30]
        except Exception as e:
            logger.warning(f"Failed to load universe: {e}")

        return []

    def _generate_summary(
        self,
        indices: List[TrendAnalysis],
        breadth: MarketBreadth,
        sectors: List[SectorTrend],
        market_trend: TrendStrength,
    ) -> str:
        """요약 생성"""
        parts = []

        # 시장 추세
        trend_labels = {
            TrendStrength.STRONG_UP: "강한 상승 추세",
            TrendStrength.MODERATE_UP: "완만한 상승 추세",
            TrendStrength.WEAK_UP: "약한 상승 흐름",
            TrendStrength.NEUTRAL: "횡보/중립",
            TrendStrength.WEAK_DOWN: "약한 하락 흐름",
            TrendStrength.MODERATE_DOWN: "완만한 하락 추세",
            TrendStrength.STRONG_DOWN: "강한 하락 추세",
        }
        parts.append(f"시장: {trend_labels.get(market_trend, '중립')}")

        # 브레드스
        if breadth:
            ad_str = f"상승 {breadth.advancing} / 하락 {breadth.declining}"
            ma_str = f"MA200↑ {breadth.above_ma200_pct:.0f}%"
            parts.append(f"{ad_str}, {ma_str}")

        # 섹터
        if sectors:
            top_sectors = [s.sector for s in sectors[:3] if s.trend_score > 0]
            if top_sectors:
                parts.append(f"강세 섹터: {', '.join(top_sectors)}")

        return " | ".join(parts)


# === 편의 함수 ===

def get_market_overview(
    market: str = "us",
    top_n: int = 20,
    progress_callback=None,
) -> MarketOverview:
    """
    시장 현황 분석 (편의 함수)

    Args:
        market: "us", "korea", "crypto"
        top_n: 각 카테고리 상위 N개
        progress_callback: 진행률 콜백

    Returns:
        MarketOverview 객체
    """
    analyzer = MarketOverviewAnalyzer()
    return analyzer.get_overview(
        market=market,
        top_n=top_n,
        progress_callback=progress_callback,
    )


def get_trending_stocks(
    market: str = "us",
    direction: str = "up",
    top_n: int = 20,
) -> List[TrendAnalysis]:
    """
    추세 강한 종목 조회

    Args:
        market: 시장
        direction: "up" or "down"
        top_n: 상위 N개

    Returns:
        TrendAnalysis 리스트
    """
    overview = get_market_overview(market=market, top_n=top_n)

    if direction == "up":
        return overview.trending_up
    else:
        return overview.trending_down


def get_sector_trends(market: str = "us") -> List[SectorTrend]:
    """섹터 트렌드 조회"""
    overview = get_market_overview(market=market)
    return overview.sectors
