"""
Price Action Patterns - 가격 행동 패턴 감지

패턴:
- Pin Bar (핀바/해머/슈팅스타)
- Engulfing (장악형)
- Morning/Evening Star (샛별/석별)
- Three White Soldiers / Three Black Crows (적삼병/흑삼병)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum


class PatternDirection(Enum):
    """패턴 방향"""
    BULLISH = "bullish"
    BEARISH = "bearish"


class PatternStrength(Enum):
    """패턴 강도"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass
class PatternSignal:
    """패턴 시그널"""
    pattern_type: str           # 패턴 유형
    direction: PatternDirection # 방향 (bullish/bearish)
    strength: PatternStrength   # 강도
    bar_index: int             # 발생 위치
    timestamp: Any             # 타임스탬프

    # 가격 정보
    entry_price: float         # 진입가
    stop_loss: float          # 손절가
    take_profit_1: float      # 익절1 (1:1 RR)
    take_profit_2: float      # 익절2 (1:2 RR)
    take_profit_3: float      # 익절3 (1:3 RR)

    # 리스크
    risk_amount: float        # 리스크 금액 (진입-손절)
    risk_reward_1: float = 1.0
    risk_reward_2: float = 2.0
    risk_reward_3: float = 3.0

    # 추가 정보
    confidence: float = 0.0   # 신뢰도 (0-100)
    rationale: str = ""       # 진입 근거
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "pattern": self.pattern_type,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "bar_index": self.bar_index,
            "timestamp": str(self.timestamp),
            "entry": self.entry_price,
            "stop_loss": self.stop_loss,
            "tp1": self.take_profit_1,
            "tp2": self.take_profit_2,
            "tp3": self.take_profit_3,
            "risk": self.risk_amount,
            "rr1": self.risk_reward_1,
            "rr2": self.risk_reward_2,
            "rr3": self.risk_reward_3,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


def _get_candle_data(df: pd.DataFrame, idx: int) -> Dict:
    """캔들 데이터 추출"""
    row = df.iloc[idx]
    o, h, l, c = row['open'], row['high'], row['low'], row['close']

    body_size = abs(c - o)
    candle_range = h - l
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    return {
        'open': o, 'high': h, 'low': l, 'close': c,
        'body_size': body_size,
        'candle_range': candle_range,
        'upper_wick': upper_wick,
        'lower_wick': lower_wick,
        'is_bullish': c > o,
        'is_bearish': c < o,
        'body_ratio': body_size / candle_range if candle_range > 0 else 0,
        'upper_wick_ratio': upper_wick / candle_range if candle_range > 0 else 0,
        'lower_wick_ratio': lower_wick / candle_range if candle_range > 0 else 0,
    }


def _calculate_entry_sl_tp(
    direction: PatternDirection,
    entry: float,
    candle_high: float,
    candle_low: float,
    atr: float = None,
    sl_buffer_ratio: float = 0.002,
) -> Tuple[float, float, float, float, float]:
    """진입/손절/익절 계산"""

    if direction == PatternDirection.BULLISH:
        # 롱 진입
        stop_loss = candle_low * (1 - sl_buffer_ratio)
        risk = entry - stop_loss
        tp1 = entry + risk * 1.0
        tp2 = entry + risk * 2.0
        tp3 = entry + risk * 3.0
    else:
        # 숏 진입
        stop_loss = candle_high * (1 + sl_buffer_ratio)
        risk = stop_loss - entry
        tp1 = entry - risk * 1.0
        tp2 = entry - risk * 2.0
        tp3 = entry - risk * 3.0

    return stop_loss, tp1, tp2, tp3, abs(risk)


