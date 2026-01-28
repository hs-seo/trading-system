"""
Swing Screener Strategy - 스윙 트레이딩 스크리너

미너비니 스타일의 스윙 트레이딩 전략
"""
from datetime import datetime
from typing import Dict, List, Optional
import logging

import pandas as pd
import numpy as np

from core.interfaces import Strategy, Symbol, Timeframe, AnalysisResult, Signal, SignalType, Confidence
from core.registry import register

logger = logging.getLogger(__name__)


@register("strategy", "swing_screener")
class SwingScreener(Strategy):
    """
    스윙 트레이딩 스크리너

    조건:
    - 가격이 50MA 위
    - 50MA가 150MA 위
    - 150MA가 200MA 위
    - 52주 최저 대비 30% 이상 상승
    - 52주 최고 대비 25% 이하
    - 상대강도(RS) 80 이상
    """

    name = "swing_screener"

    def __init__(self, **params):
        self.params = params or {
            "price_above_ma50": True,
            "ma50_above_ma150": True,
            "ma150_above_ma200": True,
            "min_from_52w_low": 30,
            "max_from_52w_high": 25,
            "min_rs_rating": 80,
        }

    def screen(
        self,
        universe: List[Symbol],
        data: Dict[str, pd.DataFrame],
    ) -> List[AnalysisResult]:
        """종목 스크리닝"""
        results = []

        for symbol in universe:
            df = data.get(symbol.ticker)
            if df is None or df.empty:
                continue

            result = self.analyze(symbol, df)
            if result.final_score > 0:  # 점수가 있는 경우만
                results.append(result)

        # 점수순 정렬
        results.sort(key=lambda x: x.final_score, reverse=True)

        # 순위 부여
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def analyze(self, symbol: Symbol, data: pd.DataFrame) -> AnalysisResult:
        """분석 실행"""
        if data.empty or len(data) < 200:
            return AnalysisResult(
                symbol=symbol,
                timestamp=datetime.now(),
                signals=[],
                scores={},
                final_score=0.0,
                rank=0,
            )

        try:
            # 지표 계산
            indicators = self._calculate_indicators(data)

            # 신호 생성
            signals = self._generate_signals(symbol, data, indicators)

            # 점수 계산
            scores = self._calculate_scores(data, indicators)

            # 최종 점수
            final_score = sum(scores.values()) / len(scores) if scores else 0.0

            return AnalysisResult(
                symbol=symbol,
                timestamp=data.iloc[-1]["timestamp"],
                indicators=indicators,
                signals=signals,
                scores=scores,
                final_score=final_score,
                rank=0,  # 나중에 랭킹에서 설정
            )

        except Exception as e:
            logger.error(f"Failed to analyze {symbol}: {e}")
            return AnalysisResult(
                symbol=symbol,
                timestamp=datetime.now(),
                signals=[],
                scores={},
                final_score=0.0,
                rank=0,
            )

    def _calculate_indicators(self, data: pd.DataFrame) -> Dict:
        """지표 계산"""
        indicators = {}

        # 이동평균
        indicators["ma50"] = data["close"].rolling(50).mean()
        indicators["ma150"] = data["close"].rolling(150).mean()
        indicators["ma200"] = data["close"].rolling(200).mean()

        # 52주 고저
        indicators["52w_high"] = data["high"].rolling(252).max()  # 252 거래일 ≈ 1년
        indicators["52w_low"] = data["low"].rolling(252).min()

        # RSI (14일)
        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        indicators["rsi"] = 100 - (100 / (1 + rs))

        return indicators

    def _generate_signals(self, symbol: Symbol, data: pd.DataFrame, indicators: Dict) -> List[Signal]:
        """신호 생성"""
        signals = []
        latest = data.iloc[-1]

        # 추세 신호
        if (latest["close"] > indicators["ma50"].iloc[-1] and
            indicators["ma50"].iloc[-1] > indicators["ma150"].iloc[-1] and
            indicators["ma150"].iloc[-1] > indicators["ma200"].iloc[-1]):
            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=Confidence.MEDIUM,
                source=self.name,
                timestamp=data.iloc[-1]["timestamp"],
                price=data.iloc[-1]["close"],
                reason="Strong uptrend: Price > MA50 > MA150 > MA200"
            ))

        # RSI 신호
        rsi = indicators["rsi"].iloc[-1]
        if rsi < 30:
            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=Confidence.MEDIUM,
                source=self.name,
                timestamp=data.iloc[-1]["timestamp"],
                price=data.iloc[-1]["close"],
                reason=f"Oversold RSI: {rsi:.1f}"
            ))
        elif rsi > 70:
            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=Confidence.MEDIUM,
                source=self.name,
                timestamp=data.iloc[-1]["timestamp"],
                price=data.iloc[-1]["close"],
                reason=f"Overbought RSI: {rsi:.1f}"
            ))

        return signals

    def _calculate_scores(self, data: pd.DataFrame, indicators: Dict) -> Dict[str, float]:
        """점수 계산"""
        scores = {}
        latest = data.iloc[-1]

        # 추세 점수 (0-100)
        trend_score = 0
        if latest["close"] > indicators["ma50"].iloc[-1]:
            trend_score += 25
        if indicators["ma50"].iloc[-1] > indicators["ma150"].iloc[-1]:
            trend_score += 25
        if indicators["ma150"].iloc[-1] > indicators["ma200"].iloc[-1]:
            trend_score += 25
        if indicators["ma200"].iloc[-1] > indicators["ma200"].iloc[-50]:  # MA200 상승
            trend_score += 25
        scores["trend"] = trend_score

        # 모멘텀 점수
        momentum_score = 0
        rsi = indicators["rsi"].iloc[-1]
        if 40 <= rsi <= 60:
            momentum_score = 100
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            momentum_score = 75
        elif rsi < 30 or rsi > 70:
            momentum_score = 50
        scores["momentum"] = momentum_score

        # 가격 위치 점수
        position_score = 0
        high_52w = indicators["52w_high"].iloc[-1]
        low_52w = indicators["52w_low"].iloc[-1]
        current = latest["close"]

        if current > low_52w:
            pct_from_low = (current - low_52w) / (high_52w - low_52w) * 100
            if pct_from_low >= 30:
                position_score += 50
            if pct_from_low <= 75:  # 52주 최고 대비 25% 이하
                position_score += 50
        scores["position"] = position_score

        return scores