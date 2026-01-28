"""
Double Bottom/Top Patterns - 쌍바닥/쌍봉 패턴 감지

패턴 유형:
- Simple Double Bottom/Top: 일반적인 쌍바닥/쌍봉
- M-Shaped: 중간 피크/트로프가 기준선(SMA) 위/아래
- Gull (갈매기): 두번째 저점/고점이 첫번째보다 낮/높음 (유동성 스윕)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from .price_action import PatternSignal, PatternDirection, PatternStrength


class DoublePatternType(Enum):
    """쌍바닥/쌍봉 유형"""
    SIMPLE = "simple"       # 일반 쌍바닥/쌍봉
    M_SHAPED = "m_shaped"   # M자형 (피크가 기준선 위/아래)
    GULL = "gull"           # 갈매기형 (유동성 스윕)


@dataclass
class PivotPoint:
    """피봇 포인트"""
    price: float
    bar_index: int
    is_high: bool  # True=고점, False=저점


def _find_pivot_points(
    df: pd.DataFrame,
    pivot_left: int = 5,
    pivot_right: int = 5,
) -> Tuple[List[PivotPoint], List[PivotPoint]]:
    """피봇 고점/저점 찾기"""
    pivot_highs = []
    pivot_lows = []

    for i in range(pivot_left, len(df) - pivot_right):
        # 피봇 고점 체크
        is_pivot_high = True
        for j in range(i - pivot_left, i + pivot_right + 1):
            if j != i and df['high'].iloc[j] >= df['high'].iloc[i]:
                is_pivot_high = False
                break

        if is_pivot_high:
            pivot_highs.append(PivotPoint(
                price=df['high'].iloc[i],
                bar_index=i,
                is_high=True
            ))

        # 피봇 저점 체크
        is_pivot_low = True
        for j in range(i - pivot_left, i + pivot_right + 1):
            if j != i and df['low'].iloc[j] <= df['low'].iloc[i]:
                is_pivot_low = False
                break

        if is_pivot_low:
            pivot_lows.append(PivotPoint(
                price=df['low'].iloc[i],
                bar_index=i,
                is_high=False
            ))

    return pivot_highs, pivot_lows


def _calculate_entry_sl_tp(
    direction: PatternDirection,
    entry: float,
    sl_price: float,
    rr_ratios: List[float] = [1.0, 2.0, 3.0],
) -> Tuple[float, float, float, float, float]:
    """진입/손절/익절 계산"""

    risk = abs(entry - sl_price)

    if direction == PatternDirection.BULLISH:
        tp1 = entry + risk * rr_ratios[0]
        tp2 = entry + risk * rr_ratios[1]
        tp3 = entry + risk * rr_ratios[2]
    else:
        tp1 = entry - risk * rr_ratios[0]
        tp2 = entry - risk * rr_ratios[1]
        tp3 = entry - risk * rr_ratios[2]

    return sl_price, tp1, tp2, tp3, risk


def detect_double_bottom(
    df: pd.DataFrame,
    sma_length: int = 20,
    pivot_left: int = 5,
    pivot_right: int = 5,
    tolerance: float = 0.03,  # 3% 허용 오차
    min_distance: int = 10,   # 두 저점 최소 거리 (바)
    max_distance: int = 100,  # 두 저점 최대 거리 (바)
) -> List[PatternSignal]:
    """
    쌍바닥 패턴 감지 (Simple, M-Shaped, Gull)

    Args:
        df: OHLCV DataFrame
        sma_length: SMA 기간
        pivot_left: 피봇 좌측 바 수
        pivot_right: 피봇 우측 바 수
        tolerance: 두 저점 허용 오차 (비율)
        min_distance: 두 저점 최소 거리
        max_distance: 두 저점 최대 거리
    """
    signals = []

    if len(df) < sma_length + pivot_left + pivot_right + min_distance:
        return signals

    # SMA 계산
    df = df.copy()
    df['sma'] = df['close'].rolling(sma_length).mean()

    # 피봇 포인트 찾기
    pivot_highs, pivot_lows = _find_pivot_points(df, pivot_left, pivot_right)

    if len(pivot_lows) < 2:
        return signals

    # 저점 쌍 분석
    for i in range(1, len(pivot_lows)):
        low1 = pivot_lows[i - 1]
        low2 = pivot_lows[i]

        # 거리 체크
        distance = low2.bar_index - low1.bar_index
        if distance < min_distance or distance > max_distance:
            continue

        # 두 저점 사이의 최고점(피크) 찾기
        peak_price = 0
        peak_sma = 0
        for ph in pivot_highs:
            if low1.bar_index < ph.bar_index < low2.bar_index:
                if ph.price > peak_price:
                    peak_price = ph.price
                    peak_sma = df['sma'].iloc[ph.bar_index] if not pd.isna(df['sma'].iloc[ph.bar_index]) else 0

        if peak_price == 0:
            continue

        # 현재 바 (low2 이후 확인 캔들)
        confirm_bar = low2.bar_index + pivot_right
        if confirm_bar >= len(df):
            continue

        current_close = df['close'].iloc[confirm_bar]
        current_sma = df['sma'].iloc[confirm_bar] if not pd.isna(df['sma'].iloc[confirm_bar]) else 0

        # SMA 돌파 확인 (크로스오버)
        sma_crossover = False
        for j in range(max(low2.bar_index, 1), min(confirm_bar + 1, len(df))):
            if df['close'].iloc[j] > df['sma'].iloc[j] and df['close'].iloc[j-1] <= df['sma'].iloc[j-1]:
                sma_crossover = True
                break

        if not sma_crossover:
            continue

        timestamp = df['timestamp'].iloc[confirm_bar] if 'timestamp' in df.columns else df.index[confirm_bar]

        # 패턴 유형 결정
        pattern_type = None
        pattern_name = ""
        confidence = 0
        rationale = ""

        # 1. Simple Double Bottom: low2 > low1, peak <= sma
        if low2.price > low1.price * (1 - tolerance) and peak_price <= peak_sma:
            pattern_type = DoublePatternType.SIMPLE
            pattern_name = "double_bottom_simple"
            confidence = 70
            rationale = f"일반 쌍바닥: 두번째 저점({low2.price:.2f})이 첫번째({low1.price:.2f}) 이상, 중간 피크가 SMA 아래"

        # 2. M-Shaped Double Bottom: low2 > low1, peak > sma
        elif low2.price > low1.price * (1 - tolerance) and peak_price > peak_sma:
            pattern_type = DoublePatternType.M_SHAPED
            pattern_name = "double_bottom_m"
            confidence = 65
            rationale = f"M자형 쌍바닥: 두번째 저점({low2.price:.2f})이 첫번째({low1.price:.2f}) 이상, 중간 피크가 SMA 위 (강한 반등 후 재하락)"

        # 3. Gull (갈매기): low2 < low1 (유동성 스윕)
        elif low2.price < low1.price:
            pattern_type = DoublePatternType.GULL
            pattern_name = "double_bottom_gull"
            confidence = 75  # 유동성 스윕은 더 신뢰도 높음
            rationale = f"갈매기 쌍바닥: 두번째 저점({low2.price:.2f})이 첫번째({low1.price:.2f}) 하회 후 반등 (유동성 스윕 후 반전)"

        if pattern_type is None:
            continue

        # Entry/SL/TP 계산
        entry = current_close
        sl_price = low2.price * 0.995  # 저점 아래 0.5%
        sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
            PatternDirection.BULLISH, entry, sl_price
        )

        signals.append(PatternSignal(
            pattern_type=pattern_name,
            direction=PatternDirection.BULLISH,
            strength=PatternStrength.STRONG if pattern_type == DoublePatternType.GULL else PatternStrength.MODERATE,
            bar_index=confirm_bar,
            timestamp=timestamp,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_amount=risk,
            confidence=confidence,
            rationale=rationale,
            metadata={
                "pattern_subtype": pattern_type.value,
                "low1_price": low1.price,
                "low1_bar": low1.bar_index,
                "low2_price": low2.price,
                "low2_bar": low2.bar_index,
                "peak_price": peak_price,
                "distance_bars": distance,
            }
        ))

    return signals


def detect_double_top(
    df: pd.DataFrame,
    sma_length: int = 20,
    pivot_left: int = 5,
    pivot_right: int = 5,
    tolerance: float = 0.03,
    min_distance: int = 10,
    max_distance: int = 100,
) -> List[PatternSignal]:
    """
    쌍봉 패턴 감지 (Simple, M-Shaped, Gull)

    Args:
        df: OHLCV DataFrame
        sma_length: SMA 기간
        pivot_left: 피봇 좌측 바 수
        pivot_right: 피봇 우측 바 수
        tolerance: 두 고점 허용 오차 (비율)
        min_distance: 두 고점 최소 거리
        max_distance: 두 고점 최대 거리
    """
    signals = []

    if len(df) < sma_length + pivot_left + pivot_right + min_distance:
        return signals

    # SMA 계산
    df = df.copy()
    df['sma'] = df['close'].rolling(sma_length).mean()

    # 피봇 포인트 찾기
    pivot_highs, pivot_lows = _find_pivot_points(df, pivot_left, pivot_right)

    if len(pivot_highs) < 2:
        return signals

    # 고점 쌍 분석
    for i in range(1, len(pivot_highs)):
        high1 = pivot_highs[i - 1]
        high2 = pivot_highs[i]

        # 거리 체크
        distance = high2.bar_index - high1.bar_index
        if distance < min_distance or distance > max_distance:
            continue

        # 두 고점 사이의 최저점(트로프) 찾기
        trough_price = float('inf')
        trough_sma = 0
        for pl in pivot_lows:
            if high1.bar_index < pl.bar_index < high2.bar_index:
                if pl.price < trough_price:
                    trough_price = pl.price
                    trough_sma = df['sma'].iloc[pl.bar_index] if not pd.isna(df['sma'].iloc[pl.bar_index]) else 0

        if trough_price == float('inf'):
            continue

        # 현재 바 (high2 이후 확인 캔들)
        confirm_bar = high2.bar_index + pivot_right
        if confirm_bar >= len(df):
            continue

        current_close = df['close'].iloc[confirm_bar]
        current_sma = df['sma'].iloc[confirm_bar] if not pd.isna(df['sma'].iloc[confirm_bar]) else 0

        # SMA 하향 돌파 확인 (크로스언더)
        sma_crossunder = False
        for j in range(max(high2.bar_index, 1), min(confirm_bar + 1, len(df))):
            if df['close'].iloc[j] < df['sma'].iloc[j] and df['close'].iloc[j-1] >= df['sma'].iloc[j-1]:
                sma_crossunder = True
                break

        if not sma_crossunder:
            continue

        timestamp = df['timestamp'].iloc[confirm_bar] if 'timestamp' in df.columns else df.index[confirm_bar]

        # 패턴 유형 결정
        pattern_type = None
        pattern_name = ""
        confidence = 0
        rationale = ""

        # 1. Simple Double Top: high2 < high1, trough >= sma
        if high2.price < high1.price * (1 + tolerance) and trough_price >= trough_sma:
            pattern_type = DoublePatternType.SIMPLE
            pattern_name = "double_top_simple"
            confidence = 70
            rationale = f"일반 쌍봉: 두번째 고점({high2.price:.2f})이 첫번째({high1.price:.2f}) 이하, 중간 트로프가 SMA 위"

        # 2. M-Shaped Double Top: high2 < high1, trough < sma
        elif high2.price < high1.price * (1 + tolerance) and trough_price < trough_sma:
            pattern_type = DoublePatternType.M_SHAPED
            pattern_name = "double_top_m"
            confidence = 65
            rationale = f"M자형 쌍봉: 두번째 고점({high2.price:.2f})이 첫번째({high1.price:.2f}) 이하, 중간 트로프가 SMA 아래"

        # 3. Gull (갈매기): high2 > high1 (유동성 스윕)
        elif high2.price > high1.price:
            pattern_type = DoublePatternType.GULL
            pattern_name = "double_top_gull"
            confidence = 75
            rationale = f"갈매기 쌍봉: 두번째 고점({high2.price:.2f})이 첫번째({high1.price:.2f}) 상회 후 하락 (유동성 스윕 후 반전)"

        if pattern_type is None:
            continue

        # Entry/SL/TP 계산
        entry = current_close
        sl_price = high2.price * 1.005  # 고점 위 0.5%
        sl, tp1, tp2, tp3, risk = _calculate_entry_sl_tp(
            PatternDirection.BEARISH, entry, sl_price
        )

        signals.append(PatternSignal(
            pattern_type=pattern_name,
            direction=PatternDirection.BEARISH,
            strength=PatternStrength.STRONG if pattern_type == DoublePatternType.GULL else PatternStrength.MODERATE,
            bar_index=confirm_bar,
            timestamp=timestamp,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_amount=risk,
            confidence=confidence,
            rationale=rationale,
            metadata={
                "pattern_subtype": pattern_type.value,
                "high1_price": high1.price,
                "high1_bar": high1.bar_index,
                "high2_price": high2.price,
                "high2_bar": high2.bar_index,
                "trough_price": trough_price,
                "distance_bars": distance,
            }
        ))

    return signals


class DoublePatternDetector:
    """쌍바닥/쌍봉 패턴 통합 감지기"""

    def __init__(
        self,
        sma_length: int = 20,
        pivot_left: int = 5,
        pivot_right: int = 5,
        tolerance: float = 0.03,
        min_distance: int = 10,
        max_distance: int = 100,
    ):
        self.sma_length = sma_length
        self.pivot_left = pivot_left
        self.pivot_right = pivot_right
        self.tolerance = tolerance
        self.min_distance = min_distance
        self.max_distance = max_distance

    def detect_all(
        self,
        df: pd.DataFrame,
        patterns: List[str] = None,
    ) -> List[PatternSignal]:
        """
        모든 쌍바닥/쌍봉 패턴 감지

        Args:
            df: OHLCV DataFrame
            patterns: 감지할 패턴 ["double_bottom", "double_top"]
        """
        all_patterns = patterns or ["double_bottom", "double_top"]
        signals = []

        if "double_bottom" in all_patterns:
            signals.extend(detect_double_bottom(
                df,
                sma_length=self.sma_length,
                pivot_left=self.pivot_left,
                pivot_right=self.pivot_right,
                tolerance=self.tolerance,
                min_distance=self.min_distance,
                max_distance=self.max_distance,
            ))

        if "double_top" in all_patterns:
            signals.extend(detect_double_top(
                df,
                sma_length=self.sma_length,
                pivot_left=self.pivot_left,
                pivot_right=self.pivot_right,
                tolerance=self.tolerance,
                min_distance=self.min_distance,
                max_distance=self.max_distance,
            ))

        signals.sort(key=lambda x: x.bar_index)
        return signals

    def get_latest_signals(
        self,
        df: pd.DataFrame,
        lookback_bars: int = 10,
        patterns: List[str] = None,
    ) -> List[PatternSignal]:
        """최근 N개 바에서 발생한 시그널만 반환"""
        all_signals = self.detect_all(df, patterns)

        if not all_signals:
            return []

        latest_bar = len(df) - 1
        min_bar = latest_bar - lookback_bars

        return [s for s in all_signals if s.bar_index >= min_bar]
