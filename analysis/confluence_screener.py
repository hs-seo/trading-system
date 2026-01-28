"""
Confluence Screener v2 - 컨플루언스 기반 스크리너

Pine Script 아이디어 반영:
1. 존 품질 평가: 구조(CHOCH/BOS), HTF정렬, 베이스캔들, 임펄스, 골든존
2. 확인 캔들 강도: IBFB(3) > PIN/ENG(2) > DOJI(1)
3. 추가 확인: Price Action, Double Pattern, Liquidity Sweep
4. 위험도 평가: 반대 존 근접도
5. 시그널 상태: GO (확인완료), WAIT (존 진입, 트리거 대기)

점수 시스템 (최대 100점):
- 존 접근 거리: 0~20점
- 존 품질 (등급/Golden/CHOCH): 0~25점
- 트리거 캔들 강도 (IBFB/PIN/ENG/DOJI): 0~20점
- 추가 확인 (PA/Double/Liquidity): 0~25점
- HTF 정렬: 0~10점
- 위험도 (반대존): -10~0점
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging
import concurrent.futures

from .patterns import (
    PriceActionDetector,
    DoublePatternDetector,
    SMCDetector,
    LiquidityDetector,
)
from .patterns.price_action import PatternSignal, PatternDirection, PatternStrength
from .patterns.smc import OrderBlock, ZoneType

logger = logging.getLogger(__name__)


class POIType(Enum):
    """POI 유형"""
    DEMAND_ZONE = "demand"
    SUPPLY_ZONE = "supply"
    ORDER_BLOCK_BULL = "ob_bull"
    ORDER_BLOCK_BEAR = "ob_bear"


class TriggerStrength(Enum):
    """트리거 강도"""
    NONE = 0       # 없음
    WEAK = 1       # DOJI
    MEDIUM = 2     # PIN/ENG
    STRONG = 3     # IBFB


class SignalState(Enum):
    """시그널 상태"""
    NONE = "none"
    WAIT = "wait"   # 존 진입, 트리거 대기
    GO = "go"       # 확인 완료


@dataclass
class POI:
    """Point of Interest - 관심 지점"""
    poi_type: POIType
    top: float
    bottom: float
    grade: str              # S, A, B, C
    score: int              # 존 자체 품질 점수 (0-18)
    bar_index: int
    is_golden: bool = False
    golden_level: int = 0   # 0=없음, 1=38.2%, 2=50%, 3=61.8%
    is_choch: bool = False
    is_fresh: bool = True
    impulse_size: float = 0.0
    base_candles: int = 0

    @property
    def mid_price(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def zone_height(self) -> float:
        return self.top - self.bottom

    def distance_pct(self, price: float) -> float:
        """현재 가격에서 존까지의 거리 (%)"""
        if price > self.top:
            return (price - self.top) / price * 100
        elif price < self.bottom:
            return (self.bottom - price) / price * 100
        else:
            return 0.0

    def is_price_in_zone(self, price: float) -> bool:
        return self.bottom <= price <= self.top

    def is_approaching(self, price: float, threshold_pct: float = 3.0) -> bool:
        return self.distance_pct(price) <= threshold_pct


@dataclass
class TriggerCandle:
    """확인 캔들 정보"""
    trigger_type: str       # "ibfb", "pinbar", "engulfing", "doji", "liquidity_sweep"
    strength: TriggerStrength
    direction: PatternDirection
    bar_index: int
    details: str = ""

    @property
    def score(self) -> int:
        """강도별 점수 (0~20)"""
        return {
            TriggerStrength.STRONG: 20,  # IBFB
            TriggerStrength.MEDIUM: 15,  # PIN/ENG
            TriggerStrength.WEAK: 8,     # DOJI
            TriggerStrength.NONE: 0,
        }.get(self.strength, 0)


@dataclass
class ConfirmationSignal:
    """추가 확인 시그널 (PA, Double, Liquidity)"""
    pattern_type: str       # "pinbar", "engulfing", "double_bottom", "liquidity_sweep" 등
    category: str           # "price_action", "double_pattern", "liquidity"
    direction: PatternDirection
    score: int              # 개별 점수
    details: str = ""


class TrendDirection(Enum):
    """추세 방향"""
    STRONG_UP = "strong_up"      # 강한 상승
    UP = "up"                    # 상승
    NEUTRAL = "neutral"         # 횡보/박스
    DOWN = "down"               # 하락
    STRONG_DOWN = "strong_down" # 강한 하락


class MarketRegime(Enum):
    """시장 상태"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGE_BOUND = "range_bound"
    VOLATILE = "volatile"


@dataclass
class MarketContext:
    """시장 컨텍스트 분석 결과"""
    # 1. 장기 추세 (주봉 기준)
    weekly_trend: TrendDirection = TrendDirection.NEUTRAL
    weekly_ma_direction: str = "flat"  # "up", "down", "flat"
    higher_highs: bool = False         # 고점 상승 중인지
    higher_lows: bool = False          # 저점 상승 중인지

    # 2. 매물대 밀집도
    resistance_density: float = 0.0    # 0~1 (1=매우 밀집)
    resistance_count: int = 0          # TP까지 저항 개수
    nearest_resistance_dist: float = 0.0  # 가장 가까운 저항까지 거리(%)

    # 3. 레인지/박스권 감지
    market_regime: MarketRegime = MarketRegime.TRENDING_UP
    range_bound_score: float = 0.0     # 0~1 (1=완전 박스권)
    range_high: float = 0.0            # 박스 상단
    range_low: float = 0.0             # 박스 하단
    days_in_range: int = 0             # 박스권 기간(일)

    # 4. 하락폭 대비 위치
    drawdown_from_high: float = 0.0    # 고점 대비 하락률(%)
    position_in_range: float = 0.0     # 0=바닥, 1=천장
    recovery_ratio: float = 0.0        # 저점 대비 회복률(%)

    # 종합 평가
    context_score: int = 0             # 컨텍스트 점수 (0~100, 높을수록 좋음)
    context_grade: str = "C"           # S/A/B/C
    warnings: List[str] = field(default_factory=list)

    def get_summary(self) -> str:
        """컨텍스트 요약"""
        parts = []

        # 추세
        trend_labels = {
            TrendDirection.STRONG_UP: "강한상승",
            TrendDirection.UP: "상승",
            TrendDirection.NEUTRAL: "횡보",
            TrendDirection.DOWN: "하락",
            TrendDirection.STRONG_DOWN: "강한하락",
        }
        parts.append(trend_labels.get(self.weekly_trend, "?"))

        # 레인지
        if self.market_regime == MarketRegime.RANGE_BOUND:
            parts.append(f"박스권({self.days_in_range}일)")

        # 위치
        if self.drawdown_from_high > 20:
            parts.append(f"고점-{self.drawdown_from_high:.0f}%")

        # 매물대
        if self.resistance_density > 0.5:
            parts.append(f"저항밀집({self.resistance_count}개)")

        return " | ".join(parts) if parts else "분석없음"


