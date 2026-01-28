"""
Supply/Demand Zone Indicator

수요/공급 존 식별:
- Base (횡보) + Impulse (강한 이탈) 패턴 감지
- Zone 강도 평가
- Zone 재테스트 감지
- Zone 무효화 처리
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

import pandas as pd
import numpy as np

from core.interfaces import Indicator, Signal, SignalType, Confidence, Symbol
from core.registry import register

logger = logging.getLogger(__name__)


class ZoneType(Enum):
    """존 타입"""
    DEMAND = "demand"  # 수요 존 (지지)
    SUPPLY = "supply"  # 공급 존 (저항)


class ZoneStrength(Enum):
    """존 강도"""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    EXTREME = 4


@dataclass
class Zone:
    """수요/공급 존"""
    type: ZoneType
    high: float
    low: float
    start_index: int
    start_time: datetime
    strength: ZoneStrength = ZoneStrength.MODERATE
    touches: int = 0
    is_fresh: bool = True  # 아직 테스트되지 않음
    is_valid: bool = True  # 무효화되지 않음
    impulse_strength: float = 0.0  # 이탈 강도 (%)
    time_in_zone: int = 0  # 존 형성 기간 (캔들 수)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def midpoint(self) -> float:
        """존 중심가"""
        return (self.high + self.low) / 2

    @property
    def height(self) -> float:
        """존 높이"""
        return self.high - self.low

    def contains_price(self, price: float) -> bool:
        """가격이 존 내부인지"""
        return self.low <= price <= self.high

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "high": self.high,
            "low": self.low,
            "strength": self.strength.value,
            "touches": self.touches,
            "is_fresh": self.is_fresh,
            "is_valid": self.is_valid,
            "impulse_strength": self.impulse_strength,
        }


@register("indicator", "supply_demand")
class SupplyDemandIndicator(Indicator):
    """
    수요/공급 존 지표

    알고리즘:
    1. Base 캔들 패턴 감지 (작은 body, 횡보)
    2. Impulse 캔들 감지 (큰 body, 강한 방향성)
    3. Base + Impulse 조합으로 존 형성
    4. 존 강도 평가
    5. 존 터치/무효화 추적

    사용법:
        indicator = SupplyDemandIndicator(lookback=50)
        df = indicator.calculate(df)
        zones = indicator.get_zones()
    """

    name = "supply_demand"
    description = "Supply and Demand Zones"

    default_params = {
        "lookback": 50,           # 존 탐색 기간
        "base_threshold": 0.5,    # Base 캔들 기준 (ATR 배수)
        "impulse_threshold": 1.5, # Impulse 캔들 기준 (ATR 배수)
        "min_base_candles": 2,    # 최소 Base 캔들 수
        "zone_extension": 0.1,    # 존 확장 (ATR 배수)
        "invalidation_pips": 0,   # 무효화 기준 (0=완전 돌파)
    }

    def __init__(self, **params):
        super().__init__(**params)
        self.zones: List[Zone] = []
        self.demand_zones: List[Zone] = []
        self.supply_zones: List[Zone] = []

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """수요/공급 존 계산"""
        df = df.copy()

        # ATR 계산 (변동성 기준)
        df = self._calculate_atr(df)

        # 캔들 특성 분류
        df = self._classify_candles(df)

        # 존 식별
        self._identify_zones(df)

        # 존 상태 업데이트
        self._update_zones(df)

        # 결과 컬럼 추가
        df = self._add_zone_columns(df)

        return df

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """ATR 계산"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        df["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["atr"] = df["tr"].ewm(span=period, adjust=False).mean()

        return df

    def _classify_candles(self, df: pd.DataFrame) -> pd.DataFrame:
        """캔들 분류 (Base/Impulse)"""
        base_thresh = self.params["base_threshold"]
        impulse_thresh = self.params["impulse_threshold"]

        # 캔들 바디 크기
        df["body"] = abs(df["close"] - df["open"])
        df["body_ratio"] = df["body"] / df["atr"]

        # 캔들 방향
        df["direction"] = np.where(df["close"] > df["open"], 1, -1)

        # Base 캔들 (작은 바디)
        df["is_base"] = df["body_ratio"] < base_thresh

        # Impulse 캔들 (큰 바디)
        df["is_impulse_up"] = (df["body_ratio"] > impulse_thresh) & (df["direction"] == 1)
        df["is_impulse_down"] = (df["body_ratio"] > impulse_thresh) & (df["direction"] == -1)

        return df

    def _identify_zones(self, df: pd.DataFrame):
        """존 식별"""
        self.zones = []
        self.demand_zones = []
        self.supply_zones = []

        lookback = self.params["lookback"]
        min_base = self.params["min_base_candles"]

        for i in range(lookback, len(df)):
            # Demand Zone: Base + Impulse Up
            demand_zone = self._find_demand_zone(df, i, min_base)
            if demand_zone:
                self.zones.append(demand_zone)
                self.demand_zones.append(demand_zone)

            # Supply Zone: Base + Impulse Down
            supply_zone = self._find_supply_zone(df, i, min_base)
            if supply_zone:
                self.zones.append(supply_zone)
                self.supply_zones.append(supply_zone)

    def _find_demand_zone(self, df: pd.DataFrame, idx: int, min_base: int) -> Optional[Zone]:
        """Demand Zone 찾기"""
        if not df.iloc[idx]["is_impulse_up"]:
            return None

        # 이전 Base 캔들들 찾기
        base_start = None
        base_count = 0

        for j in range(idx - 1, max(0, idx - 20), -1):
            if df.iloc[j]["is_base"]:
                base_count += 1
                base_start = j
            else:
                break

        if base_count < min_base:
            return None

        # Zone 범위 계산
        base_candles = df.iloc[base_start:idx]
        zone_low = base_candles["low"].min()
        zone_high = base_candles["high"].max()

        # 확장
        extension = df.iloc[idx]["atr"] * self.params["zone_extension"]
        zone_low -= extension

        # Impulse 강도 계산
        impulse_strength = (df.iloc[idx]["close"] - df.iloc[idx]["open"]) / df.iloc[idx]["atr"]

        # Zone 강도 평가
        strength = self._evaluate_zone_strength(
            impulse_strength=impulse_strength,
            base_count=base_count,
            zone_height=(zone_high - zone_low) / df.iloc[idx]["close"]
        )

        return Zone(
            type=ZoneType.DEMAND,
            high=zone_high,
            low=zone_low,
            start_index=base_start,
            start_time=df.iloc[base_start]["timestamp"] if "timestamp" in df.columns else datetime.now(),
            strength=strength,
            impulse_strength=impulse_strength,
            time_in_zone=base_count,
        )

    def _find_supply_zone(self, df: pd.DataFrame, idx: int, min_base: int) -> Optional[Zone]:
        """Supply Zone 찾기"""
        if not df.iloc[idx]["is_impulse_down"]:
            return None

        # 이전 Base 캔들들 찾기
        base_start = None
        base_count = 0

        for j in range(idx - 1, max(0, idx - 20), -1):
            if df.iloc[j]["is_base"]:
                base_count += 1
                base_start = j
            else:
                break

        if base_count < min_base:
            return None

        # Zone 범위 계산
        base_candles = df.iloc[base_start:idx]
        zone_low = base_candles["low"].min()
        zone_high = base_candles["high"].max()

        # 확장
        extension = df.iloc[idx]["atr"] * self.params["zone_extension"]
        zone_high += extension

        # Impulse 강도 계산
        impulse_strength = abs(df.iloc[idx]["close"] - df.iloc[idx]["open"]) / df.iloc[idx]["atr"]

        # Zone 강도 평가
        strength = self._evaluate_zone_strength(
            impulse_strength=impulse_strength,
            base_count=base_count,
            zone_height=(zone_high - zone_low) / df.iloc[idx]["close"]
        )

        return Zone(
            type=ZoneType.SUPPLY,
            high=zone_high,
            low=zone_low,
            start_index=base_start,
            start_time=df.iloc[base_start]["timestamp"] if "timestamp" in df.columns else datetime.now(),
            strength=strength,
            impulse_strength=impulse_strength,
            time_in_zone=base_count,
        )

    def _evaluate_zone_strength(
        self,
        impulse_strength: float,
        base_count: int,
        zone_height: float
    ) -> ZoneStrength:
        """존 강도 평가"""
        score = 0

        # Impulse 강도 (0-3점)
        if impulse_strength > 3.0:
            score += 3
        elif impulse_strength > 2.0:
            score += 2
        elif impulse_strength > 1.5:
            score += 1

        # Base 캔들 수 (0-2점)
        if base_count >= 5:
            score += 2
        elif base_count >= 3:
            score += 1

        # Zone 높이 (작을수록 좋음, 0-2점)
        if zone_height < 0.01:
            score += 2
        elif zone_height < 0.02:
            score += 1

        # 강도 매핑
        if score >= 6:
            return ZoneStrength.EXTREME
        elif score >= 4:
            return ZoneStrength.STRONG
        elif score >= 2:
            return ZoneStrength.MODERATE
        else:
            return ZoneStrength.WEAK

    def _update_zones(self, df: pd.DataFrame):
        """존 상태 업데이트 (터치, 무효화)"""
        current_price = df.iloc[-1]["close"]
        current_high = df.iloc[-1]["high"]
        current_low = df.iloc[-1]["low"]

        for zone in self.zones:
            if not zone.is_valid:
                continue

            # Demand Zone
            if zone.type == ZoneType.DEMAND:
                # 터치 (가격이 존에 진입)
                if zone.contains_price(current_low):
                    zone.touches += 1
                    zone.is_fresh = False

                # 무효화 (존 하단 돌파)
                if current_close := current_price < zone.low:
                    zone.is_valid = False

            # Supply Zone
            elif zone.type == ZoneType.SUPPLY:
                # 터치
                if zone.contains_price(current_high):
                    zone.touches += 1
                    zone.is_fresh = False

                # 무효화 (존 상단 돌파)
                if current_price > zone.high:
                    zone.is_valid = False

    def _add_zone_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """존 정보 컬럼 추가"""
        df["in_demand_zone"] = False
        df["in_supply_zone"] = False
        df["nearest_demand"] = np.nan
        df["nearest_supply"] = np.nan

        current_price = df.iloc[-1]["close"]

        # 유효한 존들
        valid_demands = [z for z in self.demand_zones if z.is_valid]
        valid_supplies = [z for z in self.supply_zones if z.is_valid]

        # 현재 존 내부 여부
        for zone in valid_demands:
            if zone.contains_price(current_price):
                df.iloc[-1, df.columns.get_loc("in_demand_zone")] = True
                break

        for zone in valid_supplies:
            if zone.contains_price(current_price):
                df.iloc[-1, df.columns.get_loc("in_supply_zone")] = True
                break

        # 가장 가까운 존
        if valid_demands:
            nearest = min(valid_demands, key=lambda z: abs(z.high - current_price))
            df.iloc[-1, df.columns.get_loc("nearest_demand")] = nearest.high

        if valid_supplies:
            nearest = min(valid_supplies, key=lambda z: abs(z.low - current_price))
            df.iloc[-1, df.columns.get_loc("nearest_supply")] = nearest.low

        return df

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """존 기반 신호 생성"""
        signals = []

        if "in_demand_zone" not in df.columns:
            df = self.calculate(df)

        last_row = df.iloc[-1]
        current_price = last_row["close"]

        # Demand Zone 진입 신호
        if last_row["in_demand_zone"]:
            zone = self._get_current_zone(current_price, ZoneType.DEMAND)
            if zone and zone.is_fresh:
                signals.append(Signal(
                    symbol=Symbol(ticker="", name="", market=None),
                    signal_type=SignalType.BUY,
                    confidence=self._strength_to_confidence(zone.strength),
                    source=self.name,
                    timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                    price=current_price,
                    reason=f"Price entering fresh Demand Zone ({zone.low:.2f} - {zone.high:.2f})",
                    metadata={
                        "zone_type": "demand",
                        "zone_strength": zone.strength.value,
                        "zone_touches": zone.touches,
                    }
                ))

        # Supply Zone 진입 신호
        if last_row["in_supply_zone"]:
            zone = self._get_current_zone(current_price, ZoneType.SUPPLY)
            if zone and zone.is_fresh:
                signals.append(Signal(
                    symbol=Symbol(ticker="", name="", market=None),
                    signal_type=SignalType.SELL,
                    confidence=self._strength_to_confidence(zone.strength),
                    source=self.name,
                    timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                    price=current_price,
                    reason=f"Price entering fresh Supply Zone ({zone.low:.2f} - {zone.high:.2f})",
                    metadata={
                        "zone_type": "supply",
                        "zone_strength": zone.strength.value,
                        "zone_touches": zone.touches,
                    }
                ))

        return signals

    def _get_current_zone(self, price: float, zone_type: ZoneType) -> Optional[Zone]:
        """현재 가격이 속한 존 반환"""
        zones = self.demand_zones if zone_type == ZoneType.DEMAND else self.supply_zones
        for zone in zones:
            if zone.is_valid and zone.contains_price(price):
                return zone
        return None

    def _strength_to_confidence(self, strength: ZoneStrength) -> Confidence:
        """존 강도를 신뢰도로 변환"""
        mapping = {
            ZoneStrength.WEAK: Confidence.LOW,
            ZoneStrength.MODERATE: Confidence.MEDIUM,
            ZoneStrength.STRONG: Confidence.HIGH,
            ZoneStrength.EXTREME: Confidence.VERY_HIGH,
        }
        return mapping.get(strength, Confidence.MEDIUM)

    def get_zones(self, valid_only: bool = True) -> Dict[str, List[Zone]]:
        """존 목록 반환"""
        if valid_only:
            return {
                "demand": [z for z in self.demand_zones if z.is_valid],
                "supply": [z for z in self.supply_zones if z.is_valid],
            }
        return {
            "demand": self.demand_zones,
            "supply": self.supply_zones,
        }

    def get_key_levels(self) -> Dict[str, List[float]]:
        """주요 레벨 반환"""
        valid_demands = [z for z in self.demand_zones if z.is_valid]
        valid_supplies = [z for z in self.supply_zones if z.is_valid]

        return {
            "demand_highs": [z.high for z in valid_demands],
            "demand_lows": [z.low for z in valid_demands],
            "supply_highs": [z.high for z in valid_supplies],
            "supply_lows": [z.low for z in valid_supplies],
        }
