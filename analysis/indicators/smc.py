"""
SMC (Smart Money Concepts) Indicator

ICT/SMC 트레이딩 개념 구현:
- Market Structure (HH, HL, LH, LL)
- BOS (Break of Structure)
- CHoCH (Change of Character)
- Order Blocks
- Fair Value Gaps (FVG/Imbalance)
- Liquidity Pools
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

import pandas as pd
import numpy as np

from core.interfaces import Indicator, Signal, SignalType, Confidence, Symbol
from core.registry import register

logger = logging.getLogger(__name__)


class StructureType(Enum):
    """마켓 구조 타입"""
    HH = "higher_high"
    HL = "higher_low"
    LH = "lower_high"
    LL = "lower_low"


class TrendBias(Enum):
    """트렌드 방향"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class SwingPoint:
    """스윙 포인트"""
    index: int
    timestamp: datetime
    price: float
    type: str  # "high" or "low"
    structure: Optional[StructureType] = None


@dataclass
class OrderBlock:
    """오더 블록"""
    index: int
    timestamp: datetime
    high: float
    low: float
    type: str  # "bullish" or "bearish"
    mitigated: bool = False
    strength: float = 1.0


@dataclass
class FairValueGap:
    """Fair Value Gap (불균형 영역)"""
    index: int
    timestamp: datetime
    high: float
    low: float
    type: str  # "bullish" or "bearish"
    filled: bool = False


