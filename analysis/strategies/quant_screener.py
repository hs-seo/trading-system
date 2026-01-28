"""
Quant Screener - 퀀트 기반 종목 스크리닝

텐배거 종목 발굴을 위한 멀티 팩터 스크리닝:
- 가치: 저 PER, 저 EV/EBITDA
- 수익성: 높은 ROIC, FCF Yield
- 성장: EBITDA 성장률
- 모멘텀: 눌림목 (6-12개월 상승 후 1-3개월 조정)
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

import pandas as pd
import numpy as np

from core.interfaces import (
    Strategy, Symbol, AnalysisResult, Signal,
    SignalType, Confidence, Market
)
from core.registry import register

logger = logging.getLogger(__name__)


@dataclass
class QuantScore:
    """퀀트 점수"""
    value_score: float = 0.0      # 가치 점수
    quality_score: float = 0.0    # 품질 점수
    growth_score: float = 0.0     # 성장 점수
    momentum_score: float = 0.0   # 모멘텀 점수
    total_score: float = 0.0      # 종합 점수


@register("strategy", "quant_screener")
class QuantScreener(Strategy):
    """
    퀀트 스크리너

    여러 팩터를 조합하여 종목 점수화 및 순위 산정

    사용법:
        screener = QuantScreener(
            max_per=15,
            min_roic=15,
            min_ebitda_growth=20
        )
        results = screener.screen(universe, data)
    """

    name = "quant_screener"
    description = "Multi-factor Quant Screener"

    default_params = {
        # 가치 필터
        "max_per": 15,
        "max_ev_ebitda": 10,
        "max_pbr": 3,

        # 수익성 필터
        "min_roic": 15,        # %
        "min_fcf_yield": 5,    # %
        "min_roe": 15,         # %

        # 성장 필터
        "min_revenue_growth": 10,   # %
        "min_ebitda_growth": 20,    # %

        # 모멘텀 필터 (눌림목)
        "min_return_6m": 20,   # 6개월 최소 상승률 %
        "min_return_12m": 30,  # 12개월 최소 상승률 %
        "max_return_1m": 0,    # 1개월 최대 상승률 % (조정 중)
        "max_return_3m": 10,   # 3개월 최대 상승률 % (조정 중)

        # 가중치 (합계 = 1.0)
        "weight_value": 0.25,
        "weight_quality": 0.25,
        "weight_growth": 0.25,
        "weight_momentum": 0.25,

        # 필터링
        "min_market_cap": 0,        # 최소 시가총액
        "exclude_sectors": [],      # 제외 섹터
        "min_total_score": 60,      # 최소 종합 점수
    }

    def screen(
        self,
        universe: List[Symbol],
        data: Dict[str, pd.DataFrame],
        ratios: Optional[Dict[str, Dict]] = None,  # symbol -> ratios dict
    ) -> List[AnalysisResult]:
        """
        종목 스크리닝

        Args:
            universe: 검색 대상 종목
            data: 가격 데이터 {symbol: DataFrame}
            ratios: 재무 비율 데이터 {symbol: {ratio_name: value}}

        Returns:
            점수순 정렬된 분석 결과
        """
        results = []

        for symbol in universe:
            ticker = symbol.ticker

            # 섹터 필터
            if symbol.sector in self.params["exclude_sectors"]:
                continue

            # 가격 데이터
            df = data.get(ticker)
            if df is None or df.empty:
                continue

            # 재무 비율
            symbol_ratios = ratios.get(ticker, {}) if ratios else {}

            # 점수 계산
            score = self._calculate_scores(df, symbol_ratios)

            # 최소 점수 필터
            if score.total_score < self.params["min_total_score"]:
                continue

            # 결과 생성
            result = AnalysisResult(
                symbol=symbol,
                timestamp=datetime.now(),
                scores={
                    "value": score.value_score,
                    "quality": score.quality_score,
                    "growth": score.growth_score,
                    "momentum": score.momentum_score,
                },
                final_score=score.total_score,
                metadata={
                    "ratios": symbol_ratios,
                    "momentum_data": self._get_momentum_data(df),
                }
            )
            results.append(result)

        # 점수순 정렬
        results.sort(key=lambda x: x.final_score, reverse=True)

        # 순위 부여
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _calculate_scores(
        self,
        df: pd.DataFrame,
        ratios: Dict[str, float]
    ) -> QuantScore:
        """점수 계산 (재무 데이터 유무에 따라 동적 가중치 적용)"""
        score = QuantScore()

        # 가치 점수
        score.value_score = self._calc_value_score(ratios)

        # 품질 점수
        score.quality_score = self._calc_quality_score(ratios)

        # 성장 점수
        score.growth_score = self._calc_growth_score(ratios)

        # 모멘텀 점수
        score.momentum_score = self._calc_momentum_score(df)

        # 동적 가중치 계산 (재무 데이터 유무에 따라)
        has_fundamental = bool(ratios) and any(
            ratios.get(k) is not None
            for k in ["PER", "EV_EBITDA", "ROIC", "FCF_Yield", "EBITDA_Growth"]
        )

        if has_fundamental:
            # 재무 데이터 있음: 원래 가중치
            w_value = self.params["weight_value"]
            w_quality = self.params["weight_quality"]
            w_growth = self.params["weight_growth"]
            w_momentum = self.params["weight_momentum"]
        else:
            # 재무 데이터 없음: 모멘텀 100%
            w_value = 0
            w_quality = 0
            w_growth = 0
            w_momentum = 1.0

        # 종합 점수
        score.total_score = (
            score.value_score * w_value +
            score.quality_score * w_quality +
            score.growth_score * w_growth +
            score.momentum_score * w_momentum
        )

        return score

    def _calc_value_score(self, ratios: Dict[str, float]) -> float:
        """가치 점수 (0-100)"""
        score = 0
        count = 0

        # PER
        per = ratios.get("PER")
        if per is not None and per > 0:
            count += 1
            if per <= 5:
                score += 100
            elif per <= self.params["max_per"]:
                score += 100 - (per - 5) * (100 / (self.params["max_per"] - 5))
            else:
                score += max(0, 50 - (per - self.params["max_per"]) * 5)

        # EV/EBITDA
        ev_ebitda = ratios.get("EV_EBITDA")
        if ev_ebitda is not None and ev_ebitda > 0:
            count += 1
            if ev_ebitda <= 5:
                score += 100
            elif ev_ebitda <= self.params["max_ev_ebitda"]:
                score += 100 - (ev_ebitda - 5) * (100 / (self.params["max_ev_ebitda"] - 5))
            else:
                score += max(0, 50 - (ev_ebitda - self.params["max_ev_ebitda"]) * 5)

        # PBR
        pbr = ratios.get("PBR")
        if pbr is not None and pbr > 0:
            count += 1
            if pbr <= 1:
                score += 100
            elif pbr <= self.params["max_pbr"]:
                score += 100 - (pbr - 1) * (100 / (self.params["max_pbr"] - 1))
            else:
                score += max(0, 50 - (pbr - self.params["max_pbr"]) * 20)

        return score / max(count, 1)

    def _calc_quality_score(self, ratios: Dict[str, float]) -> float:
        """품질 점수 (0-100)"""
        score = 0
        count = 0

        # ROIC
        roic = ratios.get("ROIC")
        if roic is not None:
            count += 1
            if roic >= 30:
                score += 100
            elif roic >= self.params["min_roic"]:
                score += 50 + (roic - self.params["min_roic"]) * (50 / (30 - self.params["min_roic"]))
            else:
                score += max(0, roic * (50 / self.params["min_roic"]))

        # FCF Yield
        fcf_yield = ratios.get("FCF_Yield")
        if fcf_yield is not None:
            count += 1
            if fcf_yield >= 10:
                score += 100
            elif fcf_yield >= self.params["min_fcf_yield"]:
                score += 50 + (fcf_yield - self.params["min_fcf_yield"]) * (50 / (10 - self.params["min_fcf_yield"]))
            else:
                score += max(0, fcf_yield * (50 / self.params["min_fcf_yield"]))

        # ROE
        roe = ratios.get("ROE")
        if roe is not None:
            count += 1
            if roe >= 25:
                score += 100
            elif roe >= self.params["min_roe"]:
                score += 50 + (roe - self.params["min_roe"]) * (50 / (25 - self.params["min_roe"]))
            else:
                score += max(0, roe * (50 / self.params["min_roe"]))

        return score / max(count, 1)

    def _calc_growth_score(self, ratios: Dict[str, float]) -> float:
        """성장 점수 (0-100)"""
        score = 0
        count = 0

        # 매출 성장률
        rev_growth = ratios.get("Revenue_Growth")
        if rev_growth is not None:
            count += 1
            if rev_growth >= 30:
                score += 100
            elif rev_growth >= self.params["min_revenue_growth"]:
                score += 50 + (rev_growth - self.params["min_revenue_growth"]) * (50 / (30 - self.params["min_revenue_growth"]))
            elif rev_growth > 0:
                score += rev_growth * (50 / self.params["min_revenue_growth"])

        # EBITDA 성장률
        ebitda_growth = ratios.get("EBITDA_Growth")
        if ebitda_growth is not None:
            count += 1
            if ebitda_growth >= 40:
                score += 100
            elif ebitda_growth >= self.params["min_ebitda_growth"]:
                score += 50 + (ebitda_growth - self.params["min_ebitda_growth"]) * (50 / (40 - self.params["min_ebitda_growth"]))
            elif ebitda_growth > 0:
                score += ebitda_growth * (50 / self.params["min_ebitda_growth"])

        return score / max(count, 1)

    def _calc_momentum_score(self, df: pd.DataFrame) -> float:
        """
        모멘텀 점수 (0-100)

        두 가지 모드:
        1. 눌림목 모드: max_return_1m <= 0 (단기 조정 필요)
        2. 강세 모드: max_return_1m > 0 (단순 상승 추세)
        """
        if len(df) < 126:  # 최소 6개월 데이터
            return 50  # 데이터 부족시 중립

        close = df["close"]
        current = close.iloc[-1]

        # 수익률 계산
        ret_1m = (current / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0
        ret_3m = (current / close.iloc[-63] - 1) * 100 if len(close) >= 63 else 0
        ret_6m = (current / close.iloc[-126] - 1) * 100 if len(close) >= 126 else 0
        ret_12m = (current / close.iloc[-252] - 1) * 100 if len(close) >= 252 else ret_6m

        score = 0

        # 파라미터 가져오기
        min_ret_6m = self.params.get("min_return_6m", 20)
        min_ret_12m = self.params.get("min_return_12m", 30)
        max_ret_1m = self.params.get("max_return_1m", 0)
        max_ret_3m = self.params.get("max_return_3m", 10)

        # 모드 판단: max_return_1m이 0 이하면 눌림목 모드
        is_pullback_mode = max_ret_1m <= 0

        if is_pullback_mode:
            # 눌림목 모드: 중장기 상승 + 단기 조정
            # 중장기 상승 (50점)
            if ret_6m >= min_ret_6m:
                score += 25
            if ret_12m >= min_ret_12m:
                score += 25

            # 단기 조정 (50점)
            if ret_1m <= max_ret_1m:
                score += 25
            elif ret_1m <= max_ret_1m + 10:
                score += 15

            if ret_3m <= max_ret_3m:
                score += 25
            elif ret_3m <= max_ret_3m + 10:
                score += 15
        else:
            # 강세 모드: 단순 상승 추세 확인
            # 6개월 상승 (40점)
            if ret_6m >= min_ret_6m:
                score += 40
            elif ret_6m >= min_ret_6m * 0.5:
                score += 20

            # 12개월 상승 (30점)
            if ret_12m >= min_ret_12m:
                score += 30
            elif ret_12m >= min_ret_12m * 0.5:
                score += 15

            # 과열 방지 (30점) - 너무 급등하지 않은 경우 가산
            if ret_1m <= max_ret_1m:
                score += 15
            if ret_3m <= max_ret_3m:
                score += 15

        return min(score, 100)

    def _get_momentum_data(self, df: pd.DataFrame) -> Dict[str, float]:
        """모멘텀 데이터 추출"""
        if len(df) < 21:
            return {}

        close = df["close"]
        current = close.iloc[-1]

        return {
            "return_1w": (current / close.iloc[-5] - 1) * 100 if len(close) >= 5 else None,
            "return_1m": (current / close.iloc[-21] - 1) * 100 if len(close) >= 21 else None,
            "return_3m": (current / close.iloc[-63] - 1) * 100 if len(close) >= 63 else None,
            "return_6m": (current / close.iloc[-126] - 1) * 100 if len(close) >= 126 else None,
            "return_12m": (current / close.iloc[-252] - 1) * 100 if len(close) >= 252 else None,
            "from_52w_high": (current / close.max() - 1) * 100,
            "from_52w_low": (current / close.min() - 1) * 100,
        }


@register("strategy", "quant_momentum")
class QuantMomentumScreener(Strategy):
    """
    스윙 트레이딩용 단기 모멘텀 스크리너

    미너비니/모글렌 스타일: 최근 강한 모멘텀 종목
    """

    name = "quant_momentum"
    description = "Short-term Momentum Screener"

    default_params = {
        # 모멘텀 필터
        "min_return_1m": 5,    # 1개월 최소 상승률
        "min_return_3m": 15,   # 3개월 최소 상승률

        # 가격 위치
        "min_from_52w_low": 30,   # 52주 저점 대비 최소 %
        "max_from_52w_high": 25,  # 52주 고점 대비 최대 % (고점 근처)

        # 기술적 조건
        "price_above_ma50": True,
        "price_above_ma200": True,
        "ma50_above_ma200": True,

        # RS Rating (상대강도)
        "min_rs_rating": 80,  # 상위 20%

        # 거래량
        "min_volume_ratio": 1.0,  # 평균 대비 최소 거래량

        "min_total_score": 70,
    }

    def screen(
        self,
        universe: List[Symbol],
        data: Dict[str, pd.DataFrame],
        ratios: Optional[Dict[str, Dict]] = None,
    ) -> List[AnalysisResult]:
        """스윙 트레이딩 후보 스크리닝"""
        results = []

        for symbol in universe:
            ticker = symbol.ticker
            df = data.get(ticker)

            if df is None or len(df) < 252:
                continue

            score = self._calculate_momentum_score(df)

            if score < self.params["min_total_score"]:
                continue

            results.append(AnalysisResult(
                symbol=symbol,
                timestamp=datetime.now(),
                final_score=score,
                metadata={
                    "momentum_data": self._get_momentum_data(df),
                    "technical": self._get_technical_data(df),
                }
            ))

        results.sort(key=lambda x: x.final_score, reverse=True)

        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """모멘텀 점수 계산"""
        score = 0
        close = df["close"]
        current = close.iloc[-1]

        # 수익률
        ret_1m = (current / close.iloc[-21] - 1) * 100
        ret_3m = (current / close.iloc[-63] - 1) * 100

        # 1개월 모멘텀 (30점)
        if ret_1m >= self.params["min_return_1m"]:
            score += min(30, 15 + ret_1m)

        # 3개월 모멘텀 (30점)
        if ret_3m >= self.params["min_return_3m"]:
            score += min(30, 15 + ret_3m * 0.5)

        # 가격 위치 (20점)
        from_high = (current / close.max() - 1) * 100
        from_low = (current / close.min() - 1) * 100

        if from_low >= self.params["min_from_52w_low"]:
            score += 10
        if abs(from_high) <= self.params["max_from_52w_high"]:
            score += 10

        # MA 조건 (20점)
        ma50 = close.rolling(50).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]

        if self.params["price_above_ma50"] and current > ma50:
            score += 7
        if self.params["price_above_ma200"] and current > ma200:
            score += 7
        if self.params["ma50_above_ma200"] and ma50 > ma200:
            score += 6

        return score

    def _get_momentum_data(self, df: pd.DataFrame) -> Dict:
        """모멘텀 데이터"""
        close = df["close"]
        current = close.iloc[-1]

        return {
            "return_1m": (current / close.iloc[-21] - 1) * 100,
            "return_3m": (current / close.iloc[-63] - 1) * 100,
            "from_52w_high": (current / close.max() - 1) * 100,
            "from_52w_low": (current / close.min() - 1) * 100,
        }

    def _get_technical_data(self, df: pd.DataFrame) -> Dict:
        """기술적 데이터"""
        close = df["close"]
        current = close.iloc[-1]

        ma50 = close.rolling(50).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]

        return {
            "price": current,
            "ma50": ma50,
            "ma200": ma200,
            "price_vs_ma50": (current / ma50 - 1) * 100,
            "price_vs_ma200": (current / ma200 - 1) * 100,
            "ma50_vs_ma200": (ma50 / ma200 - 1) * 100,
        }