def detect_pinbar(
    df: pd.DataFrame,
    tail_ratio: float = 2.0,
    body_position: float = 0.3,
    lookback: int = 5,
    use_trend_filter: bool = True,
) -> List[PatternSignal]:
    """
    핀바 패턴 감지

    Args:
        df: OHLCV DataFrame
        tail_ratio: 꼬리/몸통 비율 (기본 2.0)
        body_position: 몸통 위치 (0.3 = 상/하위 30%)
        lookback: 스윙 비교 기간
        use_trend_filter: 추세 필터 사용
    """
    signals = []

    if len(df) < lookback + 2:
        return signals

    # EMA for trend filter
    if use_trend_filter and 'ma20' not in df.columns:
        df = df.copy()
        df['ma20'] = df['close'].ewm(span=20).mean()

    for i in range(lookback + 1, len(df)):
        candle = _get_candle_data(df, i)
        prev_candle = _get_candle_data(df, i - 1)

        if candle['candle_range'] == 0:
            continue

        # 최근 스윙 고/저
        recent_high = df['high'].iloc[i-lookback:i].max()
        recent_low = df['low'].iloc[i-lookback:i].min()

        timestamp = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i]

        # === Bullish Pin Bar (해머) ===
        # 조건: 긴 아래꼬리, 몸통이 상단 30%에 위치, 이전 저점 돌파
        body_top = max(candle['open'], candle['close'])
        body_bottom = min(candle['open'], candle['close'])

        is_bullish_pinbar = (
            candle['lower_wick'] > candle['body_size'] * tail_ratio and
            body_bottom > candle['low'] + candle['candle_range'] * (1 - body_position) and
            candle['low'] < recent_low
        )

        # 추세 필터: 하락 추세에서 발생
        if use_trend_filter and 'ma20' in df.columns:
            is_bullish_pinbar = is_bullish_pinbar and df['close'].iloc[i] < df['ma20'].iloc[i]

        if is_bullish_pinbar:
            entry = candle['close']
            sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
                PatternDirection.BULLISH, entry, candle['high'], candle['low']
            )

            # 강도 계산
            wick_ratio = candle['lower_wick'] / candle['body_size'] if candle['body_size'] > 0 else 0
            strength = PatternStrength.STRONG if wick_ratio > 3 else PatternStrength.MODERATE if wick_ratio > 2 else PatternStrength.WEAK

            signals.append(PatternSignal(
                pattern_type="pinbar_bullish",
                direction=PatternDirection.BULLISH,
                strength=strength,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=min(100, 50 + wick_ratio * 10),
                rationale=f"하락추세 중 긴 아래꼬리 핀바 (꼬리/몸통={wick_ratio:.1f}x), 최근 저점 돌파 후 반등",
                metadata={"wick_ratio": wick_ratio, "recent_low": recent_low}
            ))

        # === Bearish Pin Bar (슈팅스타) ===
        is_bearish_pinbar = (
            candle['upper_wick'] > candle['body_size'] * tail_ratio and
            body_top < candle['high'] - candle['candle_range'] * (1 - body_position) and
            candle['high'] > recent_high
        )

        if use_trend_filter and 'ma20' in df.columns:
            is_bearish_pinbar = is_bearish_pinbar and df['close'].iloc[i] > df['ma20'].iloc[i]

        if is_bearish_pinbar:
            entry = candle['close']
            sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
                PatternDirection.BEARISH, entry, candle['high'], candle['low']
            )

            wick_ratio = candle['upper_wick'] / candle['body_size'] if candle['body_size'] > 0 else 0
            strength = PatternStrength.STRONG if wick_ratio > 3 else PatternStrength.MODERATE if wick_ratio > 2 else PatternStrength.WEAK

            signals.append(PatternSignal(
                pattern_type="pinbar_bearish",
                direction=PatternDirection.BEARISH,
                strength=strength,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=min(100, 50 + wick_ratio * 10),
                rationale=f"상승추세 중 긴 위꼬리 핀바 (꼬리/몸통={wick_ratio:.1f}x), 최근 고점 돌파 후 거부",
                metadata={"wick_ratio": wick_ratio, "recent_high": recent_high}
            ))

    return signals