@register("indicator", "smc")
class SMCIndicator(Indicator):
    """
    Smart Money Concepts 지표

    기능:
    - 스윙 High/Low 식별
    - 마켓 구조 분석 (HH, HL, LH, LL)
    - BOS/CHoCH 감지
    - 오더 블록 식별
    - FVG 감지
    - 유동성 풀 추정

    사용법:
        indicator = SMCIndicator(swing_length=10)
        df = indicator.calculate(df)
        signals = indicator.generate_signals(df)
    """

    name = "smc"
    description = "Smart Money Concepts"

    default_params = {
        "swing_length": 10,  # 스윙 포인트 감지 기간
        "structure_lookback": 50,  # 구조 분석 기간
        "ob_lookback": 20,  # 오더 블록 감지 기간
        "fvg_min_size": 0.001,  # FVG 최소 크기 (비율)
    }

    def __init__(self, **params):
        super().__init__(**params)
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.order_blocks: List[OrderBlock] = []
        self.fvgs: List[FairValueGap] = []

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """SMC 지표 계산"""
        df = df.copy()

        # 1. 스윙 포인트 식별
        df = self._identify_swing_points(df)

        # 2. 마켓 구조 분석
        df = self._analyze_structure(df)

        # 3. BOS/CHoCH 감지
        df = self._detect_bos_choch(df)

        # 4. 오더 블록 식별
        df = self._identify_order_blocks(df)

        # 5. FVG 감지
        df = self._detect_fvg(df)

        # 6. 현재 트렌드 바이어스
        df = self._calculate_bias(df)

        return df

    def _identify_swing_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """스윙 High/Low 식별"""
        length = self.params["swing_length"]

        df["swing_high"] = False
        df["swing_low"] = False
        df["swing_high_price"] = np.nan
        df["swing_low_price"] = np.nan

        highs = df["high"].values
        lows = df["low"].values

        for i in range(length, len(df) - length):
            # Swing High: 양쪽으로 length 캔들보다 높음
            is_swing_high = True
            for j in range(1, length + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_swing_high = False
                    break

            if is_swing_high:
                df.iloc[i, df.columns.get_loc("swing_high")] = True
                df.iloc[i, df.columns.get_loc("swing_high_price")] = highs[i]
                self.swing_highs.append(SwingPoint(
                    index=i,
                    timestamp=df.iloc[i]["timestamp"] if "timestamp" in df.columns else datetime.now(),
                    price=highs[i],
                    type="high"
                ))

            # Swing Low: 양쪽으로 length 캔들보다 낮음
            is_swing_low = True
            for j in range(1, length + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_swing_low = False
                    break

            if is_swing_low:
                df.iloc[i, df.columns.get_loc("swing_low")] = True
                df.iloc[i, df.columns.get_loc("swing_low_price")] = lows[i]
                self.swing_lows.append(SwingPoint(
                    index=i,
                    timestamp=df.iloc[i]["timestamp"] if "timestamp" in df.columns else datetime.now(),
                    price=lows[i],
                    type="low"
                ))

        return df

    def _analyze_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """마켓 구조 분석 (HH, HL, LH, LL)"""
        df["structure"] = ""

        # 스윙 하이 구조
        for i in range(1, len(self.swing_highs)):
            current = self.swing_highs[i]
            prev = self.swing_highs[i - 1]

            if current.price > prev.price:
                current.structure = StructureType.HH
                df.iloc[current.index, df.columns.get_loc("structure")] = "HH"
            else:
                current.structure = StructureType.LH
                df.iloc[current.index, df.columns.get_loc("structure")] = "LH"

        # 스윙 로우 구조
        for i in range(1, len(self.swing_lows)):
            current = self.swing_lows[i]
            prev = self.swing_lows[i - 1]

            if current.price > prev.price:
                current.structure = StructureType.HL
                df.iloc[current.index, df.columns.get_loc("structure")] = "HL"
            else:
                current.structure = StructureType.LL
                df.iloc[current.index, df.columns.get_loc("structure")] = "LL"

        return df

    def _detect_bos_choch(self, df: pd.DataFrame) -> pd.DataFrame:
        """BOS (Break of Structure) / CHoCH (Change of Character) 감지"""
        df["bos"] = ""
        df["choch"] = ""

        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2:
            return df

        closes = df["close"].values

        # 최근 스윙 포인트들
        recent_high = self.swing_highs[-1] if self.swing_highs else None
        recent_low = self.swing_lows[-1] if self.swing_lows else None
        prev_high = self.swing_highs[-2] if len(self.swing_highs) > 1 else None
        prev_low = self.swing_lows[-2] if len(self.swing_lows) > 1 else None

        for i in range(len(df)):
            close = closes[i]

            # Bullish BOS: 이전 스윙 하이 돌파
            if prev_high and close > prev_high.price:
                # 상승 추세 중 BOS
                if recent_low and recent_low.structure == StructureType.HL:
                    df.iloc[i, df.columns.get_loc("bos")] = "bullish"

            # Bearish BOS: 이전 스윙 로우 돌파
            if prev_low and close < prev_low.price:
                # 하락 추세 중 BOS
                if recent_high and recent_high.structure == StructureType.LH:
                    df.iloc[i, df.columns.get_loc("bos")] = "bearish"

            # Bullish CHoCH: 하락 추세에서 LH 돌파
            if recent_high and recent_high.structure == StructureType.LH:
                if close > recent_high.price:
                    df.iloc[i, df.columns.get_loc("choch")] = "bullish"

            # Bearish CHoCH: 상승 추세에서 HL 돌파
            if recent_low and recent_low.structure == StructureType.HL:
                if close < recent_low.price:
                    df.iloc[i, df.columns.get_loc("choch")] = "bearish"

        return df

    def _identify_order_blocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """오더 블록 식별"""
        df["order_block_bull"] = False
        df["order_block_bear"] = False
        df["ob_high"] = np.nan
        df["ob_low"] = np.nan

        lookback = self.params["ob_lookback"]

        for i in range(lookback, len(df)):
            # Bullish Order Block: 강한 상승 전 마지막 하락 캔들
            if self._is_bullish_impulse(df, i):
                ob_idx = self._find_last_bearish_candle(df, i, lookback)
                if ob_idx is not None:
                    df.iloc[ob_idx, df.columns.get_loc("order_block_bull")] = True
                    df.iloc[ob_idx, df.columns.get_loc("ob_high")] = df.iloc[ob_idx]["high"]
                    df.iloc[ob_idx, df.columns.get_loc("ob_low")] = df.iloc[ob_idx]["low"]

                    self.order_blocks.append(OrderBlock(
                        index=ob_idx,
                        timestamp=df.iloc[ob_idx]["timestamp"] if "timestamp" in df.columns else datetime.now(),
                        high=df.iloc[ob_idx]["high"],
                        low=df.iloc[ob_idx]["low"],
                        type="bullish"
                    ))

            # Bearish Order Block: 강한 하락 전 마지막 상승 캔들
            if self._is_bearish_impulse(df, i):
                ob_idx = self._find_last_bullish_candle(df, i, lookback)
                if ob_idx is not None:
                    df.iloc[ob_idx, df.columns.get_loc("order_block_bear")] = True
                    df.iloc[ob_idx, df.columns.get_loc("ob_high")] = df.iloc[ob_idx]["high"]
                    df.iloc[ob_idx, df.columns.get_loc("ob_low")] = df.iloc[ob_idx]["low"]

                    self.order_blocks.append(OrderBlock(
                        index=ob_idx,
                        timestamp=df.iloc[ob_idx]["timestamp"] if "timestamp" in df.columns else datetime.now(),
                        high=df.iloc[ob_idx]["high"],
                        low=df.iloc[ob_idx]["low"],
                        type="bearish"
                    ))

        return df

    def _is_bullish_impulse(self, df: pd.DataFrame, idx: int) -> bool:
        """강한 상승 움직임 감지"""
        if idx < 3:
            return False
        # 3캔들 연속 상승 + 큰 움직임
        closes = df["close"].iloc[idx-3:idx+1].values
        return all(closes[i] < closes[i+1] for i in range(len(closes)-1))

    def _is_bearish_impulse(self, df: pd.DataFrame, idx: int) -> bool:
        """강한 하락 움직임 감지"""
        if idx < 3:
            return False
        closes = df["close"].iloc[idx-3:idx+1].values
        return all(closes[i] > closes[i+1] for i in range(len(closes)-1))

    def _find_last_bearish_candle(self, df: pd.DataFrame, end_idx: int, lookback: int) -> Optional[int]:
        """마지막 하락 캔들 찾기"""
        for i in range(end_idx - 1, max(0, end_idx - lookback), -1):
            if df.iloc[i]["close"] < df.iloc[i]["open"]:
                return i
        return None

    def _find_last_bullish_candle(self, df: pd.DataFrame, end_idx: int, lookback: int) -> Optional[int]:
        """마지막 상승 캔들 찾기"""
        for i in range(end_idx - 1, max(0, end_idx - lookback), -1):
            if df.iloc[i]["close"] > df.iloc[i]["open"]:
                return i
        return None

    def _detect_fvg(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fair Value Gap (FVG) 감지"""
        df["fvg_bull"] = False
        df["fvg_bear"] = False
        df["fvg_high"] = np.nan
        df["fvg_low"] = np.nan

        min_size = self.params["fvg_min_size"]

        for i in range(2, len(df)):
            # Bullish FVG: 캔들1의 high < 캔들3의 low
            candle1_high = df.iloc[i - 2]["high"]
            candle3_low = df.iloc[i]["low"]

            if candle3_low > candle1_high:
                gap_size = (candle3_low - candle1_high) / df.iloc[i]["close"]
                if gap_size >= min_size:
                    df.iloc[i - 1, df.columns.get_loc("fvg_bull")] = True
                    df.iloc[i - 1, df.columns.get_loc("fvg_high")] = candle3_low
                    df.iloc[i - 1, df.columns.get_loc("fvg_low")] = candle1_high

                    self.fvgs.append(FairValueGap(
                        index=i - 1,
                        timestamp=df.iloc[i - 1]["timestamp"] if "timestamp" in df.columns else datetime.now(),
                        high=candle3_low,
                        low=candle1_high,
                        type="bullish"
                    ))

            # Bearish FVG: 캔들1의 low > 캔들3의 high
            candle1_low = df.iloc[i - 2]["low"]
            candle3_high = df.iloc[i]["high"]

            if candle1_low > candle3_high:
                gap_size = (candle1_low - candle3_high) / df.iloc[i]["close"]
                if gap_size >= min_size:
                    df.iloc[i - 1, df.columns.get_loc("fvg_bear")] = True
                    df.iloc[i - 1, df.columns.get_loc("fvg_high")] = candle1_low
                    df.iloc[i - 1, df.columns.get_loc("fvg_low")] = candle3_high

                    self.fvgs.append(FairValueGap(
                        index=i - 1,
                        timestamp=df.iloc[i - 1]["timestamp"] if "timestamp" in df.columns else datetime.now(),
                        high=candle1_low,
                        low=candle3_high,
                        type="bearish"
                    ))

        return df

    def _calculate_bias(self, df: pd.DataFrame) -> pd.DataFrame:
        """현재 트렌드 바이어스 계산"""
        df["smc_bias"] = "neutral"

        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2:
            return df

        # 최근 구조 분석
        recent_structures = []
        for sh in self.swing_highs[-3:]:
            if sh.structure:
                recent_structures.append(sh.structure)
        for sl in self.swing_lows[-3:]:
            if sl.structure:
                recent_structures.append(sl.structure)

        bullish_count = sum(1 for s in recent_structures if s in [StructureType.HH, StructureType.HL])
        bearish_count = sum(1 for s in recent_structures if s in [StructureType.LH, StructureType.LL])

        if bullish_count > bearish_count:
            df["smc_bias"] = "bullish"
        elif bearish_count > bullish_count:
            df["smc_bias"] = "bearish"

        return df

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """SMC 기반 신호 생성"""
        signals = []

        if "choch" not in df.columns:
            df = self.calculate(df)

        last_row = df.iloc[-1]
        current_price = last_row["close"]

        # CHoCH 신호 (추세 전환)
        if last_row["choch"] == "bullish":
            signals.append(Signal(
                symbol=Symbol(ticker="", name="", market=None),
                signal_type=SignalType.BUY,
                confidence=Confidence.HIGH,
                source=self.name,
                timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                price=current_price,
                reason="Bullish CHoCH: Trend reversal to upside",
                metadata={"smc_event": "choch_bullish"}
            ))
        elif last_row["choch"] == "bearish":
            signals.append(Signal(
                symbol=Symbol(ticker="", name="", market=None),
                signal_type=SignalType.SELL,
                confidence=Confidence.HIGH,
                source=self.name,
                timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                price=current_price,
                reason="Bearish CHoCH: Trend reversal to downside",
                metadata={"smc_event": "choch_bearish"}
            ))

        # 오더 블록 진입 신호
        for ob in self.order_blocks[-5:]:  # 최근 5개만 확인
            if not ob.mitigated:
                if ob.type == "bullish" and ob.low <= current_price <= ob.high:
                    signals.append(Signal(
                        symbol=Symbol(ticker="", name="", market=None),
                        signal_type=SignalType.WATCH,
                        confidence=Confidence.MEDIUM,
                        source=self.name,
                        timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                        price=current_price,
                        reason=f"Price entering Bullish Order Block ({ob.low:.2f} - {ob.high:.2f})",
                        metadata={"smc_event": "ob_entry", "ob_type": "bullish"}
                    ))
                elif ob.type == "bearish" and ob.low <= current_price <= ob.high:
                    signals.append(Signal(
                        symbol=Symbol(ticker="", name="", market=None),
                        signal_type=SignalType.WATCH,
                        confidence=Confidence.MEDIUM,
                        source=self.name,
                        timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                        price=current_price,
                        reason=f"Price entering Bearish Order Block ({ob.low:.2f} - {ob.high:.2f})",
                        metadata={"smc_event": "ob_entry", "ob_type": "bearish"}
                    ))

        return signals

    def get_key_levels(self) -> Dict[str, List[float]]:
        """주요 레벨 반환"""
        return {
            "swing_highs": [sh.price for sh in self.swing_highs[-10:]],
            "swing_lows": [sl.price for sl in self.swing_lows[-10:]],
            "order_block_highs": [ob.high for ob in self.order_blocks if not ob.mitigated],
            "order_block_lows": [ob.low for ob in self.order_blocks if not ob.mitigated],
            "fvg_highs": [fvg.high for fvg in self.fvgs if not fvg.filled],
            "fvg_lows": [fvg.low for fvg in self.fvgs if not fvg.filled],
        }
