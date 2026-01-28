"""
Classic Indicators - 전통적인 기술적 지표

MA, RSI, MACD, Bollinger Bands, ATR 등
"""
from typing import Any, Dict, List
import logging

import pandas as pd
import numpy as np

from core.interfaces import Indicator, Signal, SignalType, Confidence, Symbol
from core.registry import register
from datetime import datetime

logger = logging.getLogger(__name__)


@register("indicator", "ma")
class MAIndicator(Indicator):
    """
    이동평균 지표

    단순(SMA), 지수(EMA), 가중(WMA) 이동평균 지원
    골든크로스/데드크로스 신호 생성
    """

    name = "ma"
    description = "Moving Average Indicator"

    default_params = {
        "fast_period": 20,
        "slow_period": 50,
        "ma_type": "ema",  # sma, ema, wma
        "price_column": "close",
    }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균 계산"""
        price = df[self.params["price_column"]]
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        ma_type = self.params["ma_type"]

        if ma_type == "sma":
            df[f"ma_{fast}"] = price.rolling(window=fast).mean()
            df[f"ma_{slow}"] = price.rolling(window=slow).mean()
        elif ma_type == "ema":
            df[f"ma_{fast}"] = price.ewm(span=fast, adjust=False).mean()
            df[f"ma_{slow}"] = price.ewm(span=slow, adjust=False).mean()
        elif ma_type == "wma":
            weights_fast = np.arange(1, fast + 1)
            weights_slow = np.arange(1, slow + 1)
            df[f"ma_{fast}"] = price.rolling(fast).apply(
                lambda x: np.dot(x, weights_fast) / weights_fast.sum(), raw=True
            )
            df[f"ma_{slow}"] = price.rolling(slow).apply(
                lambda x: np.dot(x, weights_slow) / weights_slow.sum(), raw=True
            )

        # 크로스 신호
        df["ma_cross"] = np.where(
            df[f"ma_{fast}"] > df[f"ma_{slow}"], 1,
            np.where(df[f"ma_{fast}"] < df[f"ma_{slow}"], -1, 0)
        )
        df["ma_cross_signal"] = df["ma_cross"].diff()

        return df

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """골든/데드 크로스 신호"""
        signals = []

        if "ma_cross_signal" not in df.columns:
            df = self.calculate(df)

        last_row = df.iloc[-1]

        if last_row["ma_cross_signal"] == 2:  # 골든 크로스
            signals.append(Signal(
                symbol=Symbol(ticker="", name="", market=None),
                signal_type=SignalType.BUY,
                confidence=Confidence.MEDIUM,
                source=self.name,
                timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                price=last_row["close"],
                reason="Golden Cross: Fast MA crossed above Slow MA",
            ))
        elif last_row["ma_cross_signal"] == -2:  # 데드 크로스
            signals.append(Signal(
                symbol=Symbol(ticker="", name="", market=None),
                signal_type=SignalType.SELL,
                confidence=Confidence.MEDIUM,
                source=self.name,
                timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                price=last_row["close"],
                reason="Dead Cross: Fast MA crossed below Slow MA",
            ))

        return signals


@register("indicator", "rsi")
class RSIIndicator(Indicator):
    """
    RSI (Relative Strength Index) 지표

    과매수/과매도 구간 감지
    다이버전스 감지 (선택적)
    """

    name = "rsi"
    description = "Relative Strength Index"

    default_params = {
        "period": 14,
        "overbought": 70,
        "oversold": 30,
        "detect_divergence": False,
    }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI 계산"""
        period = self.params["period"]
        delta = df["close"].diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # 과매수/과매도 영역
        df["rsi_overbought"] = df["rsi"] > self.params["overbought"]
        df["rsi_oversold"] = df["rsi"] < self.params["oversold"]

        return df

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """과매수/과매도 신호"""
        signals = []

        if "rsi" not in df.columns:
            df = self.calculate(df)

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else last_row

        # 과매도 탈출 (매수)
        if prev_row["rsi_oversold"] and not last_row["rsi_oversold"]:
            signals.append(Signal(
                symbol=Symbol(ticker="", name="", market=None),
                signal_type=SignalType.BUY,
                confidence=Confidence.MEDIUM,
                source=self.name,
                timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                price=last_row["close"],
                reason=f"RSI exiting oversold zone ({last_row['rsi']:.1f})",
            ))

        # 과매수 진입 (경고)
        if not prev_row["rsi_overbought"] and last_row["rsi_overbought"]:
            signals.append(Signal(
                symbol=Symbol(ticker="", name="", market=None),
                signal_type=SignalType.WATCH,
                confidence=Confidence.LOW,
                source=self.name,
                timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                price=last_row["close"],
                reason=f"RSI entering overbought zone ({last_row['rsi']:.1f})",
            ))

        return signals