def detect_engulfing(
    df: pd.DataFrame,
    min_body_ratio: float = 1.2,
    lookback: int = 5,
    use_trend_filter: bool = True,
) -> List[PatternSignal]:
    """
    잉걸핑(장악형) 패턴 감지

    Args:
        df: OHLCV DataFrame
        min_body_ratio: 현재 캔들 몸통이 이전 대비 최소 비율
        lookback: 스윙 비교 기간
        use_trend_filter: 추세 필터 사용
    """
    signals = []

    if len(df) < lookback + 2:
        return signals

    # 평균 몸통 크기 계산
    body_sizes = abs(df['close'] - df['open'])
    avg_body = body_sizes.rolling(14).mean()

    for i in range(lookback + 1, len(df)):
        candle = _get_candle_data(df, i)
        prev = _get_candle_data(df, i - 1)

        timestamp = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i]

        # 기본 조건
        current_body = candle['body_size']
        prev_body = prev['body_size']

        if prev_body == 0 or pd.isna(avg_body.iloc[i]):
            continue

        is_large_body = current_body > avg_body.iloc[i]
        is_prev_small = prev_body < avg_body.iloc[i]

        # 최근 고/저점
        recent_high = df['high'].iloc[i-lookback:i].max()
        recent_low = df['low'].iloc[i-lookback:i].min()

        # === Bullish Engulfing ===
        bullish_engulf = (
            candle['is_bullish'] and prev['is_bearish'] and
            is_large_body and is_prev_small and
            candle['close'] >= prev['open'] and
            candle['open'] <= prev['close'] and
            min(candle['low'], prev['low']) <= recent_low * 1.01  # 저점 근처
        )

        if bullish_engulf:
            entry = candle['close']
            sl_low = min(candle['low'], prev['low'])
            sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
                PatternDirection.BULLISH, entry, candle['high'], sl_low
            )

            body_ratio = current_body / prev_body if prev_body > 0 else 0
            strength = PatternStrength.STRONG if body_ratio > 2 else PatternStrength.MODERATE if body_ratio > 1.5 else PatternStrength.WEAK

            signals.append(PatternSignal(
                pattern_type="engulfing_bullish",
                direction=PatternDirection.BULLISH,
                strength=strength,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=min(100, 50 + body_ratio * 15),
                rationale=f"하락 캔들을 완전히 감싸는 상승 장악형 (몸통비={body_ratio:.1f}x)",
                metadata={"body_ratio": body_ratio}
            ))

        # === Bearish Engulfing ===
        bearish_engulf = (
            candle['is_bearish'] and prev['is_bullish'] and
            is_large_body and is_prev_small and
            candle['close'] <= prev['open'] and
            candle['open'] >= prev['close'] and
            max(candle['high'], prev['high']) >= recent_high * 0.99  # 고점 근처
        )

        if bearish_engulf:
            entry = candle['close']
            sl_high = max(candle['high'], prev['high'])
            sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
                PatternDirection.BEARISH, entry, sl_high, candle['low']
            )

            body_ratio = current_body / prev_body if prev_body > 0 else 0
            strength = PatternStrength.STRONG if body_ratio > 2 else PatternStrength.MODERATE if body_ratio > 1.5 else PatternStrength.WEAK

            signals.append(PatternSignal(
                pattern_type="engulfing_bearish",
                direction=PatternDirection.BEARISH,
                strength=strength,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=min(100, 50 + body_ratio * 15),
                rationale=f"상승 캔들을 완전히 감싸는 하락 장악형 (몸통비={body_ratio:.1f}x)",
                metadata={"body_ratio": body_ratio}
            ))

    return signals


