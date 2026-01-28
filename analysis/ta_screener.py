"""
Technical Analysis Screener - 기술적 분석 스크리너

패턴 기반 종목 스크리닝:
- Price Action: 핀바, 잉걸핑, 스타, 삼병
- SMC: Order Block, Supply/Demand
- Double Patterns: 쌍바닥/쌍봉
- Liquidity: 유동성 스윕

각 시그널에 대해 Entry/SL/TP/RR 계산
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import logging
import concurrent.futures

from .patterns import (
    PriceActionDetector,
    DoublePatternDetector,
    SMCDetector,
    LiquidityDetector,
)
from .patterns.price_action import PatternSignal, PatternDirection, PatternStrength

logger = logging.getLogger(__name__)


@dataclass
class ScreenerConfig:
    """스크리너 설정"""
    # 활성화할 패턴
    enable_price_action: bool = True
    enable_smc: bool = True
    enable_double_patterns: bool = True
    enable_liquidity: bool = True

    # Price Action 설정
    pa_patterns: List[str] = field(default_factory=lambda: ["pinbar", "engulfing", "star", "three_soldiers"])
    pa_tail_ratio: float = 2.0
    pa_use_trend_filter: bool = True

    # SMC 설정
    smc_swing_length: int = 5
    smc_min_score: int = 6
    smc_min_grade: str = "B"

    # Double Pattern 설정
    dp_sma_length: int = 20
    dp_pivot_left: int = 5
    dp_pivot_right: int = 5
    dp_tolerance: float = 0.03

    # Liquidity 설정
    liq_lookback: int = 20
    liq_threshold_pct: float = 0.3
    liq_use_volume: bool = True

    # 필터
    min_confidence: float = 50.0     # 최소 신뢰도
    min_rr_ratio: float = 1.0        # 최소 RR 비율 (TP1 기준)
    direction_filter: str = "all"    # "all", "long", "short"
    lookback_bars: int = 10          # 최근 N개 바에서 시그널 탐색


@dataclass
class ScreeningResult:
    """스크리닝 결과"""
    symbol: str
    signals: List[PatternSignal]
    timestamp: datetime = field(default_factory=datetime.now)

    # 요약
    long_signals: int = 0
    short_signals: int = 0
    best_signal: Optional[PatternSignal] = None

    # 메타
    data_bars: int = 0
    patterns_checked: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": str(self.timestamp),
            "long_signals": self.long_signals,
            "short_signals": self.short_signals,
            "total_signals": len(self.signals),
            "best_signal": self.best_signal.to_dict() if self.best_signal else None,
            "signals": [s.to_dict() for s in self.signals],
        }


class TAScreener:
    """기술적 분석 스크리너"""

    def __init__(self, config: ScreenerConfig = None):
        self.config = config or ScreenerConfig()

        # 감지기 초기화
        self.pa_detector = PriceActionDetector(
            pinbar_tail_ratio=self.config.pa_tail_ratio,
            use_trend_filter=self.config.pa_use_trend_filter,
        )

        self.smc_detector = SMCDetector(
            swing_length=self.config.smc_swing_length,
            min_score=self.config.smc_min_score,
            min_grade=self.config.smc_min_grade,
        )

        self.dp_detector = DoublePatternDetector(
            sma_length=self.config.dp_sma_length,
            pivot_left=self.config.dp_pivot_left,
            pivot_right=self.config.dp_pivot_right,
            tolerance=self.config.dp_tolerance,
        )

        self.liq_detector = LiquidityDetector(
            lookback=self.config.liq_lookback,
            threshold_pct=self.config.liq_threshold_pct,
            use_volume_filter=self.config.liq_use_volume,
        )

    def screen_symbol(
        self,
        symbol: str,
        df: pd.DataFrame,
    ) -> ScreeningResult:
        """
        단일 종목 스크리닝

        Args:
            symbol: 종목 심볼
            df: OHLCV DataFrame (지표 포함)
        """
        all_signals = []
        patterns_checked = []

        # 1. Price Action 패턴
        if self.config.enable_price_action:
            patterns_checked.append("price_action")
            try:
                pa_signals = self.pa_detector.get_latest_signals(
                    df,
                    lookback_bars=self.config.lookback_bars,
                    patterns=self.config.pa_patterns,
                )
                all_signals.extend(pa_signals)
            except Exception as e:
                logger.warning(f"[{symbol}] Price Action 감지 오류: {e}")

        # 2. SMC 패턴
        if self.config.enable_smc:
            patterns_checked.append("smc")
            try:
                smc_signals = self.smc_detector.get_latest_signals(
                    df,
                    lookback_bars=self.config.lookback_bars,
                )
                all_signals.extend(smc_signals)
            except Exception as e:
                logger.warning(f"[{symbol}] SMC 감지 오류: {e}")

        # 3. Double Pattern
        if self.config.enable_double_patterns:
            patterns_checked.append("double_patterns")
            try:
                dp_signals = self.dp_detector.get_latest_signals(
                    df,
                    lookback_bars=self.config.lookback_bars,
                )
                all_signals.extend(dp_signals)
            except Exception as e:
                logger.warning(f"[{symbol}] Double Pattern 감지 오류: {e}")

        # 4. Liquidity Sweep
        if self.config.enable_liquidity:
            patterns_checked.append("liquidity")
            try:
                liq_signals = self.liq_detector.get_latest_signals(
                    df,
                    lookback_bars=self.config.lookback_bars,
                )
                all_signals.extend(liq_signals)
            except Exception as e:
                logger.warning(f"[{symbol}] Liquidity 감지 오류: {e}")

        # 필터 적용
        filtered_signals = self._apply_filters(all_signals)

        # 결과 생성
        long_signals = [s for s in filtered_signals if s.direction == PatternDirection.BULLISH]
        short_signals = [s for s in filtered_signals if s.direction == PatternDirection.BEARISH]

        # 최고 신뢰도 시그널
        best_signal = None
        if filtered_signals:
            best_signal = max(filtered_signals, key=lambda x: x.confidence)

        return ScreeningResult(
            symbol=symbol,
            signals=filtered_signals,
            long_signals=len(long_signals),
            short_signals=len(short_signals),
            best_signal=best_signal,
            data_bars=len(df),
            patterns_checked=patterns_checked,
        )

    def _apply_filters(self, signals: List[PatternSignal]) -> List[PatternSignal]:
        """필터 적용"""
        filtered = []

        for signal in signals:
            # 신뢰도 필터
            if signal.confidence < self.config.min_confidence:
                continue

            # RR 필터 (기본 1:1 이상)
            if signal.risk_amount > 0:
                rr = abs(signal.take_profit_1 - signal.entry_price) / signal.risk_amount
                if rr < self.config.min_rr_ratio:
                    continue

            # 방향 필터
            if self.config.direction_filter == "long" and signal.direction != PatternDirection.BULLISH:
                continue
            if self.config.direction_filter == "short" and signal.direction != PatternDirection.BEARISH:
                continue

            filtered.append(signal)

        return filtered

    def screen_universe(
        self,
        symbols: List[str],
        data_fetcher: Callable[[str], pd.DataFrame],
        workers: int = 5,
        progress_callback: Callable = None,
    ) -> List[ScreeningResult]:
        """
        유니버스 전체 스크리닝

        Args:
            symbols: 종목 리스트
            data_fetcher: 데이터 가져오기 함수 fn(symbol) -> DataFrame
            workers: 병렬 워커 수
            progress_callback: fn(current, total, symbol, status)
        """
        results = []
        total = len(symbols)

        def process_symbol(symbol: str) -> Optional[ScreeningResult]:
            try:
                df = data_fetcher(symbol)
                if df is None or df.empty:
                    return None
                return self.screen_symbol(symbol, df)
            except Exception as e:
                logger.error(f"[{symbol}] 스크리닝 오류: {e}")
                return None

        # 병렬 처리
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_symbol, sym): sym for sym in symbols}

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                symbol = futures[future]
                try:
                    result = future.result()
                    if result and result.signals:
                        results.append(result)
                    status = "OK" if result and result.signals else "No Signal"
                except Exception as e:
                    status = "Error"
                    logger.error(f"[{symbol}] 처리 오류: {e}")

                if progress_callback:
                    progress_callback(i + 1, total, symbol, status)

        # 시그널 수로 정렬
        results.sort(key=lambda x: len(x.signals), reverse=True)

        return results

    def get_summary(self, results: List[ScreeningResult]) -> Dict:
        """스크리닝 결과 요약"""
        total_signals = sum(len(r.signals) for r in results)
        total_long = sum(r.long_signals for r in results)
        total_short = sum(r.short_signals for r in results)

        # 패턴별 집계
        pattern_counts = {}
        for result in results:
            for signal in result.signals:
                pt = signal.pattern_type
                pattern_counts[pt] = pattern_counts.get(pt, 0) + 1

        # 상위 종목
        top_long = [r for r in results if r.long_signals > 0]
        top_long.sort(key=lambda x: x.long_signals, reverse=True)

        top_short = [r for r in results if r.short_signals > 0]
        top_short.sort(key=lambda x: x.short_signals, reverse=True)

        return {
            "total_symbols_screened": len(results),
            "symbols_with_signals": len([r for r in results if r.signals]),
            "total_signals": total_signals,
            "long_signals": total_long,
            "short_signals": total_short,
            "pattern_breakdown": pattern_counts,
            "top_long_symbols": [{"symbol": r.symbol, "signals": r.long_signals} for r in top_long[:10]],
            "top_short_symbols": [{"symbol": r.symbol, "signals": r.short_signals} for r in top_short[:10]],
        }

    def to_dataframe(self, results: List[ScreeningResult]) -> pd.DataFrame:
        """결과를 DataFrame으로 변환"""
        rows = []

        for result in results:
            for signal in result.signals:
                rows.append({
                    "symbol": result.symbol,
                    "pattern": signal.pattern_type,
                    "direction": signal.direction.value,
                    "strength": signal.strength.value,
                    "timestamp": signal.timestamp,
                    "entry": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "tp1": signal.take_profit_1,
                    "tp2": signal.take_profit_2,
                    "tp3": signal.take_profit_3,
                    "risk": signal.risk_amount,
                    "rr1": signal.risk_reward_1,
                    "rr2": signal.risk_reward_2,
                    "confidence": signal.confidence,
                    "rationale": signal.rationale,
                })

        return pd.DataFrame(rows)


# === 편의 함수 ===

def quick_screen(
    symbols: List[str],
    data_fetcher: Callable[[str], pd.DataFrame],
    direction: str = "all",
    min_confidence: float = 50.0,
    patterns: List[str] = None,
    workers: int = 5,
    progress_callback: Callable = None,
) -> List[ScreeningResult]:
    """
    빠른 스크리닝

    Args:
        symbols: 종목 리스트
        data_fetcher: 데이터 가져오기 함수
        direction: "all", "long", "short"
        min_confidence: 최소 신뢰도
        patterns: 검색할 패턴 ["price_action", "smc", "double_patterns", "liquidity"]
        workers: 병렬 워커 수
        progress_callback: 진행률 콜백

    Returns:
        시그널이 있는 종목 결과 리스트
    """
    all_patterns = patterns or ["price_action", "smc", "double_patterns", "liquidity"]

    config = ScreenerConfig(
        enable_price_action="price_action" in all_patterns,
        enable_smc="smc" in all_patterns,
        enable_double_patterns="double_patterns" in all_patterns,
        enable_liquidity="liquidity" in all_patterns,
        min_confidence=min_confidence,
        direction_filter=direction,
    )

    screener = TAScreener(config)
    return screener.screen_universe(
        symbols,
        data_fetcher,
        workers=workers,
        progress_callback=progress_callback,
    )


def scan_for_pattern(
    symbols: List[str],
    data_fetcher: Callable[[str], pd.DataFrame],
    pattern_type: str,
    workers: int = 5,
) -> List[ScreeningResult]:
    """
    특정 패턴만 스캔

    Args:
        symbols: 종목 리스트
        data_fetcher: 데이터 가져오기 함수
        pattern_type: "pinbar", "engulfing", "star", "three_soldiers",
                      "double_bottom", "double_top", "smc", "liquidity_sweep"
        workers: 병렬 워커 수
    """
    # 패턴 타입에 따라 설정
    config = ScreenerConfig(
        enable_price_action=pattern_type in ["pinbar", "engulfing", "star", "three_soldiers"],
        enable_smc=pattern_type == "smc",
        enable_double_patterns=pattern_type in ["double_bottom", "double_top"],
        enable_liquidity=pattern_type == "liquidity_sweep",
    )

    if pattern_type in ["pinbar", "engulfing", "star", "three_soldiers"]:
        config.pa_patterns = [pattern_type]

    screener = TAScreener(config)
    return screener.screen_universe(symbols, data_fetcher, workers=workers)