@dataclass
class ConfluenceSignal:
    """컨플루언스 시그널"""
    symbol: str
    poi: POI
    direction: PatternDirection
    state: SignalState = SignalState.NONE

    # 점수 구성 (총 100점)
    zone_proximity_score: int = 0    # 존 접근 (0~20)
    zone_quality_score: int = 0      # 존 품질 (0~25)
    trigger_score: int = 0           # 트리거 캔들 (0~20)
    confirmation_score: int = 0      # 추가 확인 PA/Double/Liquidity (0~25)
    htf_alignment_score: int = 0     # HTF 정렬 (0~10)
    risk_penalty: int = 0            # 위험도 (-10~0)
    total_score: int = 0

    # 트리거 정보
    trigger: Optional[TriggerCandle] = None
    confirmations: List[ConfirmationSignal] = field(default_factory=list)

    # 트레이딩 정보
    current_price: float = 0.0
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    risk_reward_1: float = 0.0

    # 메타
    distance_to_zone_pct: float = 0.0
    opposing_zone_distance: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    is_fresh_entry: bool = False  # 방금 존에 진입한 상태

    # 시장 컨텍스트
    context: Optional[MarketContext] = None

    def __post_init__(self):
        self._calc_total()

    def _calc_total(self):
        self.total_score = max(0, min(100, (
            self.zone_proximity_score +
            self.zone_quality_score +
            self.trigger_score +
            self.confirmation_score +
            self.htf_alignment_score +
            self.risk_penalty
        )))

    def recalc_total(self):
        self._calc_total()

    @property
    def grade(self) -> str:
        """총점 기반 등급"""
        if self.total_score >= 75:
            return "S"
        elif self.total_score >= 60:
            return "A"
        elif self.total_score >= 45:
            return "B"
        else:
            return "C"

    @property
    def trigger_label(self) -> str:
        """트리거 라벨"""
        if not self.trigger:
            return "WAIT"
        labels = {
            TriggerStrength.STRONG: "◆ IBFB",
            TriggerStrength.MEDIUM: "▲ PIN/ENG",
            TriggerStrength.WEAK: "● DOJI",
        }
        return labels.get(self.trigger.strength, "?")

    @property
    def status_icon(self) -> str:
        if self.state == SignalState.GO:
            return "🔥" if self.total_score >= 60 else "✓"
        elif self.state == SignalState.WAIT:
            return "⏳"
        return ""

    @property
    def confirmation_summary(self) -> str:
        """확인 시그널 요약"""
        if not self.confirmations:
            return "-"
        names = [c.pattern_type for c in self.confirmations[:3]]
        return ", ".join(names)

    @property
    def context_summary(self) -> str:
        """컨텍스트 요약"""
        if not self.context:
            return "-"
        return self.context.get_summary()

    @property
    def context_warnings(self) -> List[str]:
        """컨텍스트 경고"""
        if not self.context:
            return []
        return self.context.warnings

    @property
    def context_grade(self) -> str:
        """컨텍스트 등급"""
        if not self.context:
            return "?"
        return self.context.context_grade

    def to_dict(self) -> Dict:
        result = {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "state": self.state.value,
            "poi_type": self.poi.poi_type.value,
            "zone_top": self.poi.top,
            "zone_bottom": self.poi.bottom,
            "zone_grade": self.poi.grade,
            "golden_level": self.poi.golden_level,
            "distance_pct": self.distance_to_zone_pct,
            "total_score": self.total_score,
            "grade": self.grade,
            "trigger": self.trigger_label,
            "confirmations": self.confirmation_summary,
            "confirmation_score": self.confirmation_score,
            "entry": self.entry_price,
            "stop_loss": self.stop_loss,
            "tp1": self.take_profit_1,
            "rr1": self.risk_reward_1,
            "risk": "⚠️" if self.risk_penalty < -5 else "OK",
            "fresh_entry": self.is_fresh_entry,
            "context_summary": self.context_summary,
            "context_grade": self.context_grade,
        }
        if self.context:
            result["context_warnings"] = self.context.warnings
            result["weekly_trend"] = self.context.weekly_trend.value
            result["drawdown"] = f"{self.context.drawdown_from_high:.1f}%"
            result["range_bound"] = self.context.market_regime == MarketRegime.RANGE_BOUND
        return result


@dataclass
class ConfluenceConfig:
    """컨플루언스 스크리너 설정"""
    # Zone 접근 설정
    max_distance_pct: float = 5.0
    ideal_distance_pct: float = 1.0

    # 최소 기준
    min_zone_grade: str = "C"
    min_total_score: int = 35

    # 컨텍스트 필터
    use_context_filter: bool = True           # 컨텍스트 분석 사용
    min_context_grade: str = "C"              # 최소 컨텍스트 등급
    exclude_range_bound: bool = False         # 박스권 종목 제외
    exclude_high_drawdown: bool = False       # 큰 하락 후 종목 제외
    max_drawdown_pct: float = 30.0            # 하락폭 기준
    exclude_dense_resistance: bool = False    # 저항 밀집 종목 제외
    require_trigger: bool = False    # True면 GO만 표시

    # 방향 필터
    direction_filter: str = "all"

    # 존 설정
    include_demand: bool = True
    include_supply: bool = True
    only_fresh_zones: bool = False
    only_golden_zones: bool = False

    # Fresh Entry 필터 (신규)
    fresh_entry_only: bool = False    # True면 방금 존에 진입한 종목만
    entry_lookback: int = 5           # 이전 N봉은 존 밖에 있어야 함
    entry_tolerance: float = 0.5      # 존 진입 허용 거리 (%)

    # HTF 설정
    use_htf_filter: bool = True

    # 감지기 설정
    smc_swing_length: int = 5
    smc_min_score: int = 4
    lookback_bars: int = 10