def detect_star(
    df: pd.DataFrame,
    middle_body_ratio: float = 0.3,
    third_body_ratio: float = 0.5,
    use_gap: bool = False,
) -> List[PatternSignal]:
    """
    스타 패턴 감지 (Morning Star / Evening Star)

    Args:
        df: OHLCV DataFrame
        middle_body_ratio: 중간 캔들 몸통 크기 비율 (첫째/셋째 대비)
        third_body_ratio: 셋째 캔들 최소 몸통 비율 (첫째 대비)
        use_gap: 갭 조건 사용 (주식 시장용)
    """
    signals = []

    if len(df) < 4:
        return signals

    for i in range(3, len(df)):
        c0 = _get_candle_data(df, i)      # 현재 (셋째)
        c1 = _get_candle_data(df, i - 1)  # 중간 (둘째)
        c2 = _get_candle_data(df, i - 2)  # 첫째

        timestamp = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i]

        # 중간 캔들이 작아야 함
        small_middle = (
            c1['body_size'] < c2['body_size'] * middle_body_ratio and
            c1['body_size'] < c0['body_size'] * middle_body_ratio
        )

        # 셋째 캔들이 적당히 커야 함
        adequate_third = c0['body_size'] > c2['body_size'] * third_body_ratio

        if not (small_middle and adequate_third):
            continue

        # === Morning Star ===
        morning_star = (
            c2['is_bearish'] and c0['is_bullish'] and
            c0['close'] > max(c2['close'], c2['open']) and
            c0['close'] > c1['close']
        )

        if morning_star:
            entry = c0['close']
            sl_low = min(c0['low'], c1['low'], c2['low'])
            sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
                PatternDirection.BULLISH, entry, c0['high'], sl_low
            )

            signals.append(PatternSignal(
                pattern_type="morning_star",
                direction=PatternDirection.BULLISH,
                strength=PatternStrength.STRONG,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=75,
                rationale="하락 후 작은 몸통, 강한 상승 반전 = 모닝스타 (3캔들 반전 패턴)",
                metadata={"pattern_bars": 3}
            ))

        # === Evening Star ===
        evening_star = (
            c2['is_bullish'] and c0['is_bearish'] and
            c0['close'] < min(c2['close'], c2['open']) and
            c0['close'] < c1['close']
        )

        if evening_star:
            entry = c0['close']
            sl_high = max(c0['high'], c1['high'], c2['high'])
            sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
                PatternDirection.BEARISH, entry, sl_high, c0['low']
            )

            signals.append(PatternSignal(
                pattern_type="evening_star",
                direction=PatternDirection.BEARISH,
                strength=PatternStrength.STRONG,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=75,
                rationale="상승 후 작은 몸통, 강한 하락 반전 = 이브닝스타 (3캔들 반전 패턴)",
                metadata={"pattern_bars": 3}
            ))

    return signals


def detect_three_soldiers(
    df: pd.DataFrame,
    body_threshold: float = 0.6,
    shadow_percent: float = 0.15,
    min_long_candles: int = 2,
) -> List[PatternSignal]:
    """
    삼병 패턴 감지 (Three White Soldiers / Three Black Crows)

    Args:
        df: OHLCV DataFrame
        body_threshold: 평균 대비 몸통 크기 배수
        shadow_percent: 허용 최대 꼬리 비율
        min_long_candles: 최소 긴 몸통 개수 (3개 중)
    """
    signals = []

    if len(df) < 4:
        return signals

    # 평균 몸통 크기
    body_sizes = abs(df['close'] - df['open'])
    avg_body = body_sizes.rolling(14).mean()

    for i in range(3, len(df)):
        c0 = _get_candle_data(df, i)
        c1 = _get_candle_data(df, i - 1)
        c2 = _get_candle_data(df, i - 2)

        timestamp = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i]

        if pd.isna(avg_body.iloc[i]):
            continue

        avg = avg_body.iloc[i]

        # 긴 몸통 체크
        long_body_0 = c0['body_size'] > avg * body_threshold
        long_body_1 = c1['body_size'] > avg * body_threshold
        long_body_2 = c2['body_size'] > avg * body_threshold
        long_count = sum([long_body_0, long_body_1, long_body_2])

        # 꼬리 조건
        small_upper_0 = c0['upper_wick_ratio'] <= shadow_percent
        small_upper_1 = c1['upper_wick_ratio'] <= shadow_percent
        small_upper_2 = c2['upper_wick_ratio'] <= shadow_percent

        small_lower_0 = c0['lower_wick_ratio'] <= shadow_percent
        small_lower_1 = c1['lower_wick_ratio'] <= shadow_percent
        small_lower_2 = c2['lower_wick_ratio'] <= shadow_percent

        # === Three White Soldiers (적삼병) ===
        all_bullish = c0['is_bullish'] and c1['is_bullish'] and c2['is_bullish']
        rising_closes = c0['close'] > c1['close'] > c2['close']
        proper_opens_bull = (
            c0['open'] <= c1['close'] and c0['open'] >= c1['low'] and
            c1['open'] <= c2['close'] and c1['open'] >= c2['low']
        )
        small_uppers = small_upper_0 and small_upper_1 and small_upper_2

        if all_bullish and rising_closes and proper_opens_bull and long_count >= min_long_candles and small_uppers:
            entry = c0['close']
            sl_low = min(c0['low'], c1['low'], c2['low'])
            sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
                PatternDirection.BULLISH, entry, c0['high'], sl_low
            )

            signals.append(PatternSignal(
                pattern_type="three_white_soldiers",
                direction=PatternDirection.BULLISH,
                strength=PatternStrength.STRONG,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=80,
                rationale=f"3개 연속 상승 캔들 (긴몸통 {long_count}개, 작은꼬리) = 적삼병 강세 신호",
                metadata={"long_body_count": long_count}
            ))

        # === Three Black Crows (흑삼병) ===
        all_bearish = c0['is_bearish'] and c1['is_bearish'] and c2['is_bearish']
        falling_closes = c0['close'] < c1['close'] < c2['close']
        proper_opens_bear = (
            c0['open'] >= c1['close'] and c0['open'] <= c1['high'] and
            c1['open'] >= c2['close'] and c1['open'] <= c2['high']
        )
        small_lowers = small_lower_0 and small_lower_1 and small_lower_2

        if all_bearish and falling_closes and proper_opens_bear and long_count >= min_long_candles and small_lowers:
            entry = c0['close']
            sl_high = max(c0['high'], c1['high'], c2['high'])
            sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
                PatternDirection.BEARISH, entry, sl_high, c0['low']
            )

            signals.append(PatternSignal(
                pattern_type="three_black_crows",
                direction=PatternDirection.BEARISH,
                strength=PatternStrength.STRONG,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=80,
                rationale=f"3개 연속 하락 캔들 (긴몸통 {long_count}개, 작은꼬리) = 흑삼병 약세 신호",
                metadata={"long_body_count": long_count}
            ))

    return signals


