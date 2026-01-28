"""
Liquidity Patterns - 유동성 패턴 감지

패턴:
- Liquidity Sweep: 유동성 스윕 (스탑헌팅)
- Liquidity Grab: 유동성 그랩
- Stop Hunt: 스탑 헌트
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from .price_action import PatternSignal, PatternDirection, PatternStrength


@dataclass
class LiquidityLevel:
    """유동성 레벨"""
    price: float
    bar_index: int
    is_high: bool  # True=고점 유동성, False=저점 유동성
    strength: int = 1  # 터치 횟수


def _find_liquidity_levels(
    df: pd.DataFrame,
    lookback: int = 20,
    tolerance: float = 0.002,  # 0.2% 허용 오차
) -> Tuple[List[LiquidityLevel], List[LiquidityLevel]]:
    """
    유동성 레벨 찾기 (스윙 고/저점)

    여러 번 테스트된 레벨은 더 강한 유동성을 가짐
    """
    high_levels = []
    low_levels = []

    # 스윙 고점/저점 찾기
    for i in range(lookback, len(df)):
        # 스윙 고점
        is_swing_high = df['high'].iloc[i] == df['high'].iloc[i-lookback:i+1].max()
        if is_swing_high:
            price = df['high'].iloc[i]

            # 기존 레벨과 병합
            merged = False
            for level in high_levels:
                if abs(level.price - price) / price < tolerance:
                    level.strength += 1
                    merged = True
                    break

            if not merged:
                high_levels.append(LiquidityLevel(
                    price=price,
                    bar_index=i,
                    is_high=True,
                    strength=1
                ))

        # 스윙 저점
        is_swing_low = df['low'].iloc[i] == df['low'].iloc[i-lookback:i+1].min()
        if is_swing_low:
            price = df['low'].iloc[i]

            merged = False
            for level in low_levels:
                if abs(level.price - price) / price < tolerance:
                    level.strength += 1
                    merged = True
                    break

            if not merged:
                low_levels.append(LiquidityLevel(
                    price=price,
                    bar_index=i,
                    is_high=False,
                    strength=1
                ))

    return high_levels, low_levels


def detect_liquidity_sweep(
    df: pd.DataFrame,
    lookback: int = 20,
    threshold_pct: float = 0.3,  # 스윕 후 반전 최소 %
    volume_multiplier: float = 1.5,  # 평균 대비 거래량 배수
    use_volume_filter: bool = True,
    use_choch_filter: bool = True,
) -> List[PatternSignal]:
    """
    유동성 스윕 감지

    유동성 스윕: 이전 스윙 고/저점을 돌파 후 즉시 반전
    - 스탑 헌팅 후 진짜 방향으로 움직임
    - 기관이 유동성을 수집하는 신호

    Args:
        df: OHLCV DataFrame
        lookback: 스윙 감지 기간
        threshold_pct: 반전 최소 퍼센트
        volume_multiplier: 거래량 필터 배수
        use_volume_filter: 거래량 필터 사용
        use_choch_filter: CHOCH 필터 사용
    """
    signals = []

    if len(df) < lookback + 5:
        return signals

    # 거래량 MA 계산
    df = df.copy()
    if 'volume' in df.columns and use_volume_filter:
        df['volume_sma'] = df['volume'].rolling(20).mean()
    else:
        df['volume_sma'] = 1  # 필터 비활성화

    for i in range(lookback + 1, len(df)):
        # 최근 스윙 포인트
        recent_high = df['high'].iloc[i-lookback:i].max()
        recent_low = df['low'].iloc[i-lookback:i].min()

        current_high = df['high'].iloc[i]
        current_low = df['low'].iloc[i]
        current_close = df['close'].iloc[i]
        current_open = df['open'].iloc[i]

        timestamp = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i]

        # 거래량 체크
        volume_ok = True
        if use_volume_filter and 'volume' in df.columns:
            vol = df['volume'].iloc[i]
            vol_sma = df['volume_sma'].iloc[i]
            volume_ok = vol > vol_sma * volume_multiplier if not pd.isna(vol_sma) else True

        # === Bullish Liquidity Sweep (저점 스윕 후 상승) ===
        # 조건: 저점 돌파(스윕) + 종가가 저점 위로 복귀 + 양봉
        swept_low = current_low < recent_low
        recovered_above = current_close > recent_low * (1 + threshold_pct / 100)
        is_bullish_candle = current_close > current_open

        # CHOCH 필터: Higher Low + Higher High
        choch_ok = True
        if use_choch_filter and i > 1:
            prev_low = df['low'].iloc[i-1]
            prev_high = df['high'].iloc[i-1]
            # 단순화된 CHOCH: 이전보다 높은 저점과 종가
            choch_ok = current_low > prev_low or current_close > prev_high

        if swept_low and recovered_above and is_bullish_candle and volume_ok and choch_ok:
            entry = current_close
            sl = current_low * 0.995
            risk = entry - sl
            tp1 = entry + risk
            tp2 = entry + risk * 2
            tp3 = entry + risk * 3

            # 스윕 깊이로 신뢰도 계산
            sweep_depth = (recent_low - current_low) / recent_low * 100
            confidence = min(85, 60 + sweep_depth * 5)

            signals.append(PatternSignal(
                pattern_type="liquidity_sweep_bullish",
                direction=PatternDirection.BULLISH,
                strength=PatternStrength.STRONG if sweep_depth > 0.5 else PatternStrength.MODERATE,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=confidence,
                rationale=f"저점 유동성 스윕: ${recent_low:.2f} 하회 후 반등 (스윕 깊이 {sweep_depth:.2f}%) - 스탑헌팅 후 상승 반전",
                metadata={
                    "sweep_level": recent_low,
                    "sweep_low": current_low,
                    "sweep_depth_pct": sweep_depth,
                    "volume_ratio": df['volume'].iloc[i] / df['volume_sma'].iloc[i] if 'volume' in df.columns else 1,
                }
            ))

        # === Bearish Liquidity Sweep (고점 스윕 후 하락) ===
        swept_high = current_high > recent_high
        recovered_below = current_close < recent_high * (1 - threshold_pct / 100)
        is_bearish_candle = current_close < current_open

        choch_ok = True
        if use_choch_filter and i > 1:
            prev_low = df['low'].iloc[i-1]
            prev_high = df['high'].iloc[i-1]
            choch_ok = current_high < prev_high or current_close < prev_low

        if swept_high and recovered_below and is_bearish_candle and volume_ok and choch_ok:
            entry = current_close
            sl = current_high * 1.005
            risk = sl - entry
            tp1 = entry - risk
            tp2 = entry - risk * 2
            tp3 = entry - risk * 3

            sweep_depth = (current_high - recent_high) / recent_high * 100
            confidence = min(85, 60 + sweep_depth * 5)

            signals.append(PatternSignal(
                pattern_type="liquidity_sweep_bearish",
                direction=PatternDirection.BEARISH,
                strength=PatternStrength.STRONG if sweep_depth > 0.5 else PatternStrength.MODERATE,
                bar_index=i,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=confidence,
                rationale=f"고점 유동성 스윕: ${recent_high:.2f} 상회 후 하락 (스윕 깊이 {sweep_depth:.2f}%) - 스탑헌팅 후 하락 반전",
                metadata={
                    "sweep_level": recent_high,
                    "sweep_high": current_high,
                    "sweep_depth_pct": sweep_depth,
                    "volume_ratio": df['volume'].iloc[i] / df['volume_sma'].iloc[i] if 'volume' in df.columns else 1,
                }
            ))

    return signals


class LiquidityDetector:
    """유동성 패턴 통합 감지기"""

    def __init__(
        self,
        lookback: int = 20,
        threshold_pct: float = 0.3,
        volume_multiplier: float = 1.5,
        use_volume_filter: bool = True,
        use_choch_filter: bool = True,
    ):
        self.lookback = lookback
        self.threshold_pct = threshold_pct
        self.volume_multiplier = volume_multiplier
        self.use_volume_filter = use_volume_filter
        self.use_choch_filter = use_choch_filter

    def detect_all(self, df: pd.DataFrame) -> List[PatternSignal]:
        """모든 유동성 패턴 감지"""
        return detect_liquidity_sweep(
            df,
            lookback=self.lookback,
            threshold_pct=self.threshold_pct,
            volume_multiplier=self.volume_multiplier,
            use_volume_filter=self.use_volume_filter,
            use_choch_filter=self.use_choch_filter,
        )

    def get_latest_signals(
        self,
        df: pd.DataFrame,
        lookback_bars: int = 5,
    ) -> List[PatternSignal]:
        """최근 시그널만 반환"""
        all_signals = self.detect_all(df)

        if not all_signals:
            return []

        latest_bar = len(df) - 1
        min_bar = latest_bar - lookback_bars

        return [s for s in all_signals if s.bar_index >= min_bar]

    def get_liquidity_levels(
        self,
        df: pd.DataFrame,
        min_strength: int = 2,
    ) -> Dict[str, List[LiquidityLevel]]:
        """
        현재 유효한 유동성 레벨 반환

        Args:
            df: OHLCV DataFrame
            min_strength: 최소 강도 (터치 횟수)
        """
        high_levels, low_levels = _find_liquidity_levels(df, self.lookback)

        current_price = df['close'].iloc[-1]

        # 현재 가격 위의 고점 유동성 (저항)
        resistance_levels = [
            lv for lv in high_levels
            if lv.price > current_price and lv.strength >= min_strength
        ]

        # 현재 가격 아래의 저점 유동성 (지지)
        support_levels = [
            lv for lv in low_levels
            if lv.price < current_price and lv.strength >= min_strength
        ]

        return {
            "resistance": sorted(resistance_levels, key=lambda x: x.price),
            "support": sorted(support_levels, key=lambda x: -x.price),
        }