class ConfluenceScreener:
    """컨플루언스 기반 스크리너 v2"""

    def __init__(self, config: ConfluenceConfig = None):
        self.config = config or ConfluenceConfig()

        self.smc_detector = SMCDetector(
            swing_length=self.config.smc_swing_length,
            min_score=self.config.smc_min_score,
            min_grade="C",
        )

        self.pa_detector = PriceActionDetector(
            use_trend_filter=True,
        )

        self.liq_detector = LiquidityDetector(
            lookback=20,
            threshold_pct=0.3,
        )

        self.dp_detector = DoublePatternDetector(
            tolerance=0.03,
        )

    def _is_fresh_zone_entry(
        self,
        df: pd.DataFrame,
        poi: POI,
        lookback: int = 5,
        tolerance: float = 0.5,
    ) -> bool:
        """
        존에 '방금' 진입했는지 확인 (Fresh Entry)

        조건:
        1. 현재 가격이 존 안에 있거나 tolerance% 이내
        2. 이전 lookback 봉은 존 밖에 있었음

        Args:
            df: OHLCV DataFrame
            poi: 체크할 POI
            lookback: 이전 N봉 체크 (기본 5)
            tolerance: 존 진입 허용 거리 % (기본 0.5)

        Returns:
            True면 방금 진입한 상태
        """
        if len(df) < lookback + 2:
            return False

        current_price = df['close'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]

        # 1. 현재 존에 있거나 tolerance% 이내인지 확인
        in_zone_now = poi.is_price_in_zone(current_price)
        near_zone_now = poi.distance_pct(current_price) <= tolerance

        # 현재 캔들이 존을 터치했는지 (위크 포함)
        touched_zone = (current_low <= poi.top and current_high >= poi.bottom)

        if not (in_zone_now or near_zone_now or touched_zone):
            return False

        # 2. 이전 lookback 봉이 존 밖에 있었는지 확인
        is_demand = poi.poi_type in [POIType.DEMAND_ZONE, POIType.ORDER_BLOCK_BULL]

        for i in range(-lookback - 1, -1):  # -6 ~ -2 (최근 1봉 제외)
            if abs(i) > len(df):
                continue

            past_low = df['low'].iloc[i]
            past_high = df['high'].iloc[i]
            past_close = df['close'].iloc[i]

            if is_demand:
                # Demand Zone: 가격이 위에서 내려와야 함
                # 이전 봉이 존 상단보다 위에 있어야 함 (존에 안 닿았어야 함)
                if past_low <= poi.top:
                    # 이미 존에 닿았었음 → Fresh가 아님
                    return False
            else:
                # Supply Zone: 가격이 아래서 올라와야 함
                # 이전 봉이 존 하단보다 아래에 있어야 함
                if past_high >= poi.bottom:
                    # 이미 존에 닿았었음 → Fresh가 아님
                    return False

        return True

    def _identify_pois(self, df: pd.DataFrame) -> List[POI]:
        """POI(관심지점) 식별"""
        pois = []

        try:
            result = self.smc_detector.detect_all(df)
            order_blocks = result.get("order_blocks", [])

            for ob in order_blocks:
                grade_order = {"S": 4, "A": 3, "B": 2, "C": 1}
                min_grade_val = grade_order.get(self.config.min_zone_grade, 1)
                ob_grade_val = grade_order.get(ob.grade, 0)

                if ob_grade_val < min_grade_val:
                    continue

                is_fresh = not ob.is_mitigated
                if self.config.only_fresh_zones and not is_fresh:
                    continue

                # 골든존 레벨 판정 (피보나치)
                golden_level = self._check_golden_level(df, ob.top, ob.bottom)
                is_golden = golden_level > 0

                if self.config.only_golden_zones and not is_golden:
                    continue

                if ob.zone_type == ZoneType.DEMAND:
                    if not self.config.include_demand:
                        continue
                    poi_type = POIType.ORDER_BLOCK_BULL
                else:
                    if not self.config.include_supply:
                        continue
                    poi_type = POIType.ORDER_BLOCK_BEAR

                pois.append(POI(
                    poi_type=poi_type,
                    top=ob.top,
                    bottom=ob.bottom,
                    grade=ob.grade,
                    score=ob.score,
                    bar_index=ob.start_bar,
                    is_golden=is_golden,
                    golden_level=golden_level,
                    is_choch=ob.is_choch,
                    is_fresh=is_fresh,
                    impulse_size=ob.impulse_size,
                    base_candles=ob.base_candles,
                ))
        except Exception as e:
            logger.warning(f"POI 식별 오류: {e}")

        return pois

    def _check_golden_level(self, df: pd.DataFrame, ob_top: float, ob_bottom: float) -> int:
        """
        골든존 레벨 체크 (최근 스윙 기준)
        Returns: 0=없음, 1=38.2%, 2=50%, 3=61.8%
        """
        try:
            lookback = 50
            if len(df) < lookback:
                return 0

            recent = df.tail(lookback)
            swing_high = recent['high'].max()
            swing_low = recent['low'].min()
            range_size = swing_high - swing_low

            if range_size <= 0:
                return 0

            # 피보나치 레벨 계산 (하락 후 반등 시나리오 - Demand)
            fib_382 = swing_high - (range_size * 0.382)
            fib_500 = swing_high - (range_size * 0.500)
            fib_618 = swing_high - (range_size * 0.618)

            ob_mid = (ob_top + ob_bottom) / 2

            # 존이 해당 레벨과 겹치는지 체크
            if ob_bottom <= fib_618 <= ob_top:
                return 3  # 61.8% - 최고
            elif ob_bottom <= fib_500 <= ob_top:
                return 2  # 50%
            elif ob_bottom <= fib_382 <= ob_top:
                return 1  # 38.2%

            return 0
        except:
            return 0

    def _detect_trigger_candle(
        self,
        df: pd.DataFrame,
        expected_direction: PatternDirection,
    ) -> Optional[TriggerCandle]:
        """
        확인 캔들 감지 (강도순: IBFB > PIN/ENG > DOJI)
        """
        if len(df) < 5:
            return None

        try:
            # 최근 3개 캔들 분석
            c0_open, c0_high, c0_low, c0_close = df['open'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1], df['close'].iloc[-1]
            c1_open, c1_high, c1_low, c1_close = df['open'].iloc[-2], df['high'].iloc[-2], df['low'].iloc[-2], df['close'].iloc[-2]
            c2_high, c2_low = df['high'].iloc[-3], df['low'].iloc[-3]

            body_0 = abs(c0_close - c0_open)
            range_0 = c0_high - c0_low
            body_1 = abs(c1_close - c1_open)
            range_1 = c1_high - c1_low

            is_bullish_0 = c0_close > c0_open
            is_bearish_0 = c0_close < c0_open
            is_bullish_1 = c1_close > c1_open
            is_bearish_1 = c1_close < c1_open

            atr = df['high'].tail(14).mean() - df['low'].tail(14).mean()
            if atr <= 0:
                atr = range_0

            # === IBFB (Inside Bar False Breakout) - 강도 3 ===
            is_inside_bar = c1_high < c2_high and c1_low > c2_low

            if expected_direction == PatternDirection.BULLISH:
                # Bullish IBFB: Inside Bar + False Breakout 아래로 + 회복
                if is_inside_bar and c0_low < c1_low and c0_close > c1_low and is_bullish_0:
                    return TriggerCandle(
                        trigger_type="ibfb",
                        strength=TriggerStrength.STRONG,
                        direction=PatternDirection.BULLISH,
                        bar_index=len(df) - 1,
                        details="Inside Bar False Breakout - 가장 강한 반전 신호",
                    )

                # Bullish Pinbar
                if range_0 > 0:
                    lower_wick = min(c0_open, c0_close) - c0_low
                    if lower_wick / range_0 >= 0.6:
                        return TriggerCandle(
                            trigger_type="pinbar",
                            strength=TriggerStrength.MEDIUM,
                            direction=PatternDirection.BULLISH,
                            bar_index=len(df) - 1,
                            details="핀바/해머 - 긴 아래꼬리",
                        )

                # Bullish Engulfing
                if is_bearish_1 and is_bullish_0 and c0_close > c1_open and c0_open < c1_close:
                    return TriggerCandle(
                        trigger_type="engulfing",
                        strength=TriggerStrength.MEDIUM,
                        direction=PatternDirection.BULLISH,
                        bar_index=len(df) - 1,
                        details="상승 잉걸핑 - 이전 음봉 감싸기",
                    )

                # Bullish Doji + 확인
                if range_1 > 0 and body_1 / range_1 < 0.1:
                    if is_bullish_0 and body_0 > atr * 0.3:
                        return TriggerCandle(
                            trigger_type="doji",
                            strength=TriggerStrength.WEAK,
                            direction=PatternDirection.BULLISH,
                            bar_index=len(df) - 1,
                            details="도지 후 양봉 확인",
                        )

            else:  # BEARISH
                # Bearish IBFB
                if is_inside_bar and c0_high > c1_high and c0_close < c1_high and is_bearish_0:
                    return TriggerCandle(
                        trigger_type="ibfb",
                        strength=TriggerStrength.STRONG,
                        direction=PatternDirection.BEARISH,
                        bar_index=len(df) - 1,
                        details="Inside Bar False Breakout - 가장 강한 반전 신호",
                    )

                # Bearish Pinbar
                if range_0 > 0:
                    upper_wick = c0_high - max(c0_open, c0_close)
                    if upper_wick / range_0 >= 0.6:
                        return TriggerCandle(
                            trigger_type="pinbar",
                            strength=TriggerStrength.MEDIUM,
                            direction=PatternDirection.BEARISH,
                            bar_index=len(df) - 1,
                            details="핀바/슈팅스타 - 긴 위꼬리",
                        )

                # Bearish Engulfing
                if is_bullish_1 and is_bearish_0 and c0_close < c1_open and c0_open > c1_close:
                    return TriggerCandle(
                        trigger_type="engulfing",
                        strength=TriggerStrength.MEDIUM,
                        direction=PatternDirection.BEARISH,
                        bar_index=len(df) - 1,
                        details="하락 잉걸핑 - 이전 양봉 감싸기",
                    )

                # Bearish Doji + 확인
                if range_1 > 0 and body_1 / range_1 < 0.1:
                    if is_bearish_0 and body_0 > atr * 0.3:
                        return TriggerCandle(
                            trigger_type="doji",
                            strength=TriggerStrength.WEAK,
                            direction=PatternDirection.BEARISH,
                            bar_index=len(df) - 1,
                            details="도지 후 음봉 확인",
                        )

        except Exception as e:
            logger.debug(f"트리거 감지 오류: {e}")

        return None

    def _check_htf_alignment(self, df: pd.DataFrame, direction: PatternDirection) -> Tuple[bool, int]:
        """HTF 추세 정렬 체크"""
        try:
            if len(df) < 50:
                return True, 5

            # 간단한 HTF 추세 판단: MA50 기준
            ma50 = df['close'].tail(50).mean()
            current = df['close'].iloc[-1]

            if direction == PatternDirection.BULLISH:
                aligned = current > ma50
            else:
                aligned = current < ma50

            score = 10 if aligned else 0
            return aligned, score
        except:
            return True, 5

    def _find_opposing_zone(
        self,
        pois: List[POI],
        current_price: float,
        for_bullish: bool,
    ) -> float:
        """반대 존까지의 거리 (%)"""
        min_distance = 100.0

        for poi in pois:
            if for_bullish:
                # 롱 진입 시 위쪽 Supply 존 체크
                if poi.poi_type in [POIType.SUPPLY_ZONE, POIType.ORDER_BLOCK_BEAR]:
                    if poi.bottom > current_price:
                        dist = (poi.bottom - current_price) / current_price * 100
                        min_distance = min(min_distance, dist)
            else:
                # 숏 진입 시 아래쪽 Demand 존 체크
                if poi.poi_type in [POIType.DEMAND_ZONE, POIType.ORDER_BLOCK_BULL]:
                    if poi.top < current_price:
                        dist = (current_price - poi.top) / current_price * 100
                        min_distance = min(min_distance, dist)

        return min_distance

    def _analyze_market_context(
        self,
        df: pd.DataFrame,
        direction: PatternDirection,
        entry_price: float,
        tp1_price: float,
    ) -> MarketContext:
        """
        시장 컨텍스트 분석 (장기추세, 매물대, 박스권, 하락폭)
        """
        context = MarketContext()
        warnings = []

        try:
            # === 1. 장기 추세 분석 (주봉 시뮬레이션 - 5일 리샘플링) ===
            weekly_trend, ma_dir, hh, hl = self._analyze_weekly_trend(df)
            context.weekly_trend = weekly_trend
            context.weekly_ma_direction = ma_dir
            context.higher_highs = hh
            context.higher_lows = hl

            # 추세와 진입 방향 불일치 경고
            if direction == PatternDirection.BULLISH:
                if weekly_trend in [TrendDirection.DOWN, TrendDirection.STRONG_DOWN]:
                    warnings.append("⚠️ 주간 하락추세에서 롱 진입")
            else:
                if weekly_trend in [TrendDirection.UP, TrendDirection.STRONG_UP]:
                    warnings.append("⚠️ 주간 상승추세에서 숏 진입")

            # === 2. 매물대 밀집도 분석 ===
            res_density, res_count, nearest_dist = self._analyze_resistance_density(
                df, entry_price, tp1_price, direction
            )
            context.resistance_density = res_density
            context.resistance_count = res_count
            context.nearest_resistance_dist = nearest_dist

            if res_density > 0.6:
                warnings.append(f"⚠️ TP까지 저항 밀집 ({res_count}개)")
            elif res_density > 0.3:
                warnings.append(f"⚡ 저항대 존재 ({res_count}개)")

            # === 3. 박스권/레인지 감지 ===
            regime, range_score, r_high, r_low, days = self._detect_range_bound(df)
            context.market_regime = regime
            context.range_bound_score = range_score
            context.range_high = r_high
            context.range_low = r_low
            context.days_in_range = days

            if regime == MarketRegime.RANGE_BOUND and days > 60:
                warnings.append(f"⚠️ 장기 박스권 ({days}일)")
            elif regime == MarketRegime.RANGE_BOUND:
                warnings.append(f"📦 박스권 ({days}일)")

            # === 4. 하락폭 대비 위치 ===
            drawdown, pos_in_range, recovery = self._analyze_drawdown_position(df)
            context.drawdown_from_high = drawdown
            context.position_in_range = pos_in_range
            context.recovery_ratio = recovery

            if drawdown > 40:
                warnings.append(f"⚠️ 고점 대비 -{drawdown:.0f}% (매물대 많음)")
            elif drawdown > 25:
                warnings.append(f"⚡ 고점 대비 -{drawdown:.0f}%")

            # === 컨텍스트 점수 계산 ===
            context.context_score = self._calc_context_score(context, direction)
            context.context_grade = self._grade_context(context.context_score)
            context.warnings = warnings

        except Exception as e:
            logger.warning(f"컨텍스트 분석 오류: {e}")
            context.warnings = ["분석 오류"]

        return context

    def _analyze_weekly_trend(self, df: pd.DataFrame) -> Tuple[TrendDirection, str, bool, bool]:
        """주봉 추세 분석"""
        if len(df) < 50:
            return TrendDirection.NEUTRAL, "flat", False, False

        # 20일(약 4주) MA와 50일(약 10주) MA
        ma20 = df['close'].rolling(20).mean()
        ma50 = df['close'].rolling(50).mean()

        current_price = df['close'].iloc[-1]
        ma20_now = ma20.iloc[-1]
        ma50_now = ma50.iloc[-1]
        ma20_prev = ma20.iloc[-10] if len(ma20) > 10 else ma20_now
        ma50_prev = ma50.iloc[-10] if len(ma50) > 10 else ma50_now

        # MA 방향
        ma_rising = ma20_now > ma20_prev and ma50_now > ma50_prev
        ma_falling = ma20_now < ma20_prev and ma50_now < ma50_prev

        if ma_rising:
            ma_dir = "up"
        elif ma_falling:
            ma_dir = "down"
        else:
            ma_dir = "flat"

        # 고점/저점 분석 (최근 60일)
        recent = df.tail(60)
        highs = recent['high'].rolling(10).max()
        lows = recent['low'].rolling(10).min()

        # Higher Highs / Higher Lows 체크
        mid_idx = len(recent) // 2
        first_half_high = recent['high'].iloc[:mid_idx].max()
        second_half_high = recent['high'].iloc[mid_idx:].max()
        first_half_low = recent['low'].iloc[:mid_idx].min()
        second_half_low = recent['low'].iloc[mid_idx:].min()

        higher_highs = second_half_high > first_half_high
        higher_lows = second_half_low > first_half_low
        lower_highs = second_half_high < first_half_high
        lower_lows = second_half_low < first_half_low

        # 추세 판정
        if current_price > ma20_now > ma50_now and ma_rising and higher_highs and higher_lows:
            trend = TrendDirection.STRONG_UP
        elif current_price > ma50_now and (ma_rising or higher_lows):
            trend = TrendDirection.UP
        elif current_price < ma20_now < ma50_now and ma_falling and lower_highs and lower_lows:
            trend = TrendDirection.STRONG_DOWN
        elif current_price < ma50_now and (ma_falling or lower_highs):
            trend = TrendDirection.DOWN
        else:
            trend = TrendDirection.NEUTRAL

        return trend, ma_dir, higher_highs, higher_lows

    def _analyze_resistance_density(
        self,
        df: pd.DataFrame,
        entry_price: float,
        tp_price: float,
        direction: PatternDirection,
    ) -> Tuple[float, int, float]:
        """매물대 밀집도 분석"""
        if len(df) < 100:
            return 0.0, 0, 100.0

        # 가격 범위 설정
        if direction == PatternDirection.BULLISH:
            price_low = entry_price
            price_high = tp_price
        else:
            price_low = tp_price
            price_high = entry_price

        if price_high <= price_low:
            return 0.0, 0, 100.0

        # 과거 데이터에서 저항/지지 레벨 찾기
        lookback = min(200, len(df))
        hist_data = df.tail(lookback)

        # 피봇 포인트 찾기 (스윙 고/저점)
        resistance_levels = []

        for i in range(5, len(hist_data) - 5):
            # 스윙 고점 (저항)
            if direction == PatternDirection.BULLISH:
                high = hist_data['high'].iloc[i]
                is_swing = all(high >= hist_data['high'].iloc[i-5:i]) and all(high >= hist_data['high'].iloc[i+1:i+6])
                if is_swing and price_low < high < price_high:
                    resistance_levels.append(high)

            # 스윙 저점 (지지) - 숏의 경우
            else:
                low = hist_data['low'].iloc[i]
                is_swing = all(low <= hist_data['low'].iloc[i-5:i]) and all(low <= hist_data['low'].iloc[i+1:i+6])
                if is_swing and price_low < low < price_high:
                    resistance_levels.append(low)

        # 중복 레벨 병합 (1% 이내)
        merged_levels = []
        for level in sorted(resistance_levels):
            if not merged_levels or (level - merged_levels[-1]) / merged_levels[-1] > 0.01:
                merged_levels.append(level)

        count = len(merged_levels)
        price_range = price_high - price_low

        # 밀집도 계산 (레벨 수 / 가격 범위)
        if price_range > 0:
            # 정규화: 5% 범위에 3개 이상이면 밀집
            density = min(1.0, count / 3.0 * (0.05 / (price_range / entry_price)))
        else:
            density = 0.0

        # 가장 가까운 저항까지 거리
        if merged_levels:
            if direction == PatternDirection.BULLISH:
                nearest = min(merged_levels)
                nearest_dist = (nearest - entry_price) / entry_price * 100
            else:
                nearest = max(merged_levels)
                nearest_dist = (entry_price - nearest) / entry_price * 100
        else:
            nearest_dist = 100.0

        return density, count, max(0, nearest_dist)

    def _detect_range_bound(self, df: pd.DataFrame) -> Tuple[MarketRegime, float, float, float, int]:
        """박스권/레인지 감지"""
        if len(df) < 60:
            return MarketRegime.TRENDING_UP, 0.0, 0.0, 0.0, 0

        # 최근 120일 (약 6개월) 분석
        lookback = min(120, len(df))
        recent = df.tail(lookback)

        highest = recent['high'].max()
        lowest = recent['low'].min()
        # 0으로 나누기 방지
        range_size = (highest - lowest) / lowest * 100 if lowest > 0 else 0

        current_price = df['close'].iloc[-1]

        # ATR 기반 변동성
        atr = (recent['high'] - recent['low']).mean()
        atr_pct = atr / current_price * 100

        # 박스권 판정 기준
        # 1. 전체 범위가 20% 이내
        # 2. ATR이 2% 이내
        # 3. 가격이 범위의 중간 40%에 있었던 비율

        in_middle_count = 0
        middle_low = lowest + (highest - lowest) * 0.3
        middle_high = lowest + (highest - lowest) * 0.7

        for i in range(len(recent)):
            close = recent['close'].iloc[i]
            if middle_low <= close <= middle_high:
                in_middle_count += 1

        middle_ratio = in_middle_count / len(recent)

        # 박스권 점수 계산
        range_score = 0.0

        if range_size < 15:
            range_score += 0.3
        elif range_size < 25:
            range_score += 0.15

        if middle_ratio > 0.6:
            range_score += 0.4
        elif middle_ratio > 0.4:
            range_score += 0.2

        if atr_pct < 1.5:
            range_score += 0.3
        elif atr_pct < 2.5:
            range_score += 0.15

        # 레짐 결정
        if range_score >= 0.6:
            regime = MarketRegime.RANGE_BOUND
        elif atr_pct > 4:
            regime = MarketRegime.VOLATILE
        else:
            # MA 기반 추세 판단
            ma50 = recent['close'].rolling(50).mean().iloc[-1]
            if current_price > ma50 * 1.02:
                regime = MarketRegime.TRENDING_UP
            elif current_price < ma50 * 0.98:
                regime = MarketRegime.TRENDING_DOWN
            else:
                regime = MarketRegime.RANGE_BOUND

        # 박스권 기간 추정
        days_in_range = 0
        if regime == MarketRegime.RANGE_BOUND:
            # 가격이 범위 내에 있었던 연속 기간
            for i in range(len(df) - 1, -1, -1):
                high = df['high'].iloc[i]
                low = df['low'].iloc[i]
                if low >= lowest * 0.98 and high <= highest * 1.02:
                    days_in_range += 1
                else:
                    break

        return regime, range_score, highest, lowest, days_in_range

    def _analyze_drawdown_position(self, df: pd.DataFrame) -> Tuple[float, float, float]:
        """하락폭 대비 현재 위치 분석"""
        if len(df) < 50:
            return 0.0, 0.5, 0.0

        # 1년(약 252일) 또는 전체 데이터
        lookback = min(252, len(df))
        data = df.tail(lookback)

        highest = data['high'].max()
        lowest = data['low'].min()
        current = df['close'].iloc[-1]

        # 고점 대비 하락률
        drawdown = (highest - current) / highest * 100

        # 범위 내 위치 (0=바닥, 1=천장)
        if highest > lowest:
            position = (current - lowest) / (highest - lowest)
        else:
            position = 0.5

        # 저점 대비 회복률
        if lowest > 0:
            recovery = (current - lowest) / lowest * 100
        else:
            recovery = 0.0

        return drawdown, position, recovery

    def _calc_context_score(self, ctx: MarketContext, direction: PatternDirection) -> int:
        """컨텍스트 점수 계산 (0~100)"""
        score = 50  # 기본 점수

        # 1. 추세 점수 (-20 ~ +20)
        trend_scores = {
            TrendDirection.STRONG_UP: 20 if direction == PatternDirection.BULLISH else -20,
            TrendDirection.UP: 10 if direction == PatternDirection.BULLISH else -10,
            TrendDirection.NEUTRAL: 0,
            TrendDirection.DOWN: -10 if direction == PatternDirection.BULLISH else 10,
            TrendDirection.STRONG_DOWN: -20 if direction == PatternDirection.BULLISH else 20,
        }
        score += trend_scores.get(ctx.weekly_trend, 0)

        # 2. 박스권 페널티 (-15 ~ 0)
        if ctx.market_regime == MarketRegime.RANGE_BOUND:
            if ctx.days_in_range > 90:
                score -= 15
            elif ctx.days_in_range > 60:
                score -= 10
            else:
                score -= 5

        # 3. 매물대 밀집도 페널티 (-15 ~ 0)
        if ctx.resistance_density > 0.7:
            score -= 15
        elif ctx.resistance_density > 0.5:
            score -= 10
        elif ctx.resistance_density > 0.3:
            score -= 5

        # 4. 하락폭 페널티 (-15 ~ 0)
        # 롱 진입 시 큰 하락 후면 위험 (매물대 많음)
        if direction == PatternDirection.BULLISH:
            if ctx.drawdown_from_high > 40:
                score -= 15
            elif ctx.drawdown_from_high > 30:
                score -= 10
            elif ctx.drawdown_from_high > 20:
                score -= 5

        # 범위 제한
        return max(0, min(100, score))

    def _grade_context(self, score: int) -> str:
        """컨텍스트 등급"""
        if score >= 70:
            return "S"
        elif score >= 55:
            return "A"
        elif score >= 40:
            return "B"
        else:
            return "C"

    def _detect_confirmations(
        self,
        df: pd.DataFrame,
        expected_direction: PatternDirection,
        lookback_bars: int = 10,
    ) -> List[ConfirmationSignal]:
        """
        추가 확인 시그널 감지 (Price Action, Double Pattern, Liquidity)
        """
        confirmations = []

        try:
            # 1. Price Action 패턴 (핀바, 잉걸핑, 스타, 삼병)
            pa_signals = self.pa_detector.get_latest_signals(
                df,
                lookback_bars=lookback_bars,
                patterns=["pinbar", "engulfing", "star", "three_soldiers"],
            )
            for sig in pa_signals:
                if sig.direction == expected_direction:
                    # 점수 배분: 강도에 따라 5~10점
                    score = 10 if sig.strength == PatternStrength.STRONG else (7 if sig.strength == PatternStrength.MODERATE else 5)
                    confirmations.append(ConfirmationSignal(
                        pattern_type=sig.pattern_type,
                        category="price_action",
                        direction=sig.direction,
                        score=score,
                        details=sig.rationale[:50] if sig.rationale else sig.pattern_type,
                    ))
        except Exception as e:
            logger.debug(f"PA 확인 감지 오류: {e}")

        try:
            # 2. Double Pattern (쌍바닥, 쌍봉)
            dp_signals = self.dp_detector.get_latest_signals(
                df,
                lookback_bars=lookback_bars,
            )
            for sig in dp_signals:
                if sig.direction == expected_direction:
                    # Double Pattern은 신뢰도 높음: 8~12점
                    score = 12 if sig.confidence >= 70 else (10 if sig.confidence >= 60 else 8)
                    confirmations.append(ConfirmationSignal(
                        pattern_type=sig.pattern_type,
                        category="double_pattern",
                        direction=sig.direction,
                        score=score,
                        details=sig.rationale[:50] if sig.rationale else sig.pattern_type,
                    ))
        except Exception as e:
            logger.debug(f"Double Pattern 확인 감지 오류: {e}")

        try:
            # 3. Liquidity Sweep
            liq_signals = self.liq_detector.get_latest_signals(
                df,
                lookback_bars=lookback_bars,
            )
            for sig in liq_signals:
                if sig.direction == expected_direction:
                    # Liquidity Sweep은 매우 강한 신호: 10~15점
                    score = 15 if sig.confidence >= 75 else (12 if sig.confidence >= 65 else 10)
                    confirmations.append(ConfirmationSignal(
                        pattern_type=sig.pattern_type,
                        category="liquidity",
                        direction=sig.direction,
                        score=score,
                        details=sig.rationale[:50] if sig.rationale else "유동성 스윕",
                    ))
        except Exception as e:
            logger.debug(f"Liquidity 확인 감지 오류: {e}")

        # 점수순 정렬
        confirmations.sort(key=lambda x: x.score, reverse=True)
        return confirmations

    def _calc_scores(
        self,
        poi: POI,
        distance_pct: float,
        trigger: Optional[TriggerCandle],
        confirmations: List[ConfirmationSignal],
        htf_score: int,
        opposing_distance: float,
    ) -> Dict[str, int]:
        """점수 계산 (총 100점)"""
        scores = {}

        # 1. 존 접근 점수 (0~20)
        if distance_pct <= 0:
            scores['proximity'] = 20
        elif distance_pct <= self.config.ideal_distance_pct:
            scores['proximity'] = 18
        elif distance_pct <= self.config.max_distance_pct:
            ratio = 1 - (distance_pct - self.config.ideal_distance_pct) / (self.config.max_distance_pct - self.config.ideal_distance_pct)
            scores['proximity'] = int(8 + ratio * 10)
        else:
            scores['proximity'] = 0

        # 2. 존 품질 점수 (0~25)
        grade_score = {"S": 12, "A": 9, "B": 6, "C": 3}.get(poi.grade, 3)
        golden_score = {0: 0, 1: 3, 2: 5, 3: 7}.get(poi.golden_level, 0)
        choch_score = 4 if poi.is_choch else 0
        fresh_score = 2 if poi.is_fresh else 0

        scores['quality'] = min(25, grade_score + golden_score + choch_score + fresh_score)

        # 3. 트리거 점수 (0~20)
        scores['trigger'] = trigger.score if trigger else 0

        # 4. 추가 확인 점수 (0~25)
        conf_score = sum(c.score for c in confirmations)
        scores['confirmation'] = min(25, conf_score)

        # 5. HTF 정렬 점수 (0~10)
        scores['htf'] = htf_score

        # 6. 위험도 페널티 (-10~0)
        if opposing_distance < 2.0:
            scores['risk'] = -10
        elif opposing_distance < 3.0:
            scores['risk'] = -5
        elif opposing_distance < 5.0:
            scores['risk'] = -2
        else:
            scores['risk'] = 0

        # 총점 (최대 100)
        scores['total'] = max(0, min(100, sum(scores.values())))

        return scores

    def _calc_entry_sl_tp(
        self,
        poi: POI,
        current_price: float,
        direction: PatternDirection,
    ) -> Dict[str, float]:
        """Entry/SL/TP 계산"""
        if direction == PatternDirection.BULLISH:
            entry = poi.top
            sl = poi.bottom * 0.995
            risk = entry - sl
            tp1 = entry + risk * 1.5
            tp2 = entry + risk * 2.5
            tp3 = entry + risk * 4.0
            rr1 = 1.5
        else:
            entry = poi.bottom
            sl = poi.top * 1.005
            risk = sl - entry
            tp1 = entry - risk * 1.5
            tp2 = entry - risk * 2.5
            tp3 = entry - risk * 4.0
            rr1 = 1.5

        return {"entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3, "rr1": rr1}

    def screen_symbol(self, symbol: str, df: pd.DataFrame) -> List[ConfluenceSignal]:
        """단일 종목 스크리닝"""
        signals = []

        if df is None or len(df) < 50:
            return signals

        current_price = df['close'].iloc[-1]

        # 1. POI 식별
        pois = self._identify_pois(df)
        if not pois:
            return signals

        # 2. 각 POI 분석
        for poi in pois:
            distance_pct = poi.distance_pct(current_price)

            if distance_pct > self.config.max_distance_pct:
                continue

            # 방향 결정
            if poi.poi_type in [POIType.DEMAND_ZONE, POIType.ORDER_BLOCK_BULL]:
                direction = PatternDirection.BULLISH
                if current_price < poi.bottom:
                    continue
            else:
                direction = PatternDirection.BEARISH
                if current_price > poi.top:
                    continue

            # 방향 필터
            if self.config.direction_filter == "long" and direction != PatternDirection.BULLISH:
                continue
            if self.config.direction_filter == "short" and direction != PatternDirection.BEARISH:
                continue

            # Fresh Entry 체크: 방금 존에 진입했는지
            is_fresh_entry = self._is_fresh_zone_entry(
                df, poi,
                lookback=self.config.entry_lookback,
                tolerance=self.config.entry_tolerance,
            )

            # Fresh Entry 필터: 방금 존에 진입한 종목만
            if self.config.fresh_entry_only and not is_fresh_entry:
                continue

            # 트리거 감지
            trigger = self._detect_trigger_candle(df, direction)

            # 상태 결정
            is_in_zone = poi.is_price_in_zone(current_price) or distance_pct <= 1.0
            if trigger and is_in_zone:
                state = SignalState.GO
            elif is_in_zone:
                state = SignalState.WAIT
            else:
                state = SignalState.NONE

            # require_trigger 필터
            if self.config.require_trigger and state != SignalState.GO:
                continue

            # HTF 정렬
            htf_aligned, htf_score = self._check_htf_alignment(df, direction)
            if self.config.use_htf_filter and not htf_aligned:
                htf_score = 0

            # 반대 존 거리
            opposing_dist = self._find_opposing_zone(pois, current_price, direction == PatternDirection.BULLISH)

            # 추가 확인 시그널 감지 (PA, Double, Liquidity)
            confirmations = self._detect_confirmations(df, direction, self.config.lookback_bars)

            # 점수 계산 (트리거 + 확인 시그널 포함)
            scores = self._calc_scores(poi, distance_pct, trigger, confirmations, htf_score, opposing_dist)

            if scores['total'] < self.config.min_total_score:
                continue

            # Entry/SL/TP
            trade = self._calc_entry_sl_tp(poi, current_price, direction)

            # 컨텍스트 분석
            context = None
            if self.config.use_context_filter:
                context = self._analyze_market_context(
                    df, direction, trade['entry'], trade['tp1']
                )

                # 컨텍스트 기반 필터
                grade_order = {"S": 4, "A": 3, "B": 2, "C": 1}
                min_ctx_grade = grade_order.get(self.config.min_context_grade, 1)
                ctx_grade = grade_order.get(context.context_grade, 0)

                if ctx_grade < min_ctx_grade:
                    continue

                if self.config.exclude_range_bound and context.market_regime == MarketRegime.RANGE_BOUND:
                    continue

                if self.config.exclude_high_drawdown and context.drawdown_from_high > self.config.max_drawdown_pct:
                    continue

                if self.config.exclude_dense_resistance and context.resistance_density > 0.6:
                    continue

            signal = ConfluenceSignal(
                symbol=symbol,
                poi=poi,
                direction=direction,
                state=state,
                zone_proximity_score=scores['proximity'],
                zone_quality_score=scores['quality'],
                trigger_score=scores['trigger'],
                confirmation_score=scores['confirmation'],
                htf_alignment_score=scores['htf'],
                risk_penalty=scores['risk'],
                total_score=scores['total'],
                trigger=trigger,
                confirmations=confirmations,
                current_price=current_price,
                entry_price=trade['entry'],
                stop_loss=trade['sl'],
                take_profit_1=trade['tp1'],
                take_profit_2=trade['tp2'],
                take_profit_3=trade['tp3'],
                risk_reward_1=trade['rr1'],
                distance_to_zone_pct=distance_pct,
                opposing_zone_distance=opposing_dist,
                is_fresh_entry=is_fresh_entry,
                context=context,
            )

            signals.append(signal)

        signals.sort(key=lambda x: x.total_score, reverse=True)
        return signals

    def screen_universe(
        self,
        symbols: List[str],
        data_fetcher: Callable[[str], pd.DataFrame],
        workers: int = 5,
        progress_callback: Callable = None,
    ) -> List[ConfluenceSignal]:
        """유니버스 전체 스크리닝"""
        all_signals = []
        total = len(symbols)

        def process_symbol(symbol: str) -> List[ConfluenceSignal]:
            try:
                df = data_fetcher(symbol)
                if df is None or df.empty:
                    return []
                return self.screen_symbol(symbol, df)
            except Exception as e:
                logger.error(f"[{symbol}] 스크리닝 오류: {e}")
                return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_symbol, sym): sym for sym in symbols}

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                symbol = futures[future]
                try:
                    sigs = future.result()
                    all_signals.extend(sigs)
                    status = f"{len(sigs)} signals" if sigs else "No POI"
                except Exception as e:
                    status = "Error"

                if progress_callback:
                    progress_callback(i + 1, total, symbol, status)

        all_signals.sort(key=lambda x: x.total_score, reverse=True)
        return all_signals

    def get_summary(self, signals: List[ConfluenceSignal]) -> Dict:
        """결과 요약"""
        if not signals:
            return {"total_signals": 0, "go_signals": 0, "wait_signals": 0}

        go_signals = [s for s in signals if s.state == SignalState.GO]
        wait_signals = [s for s in signals if s.state == SignalState.WAIT]
        long_signals = [s for s in signals if s.direction == PatternDirection.BULLISH]
        short_signals = [s for s in signals if s.direction == PatternDirection.BEARISH]

        grade_dist = {}
        for s in signals:
            grade_dist[s.grade] = grade_dist.get(s.grade, 0) + 1

        trigger_dist = {}
        for s in signals:
            if s.trigger:
                t = s.trigger.trigger_type
                trigger_dist[t] = trigger_dist.get(t, 0) + 1

        # 확인 시그널 분포
        confirmation_dist = {}
        for s in signals:
            for c in s.confirmations:
                cat = c.category
                confirmation_dist[cat] = confirmation_dist.get(cat, 0) + 1

        return {
            "total_signals": len(signals),
            "go_signals": len(go_signals),
            "wait_signals": len(wait_signals),
            "long_signals": len(long_signals),
            "short_signals": len(short_signals),
            "avg_score": sum(s.total_score for s in signals) / len(signals),
            "top_score": max(s.total_score for s in signals),
            "avg_confirmation_score": sum(s.confirmation_score for s in signals) / len(signals),
            "grade_distribution": grade_dist,
            "trigger_distribution": trigger_dist,
            "confirmation_distribution": confirmation_dist,
            "top_symbols": [
                {
                    "symbol": s.symbol,
                    "score": s.total_score,
                    "grade": s.grade,
                    "state": s.state.value,
                    "direction": s.direction.value,
                }
                for s in signals[:10]
            ],
        }

    def to_dataframe(self, signals: List[ConfluenceSignal]) -> pd.DataFrame:
        """DataFrame으로 변환"""
        rows = []
        for sig in signals:
            state_icon = {"go": "🔥", "wait": "⏳", "none": ""}.get(sig.state.value, "")
            dir_icon = "🟢" if sig.direction == PatternDirection.BULLISH else "🔴"

            # 컨텍스트 정보
            ctx_grade = sig.context_grade if sig.context else "-"
            ctx_summary = ""
            if sig.context:
                parts = []
                # 추세
                trend_icons = {
                    TrendDirection.STRONG_UP: "📈📈",
                    TrendDirection.UP: "📈",
                    TrendDirection.NEUTRAL: "➡️",
                    TrendDirection.DOWN: "📉",
                    TrendDirection.STRONG_DOWN: "📉📉",
                }
                parts.append(trend_icons.get(sig.context.weekly_trend, "?"))
                # 박스권
                if sig.context.market_regime == MarketRegime.RANGE_BOUND:
                    parts.append("📦")
                # 하락폭
                if sig.context.drawdown_from_high > 25:
                    parts.append(f"-{sig.context.drawdown_from_high:.0f}%")
                # 저항
                if sig.context.resistance_density > 0.5:
                    parts.append(f"🧱{sig.context.resistance_count}")
                ctx_summary = " ".join(parts)

            rows.append({
                "상태": state_icon,
                "방향": dir_icon,
                "종목": sig.symbol,
                "Fresh": "🆕" if sig.is_fresh_entry else "",
                "존": sig.poi.grade,
                "골든": f"Lv{sig.poi.golden_level}" if sig.poi.is_golden else "-",
                "거리": f"{sig.distance_to_zone_pct:.1f}%",
                "트리거": sig.trigger_label,
                "확인": sig.confirmation_summary,
                "점수": sig.total_score,
                "등급": sig.grade,
                "컨텍스트": ctx_summary,
                "CTX": ctx_grade,
                "Entry": f"${sig.entry_price:.2f}",
                "SL": f"${sig.stop_loss:.2f}",
                "TP1": f"${sig.take_profit_1:.2f}",
                "위험": "⚠️" if sig.risk_penalty < -5 else "OK",
            })

        return pd.DataFrame(rows)


def quick_confluence_scan(
    symbols: List[str],
    data_fetcher: Callable[[str], pd.DataFrame],
    direction: str = "all",
    min_score: int = 35,
    require_trigger: bool = False,
    fresh_entry_only: bool = False,
    entry_lookback: int = 5,
    workers: int = 5,
    progress_callback: Callable = None,
) -> List[ConfluenceSignal]:
    """
    빠른 컨플루언스 스캔

    Args:
        fresh_entry_only: True면 방금 존에 진입한 종목만 필터링
        entry_lookback: Fresh Entry 체크 시 이전 N봉 확인 (기본 5)
    """
    config = ConfluenceConfig(
        direction_filter=direction,
        min_total_score=min_score,
        require_trigger=require_trigger,
        fresh_entry_only=fresh_entry_only,
        entry_lookback=entry_lookback,
    )

    screener = ConfluenceScreener(config)
    return screener.screen_universe(
        symbols=symbols,
        data_fetcher=data_fetcher,
        workers=workers,
        progress_callback=progress_callback,
    )