@register("indicator", "macd")
class MACDIndicator(Indicator):
    """
    MACD (Moving Average Convergence Divergence) 지표

    트렌드 강도 및 방향 판단
    시그널 라인 크로스 감지
    """

    name = "macd"
    description = "Moving Average Convergence Divergence"

    default_params = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
    }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD 계산"""
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        signal = self.params["signal_period"]

        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        # 크로스 신호
        df["macd_cross"] = np.where(
            df["macd"] > df["macd_signal"], 1,
            np.where(df["macd"] < df["macd_signal"], -1, 0)
        )
        df["macd_cross_signal"] = df["macd_cross"].diff()

        return df

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """MACD 크로스 신호"""
        signals = []

        if "macd_cross_signal" not in df.columns:
            df = self.calculate(df)

        last_row = df.iloc[-1]

        if last_row["macd_cross_signal"] == 2:  # 상향 크로스
            signals.append(Signal(
                symbol=Symbol(ticker="", name="", market=None),
                signal_type=SignalType.BUY,
                confidence=Confidence.MEDIUM,
                source=self.name,
                timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                price=last_row["close"],
                reason="MACD crossed above signal line",
            ))
        elif last_row["macd_cross_signal"] == -2:  # 하향 크로스
            signals.append(Signal(
                symbol=Symbol(ticker="", name="", market=None),
                signal_type=SignalType.SELL,
                confidence=Confidence.MEDIUM,
                source=self.name,
                timestamp=last_row["timestamp"] if "timestamp" in last_row else datetime.now(),
                price=last_row["close"],
                reason="MACD crossed below signal line",
            ))

        return signals


@register("indicator", "bollinger")
class BollingerBands(Indicator):
    """
    볼린저 밴드 지표

    변동성 기반 상/하단 밴드
    밴드 터치 및 스퀴즈 감지
    """

    name = "bollinger"
    description = "Bollinger Bands"

    default_params = {
        "period": 20,
        "std_dev": 2.0,
    }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """볼린저 밴드 계산"""
        period = self.params["period"]
        std = self.params["std_dev"]

        df["bb_middle"] = df["close"].rolling(window=period).mean()
        rolling_std = df["close"].rolling(window=period).std()

        df["bb_upper"] = df["bb_middle"] + (rolling_std * std)
        df["bb_lower"] = df["bb_middle"] - (rolling_std * std)

        # 밴드폭 (변동성)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        # %B (현재 위치)
        df["bb_pct_b"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        return df


@register("indicator", "atr")
class ATRIndicator(Indicator):
    """
    ATR (Average True Range) 지표

    변동성 측정
    손절/익절 레벨 계산에 활용
    """

    name = "atr"
    description = "Average True Range"

    default_params = {
        "period": 14,
    }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """ATR 계산"""
        period = self.params["period"]

        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        df["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["atr"] = df["tr"].ewm(span=period, adjust=False).mean()

        # ATR 비율 (현재가 대비)
        df["atr_pct"] = df["atr"] / df["close"] * 100

        return df


# ============================================================================
# Utility Functions
# ============================================================================

def calculate_all_classic(df: pd.DataFrame, config: Dict[str, Any] = None) -> pd.DataFrame:
    """
    모든 클래식 지표 일괄 계산

    편의 함수: 기본 설정으로 모든 지표 계산
    """
    config = config or {}

    indicators = [
        MAIndicator(**config.get("ma", {})),
        RSIIndicator(**config.get("rsi", {})),
        MACDIndicator(**config.get("macd", {})),
        BollingerBands(**config.get("bollinger", {})),
        ATRIndicator(**config.get("atr", {})),
    ]

    for indicator in indicators:
        df = indicator.calculate(df)

    return df