class PriceActionDetector:
    """Price Action 패턴 통합 감지기"""

    def __init__(
        self,
        pinbar_tail_ratio: float = 2.0,
        engulfing_body_ratio: float = 1.2,
        star_middle_ratio: float = 0.3,
        soldiers_body_threshold: float = 0.6,
        use_trend_filter: bool = True,
    ):
        self.pinbar_tail_ratio = pinbar_tail_ratio
        self.engulfing_body_ratio = engulfing_body_ratio
        self.star_middle_ratio = star_middle_ratio
        self.soldiers_body_threshold = soldiers_body_threshold
        self.use_trend_filter = use_trend_filter

    def detect_all(
        self,
        df: pd.DataFrame,
        patterns: List[str] = None,
    ) -> List[PatternSignal]:
        """
        모든 Price Action 패턴 감지

        Args:
            df: OHLCV DataFrame
            patterns: 감지할 패턴 리스트 (None이면 전체)
                     ["pinbar", "engulfing", "star", "three_soldiers"]
        """
        all_patterns = patterns or ["pinbar", "engulfing", "star", "three_soldiers"]
        signals = []

        if "pinbar" in all_patterns:
            signals.extend(detect_pinbar(
                df,
                tail_ratio=self.pinbar_tail_ratio,
                use_trend_filter=self.use_trend_filter
            ))

        if "engulfing" in all_patterns:
            signals.extend(detect_engulfing(
                df,
                min_body_ratio=self.engulfing_body_ratio,
                use_trend_filter=self.use_trend_filter
            ))

        if "star" in all_patterns:
            signals.extend(detect_star(
                df,
                middle_body_ratio=self.star_middle_ratio
            ))

        if "three_soldiers" in all_patterns:
            signals.extend(detect_three_soldiers(
                df,
                body_threshold=self.soldiers_body_threshold
            ))

        # 바 인덱스로 정렬
        signals.sort(key=lambda x: x.bar_index)

        return signals

    def get_latest_signals(
        self,
        df: pd.DataFrame,
        lookback_bars: int = 5,
        patterns: List[str] = None,
    ) -> List[PatternSignal]:
        """최근 N개 바에서 발생한 시그널만 반환"""
        all_signals = self.detect_all(df, patterns)

        if not all_signals:
            return []

        latest_bar = len(df) - 1
        min_bar = latest_bar - lookback_bars

        return [s for s in all_signals if s.bar_index >= min_bar]
