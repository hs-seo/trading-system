"""
SMC (Smart Money Concepts) Patterns - 스마트머니 개념 패턴

패턴:
- Order Block (OB): 기관 주문 영역
- BOS (Break of Structure): 구조 돌파
- CHOCH (Change of Character): 추세 전환
- Supply/Demand Zone: 수급 영역
- Golden Zone: 피보나치 황금 영역 (38.2%-61.8%)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from .price_action import PatternSignal, PatternDirection, PatternStrength


class StructureType(Enum):
    """구조 유형"""
    BOS = "bos"      # Break of Structure
    CHOCH = "choch"  # Change of Character


class ZoneType(Enum):
    """존 유형"""
    DEMAND = "demand"  # 수요 영역 (매수)
    SUPPLY = "supply"  # 공급 영역 (매도)


@dataclass
class SwingPoint:
    """스윙 포인트"""
    price: float
    bar_index: int
    is_high: bool
    timestamp: Any = None


@dataclass
class OrderBlock:
    """오더 블록"""
    zone_type: ZoneType
    top: float
    bottom: float
    start_bar: int
    end_bar: int
    timestamp: Any

    # 품질 점수
    score: int = 0
    grade: str = "C"  # S, A, B, C

    # 상태
    is_golden: bool = False     # 골든존 내 위치
    is_choch: bool = False      # CHOCH에서 생성
    is_mitigated: bool = False  # 소진됨

    # 메타데이터
    impulse_size: float = 0     # 임펄스 크기
    base_candles: int = 0       # 베이스 캔들 수

    def to_dict(self) -> Dict:
        return {
            "type": self.zone_type.value,
            "top": self.top,
            "bottom": self.bottom,
            "start_bar": self.start_bar,
            "score": self.score,
            "grade": self.grade,
            "is_golden": self.is_golden,
            "is_choch": self.is_choch,
        }


@dataclass
class FibonacciLevel:
    """피보나치 레벨"""
    fib_382: float
    fib_500: float
    fib_618: float
    start_price: float
    end_price: float
    is_bullish: bool


def _find_swing_points(
    df: pd.DataFrame,
    swing_length: int = 5,
) -> Tuple[List[SwingPoint], List[SwingPoint]]:
    """스윙 고점/저점 찾기"""
    swing_highs = []
    swing_lows = []

    for i in range(swing_length, len(df) - swing_length):
        # 스윙 고점
        is_swing_high = df['high'].iloc[i] == df['high'].iloc[i-swing_length:i+swing_length+1].max()
        if is_swing_high:
            ts = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i]
            swing_highs.append(SwingPoint(
                price=df['high'].iloc[i],
                bar_index=i,
                is_high=True,
                timestamp=ts
            ))

        # 스윙 저점
        is_swing_low = df['low'].iloc[i] == df['low'].iloc[i-swing_length:i+swing_length+1].min()
        if is_swing_low:
            ts = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i]
            swing_lows.append(SwingPoint(
                price=df['low'].iloc[i],
                bar_index=i,
                is_high=False,
                timestamp=ts
            ))

    return swing_highs, swing_lows


def _calculate_fib_levels(
    start_price: float,
    end_price: float,
    is_bullish: bool,
) -> FibonacciLevel:
    """피보나치 레벨 계산"""
    range_size = abs(end_price - start_price)

    if is_bullish:
        # 상승 임펄스: 조정 레벨은 위에서 아래로
        fib_382 = end_price - range_size * 0.382
        fib_500 = end_price - range_size * 0.500
        fib_618 = end_price - range_size * 0.618
    else:
        # 하락 임펄스: 조정 레벨은 아래에서 위로
        fib_382 = end_price + range_size * 0.382
        fib_500 = end_price + range_size * 0.500
        fib_618 = end_price + range_size * 0.618

    return FibonacciLevel(
        fib_382=fib_382,
        fib_500=fib_500,
        fib_618=fib_618,
        start_price=start_price,
        end_price=end_price,
        is_bullish=is_bullish
    )


def _is_in_golden_zone(price_top: float, price_bottom: float, fib: FibonacciLevel) -> bool:
    """골든존(38.2%-61.8%) 내에 있는지 확인"""
    zone_mid = (price_top + price_bottom) / 2

    if fib.is_bullish:
        # 상승: 골든존은 fib_618과 fib_382 사이
        golden_top = fib.fib_382
        golden_bottom = fib.fib_618
    else:
        # 하락: 골든존은 fib_382와 fib_618 사이
        golden_top = fib.fib_618
        golden_bottom = fib.fib_382

    return golden_bottom <= zone_mid <= golden_top


def _calculate_ob_score(
    is_choch: bool,
    base_candles: int,
    impulse_size: float,
    atr: float,
    is_golden: bool,
    wick_ratio: float = 0.5,
) -> Tuple[int, str]:
    """오더 블록 점수 계산 (Pine Script 로직 기반)"""
    score = 0

    # 1. 구조 점수 (CHOCH vs BOS)
    score += 4 if is_choch else 2

    # 2. 베이스 캔들 점수
    if 1 <= base_candles <= 3:
        score += 2
    elif base_candles <= 5:
        score += 1

    # 3. 임펄스 크기 점수
    if impulse_size >= atr * 2.5:
        score += 2
    elif impulse_size >= atr * 1.5:
        score += 1

    # 4. 위크 점수
    if wick_ratio <= 0.4:
        score += 2
    elif wick_ratio <= 0.6:
        score += 1

    # 5. 골든존 점수
    if is_golden:
        score += 3

    # 등급 결정
    if score >= 12:
        grade = "S"
    elif score >= 9:
        grade = "A"
    elif score >= 6:
        grade = "B"
    else:
        grade = "C"

    return score, grade


def detect_bos_choch(
    df: pd.DataFrame,
    swing_length: int = 5,
) -> List[Dict]:
    """
    BOS(구조 돌파) 및 CHOCH(추세 전환) 감지

    Returns:
        List of structure breaks with type, direction, bar_index
    """
    structures = []

    swing_highs, swing_lows = _find_swing_points(df, swing_length)

    if not swing_highs or not swing_lows:
        return structures

    # 추세 추적
    trend = 0  # 1: 상승, -1: 하락, 0: 없음
    last_swing_high = None
    last_swing_low = None

    for i in range(len(df)):
        # 스윙 고점 업데이트
        for sh in swing_highs:
            if sh.bar_index == i - swing_length:
                last_swing_high = sh

        # 스윙 저점 업데이트
        for sl in swing_lows:
            if sl.bar_index == i - swing_length:
                last_swing_low = sl

        if last_swing_high is None or last_swing_low is None:
            continue

        close = df['close'].iloc[i]
        timestamp = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i]

        # BOS Up (상승 돌파)
        if close > last_swing_high.price:
            is_choch = trend == -1
            structures.append({
                "type": StructureType.CHOCH if is_choch else StructureType.BOS,
                "direction": PatternDirection.BULLISH,
                "bar_index": i,
                "price": last_swing_high.price,
                "timestamp": timestamp,
                "is_choch": is_choch,
            })
            trend = 1

        # BOS Down (하락 돌파)
        if close < last_swing_low.price:
            is_choch = trend == 1
            structures.append({
                "type": StructureType.CHOCH if is_choch else StructureType.BOS,
                "direction": PatternDirection.BEARISH,
                "bar_index": i,
                "price": last_swing_low.price,
                "timestamp": timestamp,
                "is_choch": is_choch,
            })
            trend = -1

    return structures


def detect_order_blocks(
    df: pd.DataFrame,
    swing_length: int = 5,
    ob_lookback: int = 10,
    max_base_bars: int = 5,
    atr_period: int = 14,
    atr_multiplier: float = 0.8,
    min_score: int = 4,
) -> List[OrderBlock]:
    """
    오더 블록 감지 (SMC Order Block)

    Args:
        df: OHLCV DataFrame
        swing_length: 스윙 감지 기간
        ob_lookback: OB 탐색 범위
        max_base_bars: 최대 베이스 캔들 수
        atr_period: ATR 기간
        atr_multiplier: 임펄스 크기 배수
        min_score: 최소 점수
    """
    order_blocks = []

    if len(df) < swing_length * 2 + ob_lookback:
        return order_blocks

    # ATR 계산
    df = df.copy()
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift(1))
    low_close = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(atr_period).mean()

    # BOS/CHOCH 감지
    structures = detect_bos_choch(df, swing_length)

    # 피보나치 히스토리 (최근 임펄스)
    fib_history = []

    for struct in structures:
        bar_idx = struct['bar_index']
        is_bullish = struct['direction'] == PatternDirection.BULLISH
        is_choch = struct['is_choch']

        atr = df['atr'].iloc[bar_idx] if not pd.isna(df['atr'].iloc[bar_idx]) else 1
        timestamp = struct['timestamp']

        # 피보나치 레벨 저장
        swing_highs, swing_lows = _find_swing_points(df.iloc[:bar_idx+1], swing_length)

        if is_bullish and swing_lows:
            last_low = swing_lows[-1] if swing_lows else None
            last_high_price = struct['price']
            if last_low:
                fib = _calculate_fib_levels(last_low.price, last_high_price, True)
                fib_history.append(fib)
        elif not is_bullish and swing_highs:
            last_high = swing_highs[-1] if swing_highs else None
            last_low_price = struct['price']
            if last_high:
                fib = _calculate_fib_levels(last_high.price, last_low_price, False)
                fib_history.append(fib)

        # 최근 피보나치만 유지
        if len(fib_history) > 3:
            fib_history = fib_history[-3:]

        # 오더 블록 찾기
        if is_bullish:
            # Bullish OB: BOS/CHOCH 전 마지막 하락 캔들
            for j in range(1, min(ob_lookback, bar_idx)):
                idx = bar_idx - j
                if df['close'].iloc[idx] < df['open'].iloc[idx]:  # 하락 캔들
                    ob_top = df['high'].iloc[idx]
                    ob_bottom = df['low'].iloc[idx]

                    # 베이스 캔들 확장
                    base_count = 0
                    for k in range(1, max_base_bars + 1):
                        if idx + k < bar_idx:
                            body = abs(df['close'].iloc[idx+k] - df['open'].iloc[idx+k])
                            if body < atr * 0.5:
                                base_count += 1
                                ob_top = max(ob_top, df['high'].iloc[idx+k])
                                ob_bottom = min(ob_bottom, df['low'].iloc[idx+k])
                            else:
                                break

                    # 임펄스 크기 계산
                    impulse_size = df['close'].iloc[bar_idx] - ob_bottom

                    # 골든존 체크
                    is_golden = False
                    if fib_history:
                        for fib in fib_history:
                            if _is_in_golden_zone(ob_top, ob_bottom, fib):
                                is_golden = True
                                break

                    # 점수 계산
                    score, grade = _calculate_ob_score(
                        is_choch, base_count, impulse_size, atr, is_golden
                    )

                    if score >= min_score:
                        order_blocks.append(OrderBlock(
                            zone_type=ZoneType.DEMAND,
                            top=ob_top,
                            bottom=ob_bottom,
                            start_bar=idx,
                            end_bar=bar_idx,
                            timestamp=timestamp,
                            score=score,
                            grade=grade,
                            is_golden=is_golden,
                            is_choch=is_choch,
                            impulse_size=impulse_size,
                            base_candles=base_count,
                        ))
                    break

        else:
            # Bearish OB: BOS/CHOCH 전 마지막 상승 캔들
            for j in range(1, min(ob_lookback, bar_idx)):
                idx = bar_idx - j
                if df['close'].iloc[idx] > df['open'].iloc[idx]:  # 상승 캔들
                    ob_top = df['high'].iloc[idx]
                    ob_bottom = df['low'].iloc[idx]

                    # 베이스 캔들 확장
                    base_count = 0
                    for k in range(1, max_base_bars + 1):
                        if idx + k < bar_idx:
                            body = abs(df['close'].iloc[idx+k] - df['open'].iloc[idx+k])
                            if body < atr * 0.5:
                                base_count += 1
                                ob_top = max(ob_top, df['high'].iloc[idx+k])
                                ob_bottom = min(ob_bottom, df['low'].iloc[idx+k])
                            else:
                                break

                    # 임펄스 크기 계산
                    impulse_size = ob_top - df['close'].iloc[bar_idx]

                    # 골든존 체크
                    is_golden = False
                    if fib_history:
                        for fib in fib_history:
                            if _is_in_golden_zone(ob_top, ob_bottom, fib):
                                is_golden = True
                                break

                    # 점수 계산
                    score, grade = _calculate_ob_score(
                        is_choch, base_count, impulse_size, atr, is_golden
                    )

                    if score >= min_score:
                        order_blocks.append(OrderBlock(
                            zone_type=ZoneType.SUPPLY,
                            top=ob_top,
                            bottom=ob_bottom,
                            start_bar=idx,
                            end_bar=bar_idx,
                            timestamp=timestamp,
                            score=score,
                            grade=grade,
                            is_golden=is_golden,
                            is_choch=is_choch,
                            impulse_size=impulse_size,
                            base_candles=base_count,
                        ))
                    break

    return order_blocks


def detect_supply_demand(
    df: pd.DataFrame,
    swing_length: int = 5,
    min_score: int = 4,
    check_mitigation: bool = True,
) -> Tuple[List[OrderBlock], List[PatternSignal]]:
    """
    수급 영역 감지 및 진입 시그널 생성

    Returns:
        (active_zones, signals)
    """
    order_blocks = detect_order_blocks(df, swing_length=swing_length, min_score=min_score)
    signals = []

    if not order_blocks:
        return [], []

    # 최신 가격으로 존 상태 업데이트 및 시그널 생성
    for ob in order_blocks:
        # Mitigation 체크 (가격이 존을 완전히 통과했는지)
        if check_mitigation and ob.end_bar < len(df) - 1:
            for i in range(ob.end_bar + 1, len(df)):
                if ob.zone_type == ZoneType.DEMAND:
                    if df['close'].iloc[i] < ob.bottom:
                        ob.is_mitigated = True
                        break
                else:
                    if df['close'].iloc[i] > ob.top:
                        ob.is_mitigated = True
                        break

        if ob.is_mitigated:
            continue

        # 현재 가격이 존에 진입했는지 확인
        current_bar = len(df) - 1
        current_low = df['low'].iloc[current_bar]
        current_high = df['high'].iloc[current_bar]
        current_close = df['close'].iloc[current_bar]
        timestamp = df['timestamp'].iloc[current_bar] if 'timestamp' in df.columns else df.index[current_bar]

        # Demand Zone 진입 (롱 시그널)
        if ob.zone_type == ZoneType.DEMAND and current_low <= ob.top and current_low >= ob.bottom:
            entry = current_close
            sl = ob.bottom * 0.995
            risk = entry - sl
            tp1 = entry + risk
            tp2 = entry + risk * 2
            tp3 = entry + risk * 3

            golden_mark = " (Golden)" if ob.is_golden else ""
            choch_mark = " CHOCH" if ob.is_choch else " BOS"

            signals.append(PatternSignal(
                pattern_type=f"smc_demand_{ob.grade.lower()}",
                direction=PatternDirection.BULLISH,
                strength=PatternStrength.STRONG if ob.grade in ["S", "A"] else PatternStrength.MODERATE,
                bar_index=current_bar,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=50 + ob.score * 3,
                rationale=f"SMC Demand Zone [{ob.grade}]{golden_mark}{choch_mark} 진입 - 기관 매수 영역 터치",
                metadata={
                    "zone_top": ob.top,
                    "zone_bottom": ob.bottom,
                    "score": ob.score,
                    "grade": ob.grade,
                    "is_golden": ob.is_golden,
                    "is_choch": ob.is_choch,
                }
            ))

        # Supply Zone 진입 (숏 시그널)
        if ob.zone_type == ZoneType.SUPPLY and current_high >= ob.bottom and current_high <= ob.top:
            entry = current_close
            sl = ob.top * 1.005
            risk = sl - entry
            tp1 = entry - risk
            tp2 = entry - risk * 2
            tp3 = entry - risk * 3

            golden_mark = " (Golden)" if ob.is_golden else ""
            choch_mark = " CHOCH" if ob.is_choch else " BOS"

            signals.append(PatternSignal(
                pattern_type=f"smc_supply_{ob.grade.lower()}",
                direction=PatternDirection.BEARISH,
                strength=PatternStrength.STRONG if ob.grade in ["S", "A"] else PatternStrength.MODERATE,
                bar_index=current_bar,
                timestamp=timestamp,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_amount=risk,
                confidence=50 + ob.score * 3,
                rationale=f"SMC Supply Zone [{ob.grade}]{golden_mark}{choch_mark} 진입 - 기관 매도 영역 터치",
                metadata={
                    "zone_top": ob.top,
                    "zone_bottom": ob.bottom,
                    "score": ob.score,
                    "grade": ob.grade,
                    "is_golden": ob.is_golden,
                    "is_choch": ob.is_choch,
                }
            ))

    # 활성 존만 반환
    active_zones = [ob for ob in order_blocks if not ob.is_mitigated]

    return active_zones, signals


class SMCDetector:
    """SMC 패턴 통합 감지기"""

    def __init__(
        self,
        swing_length: int = 5,
        ob_lookback: int = 10,
        min_score: int = 4,
        min_grade: str = "B",  # S, A, B, C
    ):
        self.swing_length = swing_length
        self.ob_lookback = ob_lookback
        self.min_score = min_score
        self.min_grade = min_grade

    def detect_all(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        모든 SMC 패턴 감지

        Returns:
            {
                "structures": List[Dict],  # BOS/CHOCH
                "order_blocks": List[OrderBlock],
                "signals": List[PatternSignal],
            }
        """
        structures = detect_bos_choch(df, self.swing_length)
        active_zones, signals = detect_supply_demand(
            df,
            swing_length=self.swing_length,
            min_score=self.min_score,
        )

        # 등급 필터링
        grade_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        min_grade_idx = grade_order.get(self.min_grade, 2)

        filtered_zones = [
            ob for ob in active_zones
            if grade_order.get(ob.grade, 3) <= min_grade_idx
        ]

        filtered_signals = [
            s for s in signals
            if grade_order.get(s.metadata.get("grade", "C"), 3) <= min_grade_idx
        ]

        return {
            "structures": structures,
            "order_blocks": filtered_zones,
            "signals": filtered_signals,
        }

    def get_latest_signals(
        self,
        df: pd.DataFrame,
        lookback_bars: int = 5,
    ) -> List[PatternSignal]:
        """최근 시그널만 반환"""
        result = self.detect_all(df)
        signals = result.get("signals", [])

        if not signals:
            return []

        latest_bar = len(df) - 1
        min_bar = latest_bar - lookback_bars

        return [s for s in signals if s.bar_index >= min_bar]
