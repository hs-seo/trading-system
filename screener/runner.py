"""
Screener Runner - 스크리닝 실행 엔진

아이디어 + 유니버스 = 스크리닝 결과
FastFetcher 통합으로 병렬 데이터 수집 지원
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import uuid
import logging
import sys
from pathlib import Path

from core.interfaces import Symbol, Timeframe, AnalysisResult
from core.metadata import ScreeningMeta, DataMeta, create_data_meta
from .ideas import ScreenerIdea, IdeaManager
from .universe import Universe, UniverseManager

# FastFetcher 임포트
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.fast_fetcher import FastFetcher, FetchStats

logger = logging.getLogger(__name__)


@dataclass
class ScreeningResult:
    """스크리닝 결과"""
    # 메타
    meta: ScreeningMeta

    # 결과
    candidates: List[AnalysisResult]

    # 데이터 품질
    data_metas: Dict[str, DataMeta] = field(default_factory=dict)

    # 요약
    top_10: List[str] = field(default_factory=list)

    def get_summary(self) -> Dict:
        """결과 요약"""
        return {
            "run_id": self.meta.run_id,
            "strategy": self.meta.strategy_name,
            "market": self.meta.market,
            "universe_size": self.meta.universe_size,
            "passed": self.meta.passed_count,
            "pass_rate": f"{self.meta.pass_rate:.1f}%",
            "execution_time": f"{self.meta.execution_time_sec:.2f}s",
            "top_10": self.top_10,
            "avg_data_quality": f"{self.meta.avg_data_quality:.1f}%",
        }

    def to_dataframe(self):
        """결과를 DataFrame으로 변환"""
        import pandas as pd

        rows = []
        for c in self.candidates:
            row = {
                "rank": c.rank,
                "ticker": c.symbol.ticker,
                "name": c.symbol.name,
                "score": c.final_score,
            }
            row.update(c.scores)

            # 메타데이터에서 추가 정보
            if "momentum_data" in c.metadata:
                md = c.metadata["momentum_data"]
                row["return_1m"] = md.get("return_1m")
                row["return_3m"] = md.get("return_3m")
                row["return_6m"] = md.get("return_6m")

            # 데이터 품질
            dm = self.data_metas.get(c.symbol.ticker)
            if dm:
                row["data_period"] = dm.period_str
                row["data_freshness"] = dm.freshness.value
                row["data_quality"] = dm.quality_score

            rows.append(row)

        return pd.DataFrame(rows)


class ScreenerRunner:
    """스크리닝 실행기"""

    def __init__(
        self,
        idea_manager: Optional[IdeaManager] = None,
        universe_manager: Optional[UniverseManager] = None,
        cache_dir: str = "./data/cache",
    ):
        self.idea_manager = idea_manager or IdeaManager()
        self.universe_manager = universe_manager or UniverseManager()
        self.history: List[ScreeningResult] = []
        self.fast_fetcher = FastFetcher(cache_dir=cache_dir)

    def run(
        self,
        idea_id: str,
        universe_id: str,
        data_source=None,  # DataSource (optional, FastFetcher used if None)
        storage=None,  # Storage (optional)
        days: int = 365,
        workers: int = 10,
        use_cache: bool = True,
        progress_callback: Optional[Callable] = None,
        filter_overrides: Optional[Dict[str, Any]] = None,
    ) -> ScreeningResult:
        """
        스크리닝 실행

        Args:
            idea_id: 스크리닝 아이디어 ID
            universe_id: 유니버스 ID
            data_source: 데이터 소스 (None이면 FastFetcher 사용)
            storage: 저장소 (optional)
            days: 데이터 기간 (일)
            workers: 병렬 워커 수 (FastFetcher 사용 시)
            use_cache: 캐시 사용 여부
            progress_callback: 진행률 콜백 fn(current, total, symbol, status)
            filter_overrides: 필터 오버라이드 (아이디어 기본값 덮어쓰기)
        """
        run_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        # 아이디어 & 유니버스 로드
        idea = self.idea_manager.get(idea_id)
        universe = self.universe_manager.get(universe_id)

        if not idea:
            raise ValueError(f"Unknown idea: {idea_id}")
        if not universe:
            raise ValueError(f"Unknown universe: {universe_id}")

        # 필터 오버라이드 적용
        if filter_overrides:
            # 아이디어 복제 후 필터 덮어쓰기
            import copy
            idea = copy.deepcopy(idea)
            idea.filters.update(filter_overrides)
            logger.info(f"Filter overrides applied: {list(filter_overrides.keys())}")

        logger.info(f"Starting screening: {idea.name} on {universe.name} ({len(universe.symbols)} symbols)")

        # 메타데이터 초기화
        source_name = data_source.name if data_source else "FastFetcher"
        meta = ScreeningMeta(
            run_id=run_id,
            started_at=started_at,
            market=universe.market.value if universe.market else "",
            universe_size=len(universe.symbols),
            strategy_name=idea.strategy_type or idea.name,
            filters_applied=list(idea.filters.keys()),
            data_sources=[source_name],
        )

        # 데이터 수집 (FastFetcher 또는 기존 방식)
        tickers = [s.ticker for s in universe.symbols]

        if data_source is None:
            # FastFetcher 사용 (병렬 수집)
            data, fetch_stats = self.fast_fetcher.fetch_many(
                symbols=tickers,
                days=days,
                workers=workers,
                use_cache=use_cache,
                progress_callback=progress_callback,
            )
            meta.screened_count = fetch_stats.success
            meta.symbols_with_issues = [t for t in tickers if t not in data]

            # 캐시 통계 추가
            meta.metadata["fetch_stats"] = {
                "total": fetch_stats.total,
                "success": fetch_stats.success,
                "cached": fetch_stats.cached,
                "failed": fetch_stats.failed,
                "fetch_time_sec": fetch_stats.elapsed_sec,
            }
        else:
            # 기존 방식 (순차 수집)
            data = self._fetch_sequential(data_source, tickers, days, meta)

        # 데이터 메타 생성
        data_metas, quality_scores = self._create_data_metas(data, source_name)

        # 전략 실행
        candidates = self._run_strategy(idea, universe.symbols, data)

        meta.passed_count = len(candidates)
        meta.avg_data_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # 완료
        meta.completed_at = datetime.now()
        meta.execution_time_sec = (meta.completed_at - meta.started_at).total_seconds()

        result = ScreeningResult(
            meta=meta,
            candidates=candidates,
            data_metas=data_metas,
            top_10=[c.symbol.ticker for c in candidates[:10]],
        )

        # 히스토리 저장
        self.history.append(result)

        logger.info(
            f"Screening complete: {meta.passed_count}/{meta.screened_count} passed "
            f"in {meta.execution_time_sec:.2f}s"
        )

        return result

    def _fetch_sequential(
        self,
        data_source,
        tickers: List[str],
        days: int,
        meta: ScreeningMeta,
    ) -> Dict[str, Any]:
        """순차 데이터 수집 (기존 방식)"""
        data: Dict[str, Any] = {}
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        for ticker in tickers:
            try:
                df = data_source.fetch_ohlcv(
                    ticker,
                    Timeframe.D1,
                    start_date,
                    end_date,
                )

                if df is not None and not df.empty:
                    data[ticker] = df
                    meta.screened_count += 1
                else:
                    meta.symbols_with_issues.append(ticker)

            except Exception as e:
                logger.error(f"Failed to fetch {ticker}: {e}")
                meta.errors.append({
                    "symbol": ticker,
                    "error": str(e),
                })

        return data

    def _create_data_metas(
        self,
        data: Dict[str, Any],
        source_name: str,
    ) -> tuple:
        """데이터 메타 생성"""
        data_metas: Dict[str, DataMeta] = {}
        quality_scores = []

        for ticker, df in data.items():
            dm = create_data_meta(
                symbol=ticker,
                source=source_name,
                timeframe="1d",
                df=df,
            )
            data_metas[ticker] = dm
            quality_scores.append(dm.quality_score)

        return data_metas, quality_scores

    def _run_strategy(
        self,
        idea: ScreenerIdea,
        symbols: List[Symbol],
        data: Dict[str, Any],
    ) -> List[AnalysisResult]:
        """전략 실행"""
        # 전략 타입에 따라 적절한 스크리너 사용
        strategy_type = idea.strategy_type

        try:
            if strategy_type == "quant_screener":
                from analysis.strategies import QuantScreener
                strategy = QuantScreener(**idea.filters)

            elif strategy_type == "swing_screener":
                from analysis.strategies import SwingScreener
                strategy = SwingScreener(**idea.filters)

            else:
                # 기본 스윙 스크리너 사용
                from analysis.strategies import SwingScreener
                strategy = SwingScreener(**idea.filters)

            return strategy.screen(symbols, data)

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            return []

    def run_quick(
        self,
        idea_id: str,
        symbols: List[str],
        data_source=None,
        days: int = 365,
        workers: int = 10,
        use_cache: bool = True,
        progress_callback: Optional[Callable] = None,
    ) -> ScreeningResult:
        """
        빠른 스크리닝 (심볼 직접 지정)

        Args:
            idea_id: 스크리닝 아이디어 ID
            symbols: 티커 리스트
            data_source: 데이터 소스 (None이면 FastFetcher 사용)
            days: 데이터 기간
            workers: 병렬 워커 수
            use_cache: 캐시 사용 여부
            progress_callback: 진행률 콜백
        """
        # 임시 유니버스 생성
        temp_universe = Universe(
            id="temp",
            name="Quick Screen",
            type=None,
        )
        for ticker in symbols:
            temp_universe.add_symbol(Symbol(ticker=ticker, name=ticker, market=None))

        self.universe_manager.universes["temp"] = temp_universe

        return self.run(
            idea_id, "temp", data_source,
            days=days, workers=workers,
            use_cache=use_cache, progress_callback=progress_callback,
        )

    def compare_ideas(
        self,
        idea_ids: List[str],
        universe_id: str,
        data_source=None,
        workers: int = 10,
        use_cache: bool = True,
    ) -> Dict[str, ScreeningResult]:
        """
        여러 아이디어 비교

        첫 번째 실행에서 캐시를 채우고, 이후 실행은 캐시 활용
        """
        results = {}
        for i, idea_id in enumerate(idea_ids):
            try:
                # 첫 번째 이후는 캐시에서 빠르게 로드
                result = self.run(
                    idea_id, universe_id, data_source,
                    workers=workers, use_cache=use_cache,
                )
                results[idea_id] = result
            except Exception as e:
                logger.error(f"Failed to run {idea_id}: {e}")

        return results

    def get_history(self, limit: int = 10) -> List[Dict]:
        """실행 히스토리"""
        return [r.get_summary() for r in self.history[-limit:]]

    def export_result(self, result: ScreeningResult, filepath: str, format: str = "csv"):
        """결과 내보내기"""
        df = result.to_dataframe()

        if format == "csv":
            df.to_csv(filepath, index=False)
        elif format == "excel":
            df.to_excel(filepath, index=False)
        elif format == "json":
            df.to_json(filepath, orient="records", indent=2)

    def run_full_market(
        self,
        idea_id: str,
        market: str = "korea",  # korea, us, crypto
        top_n: int = 500,
        days: int = 365,
        workers: int = 15,
        progress_callback: Optional[Callable] = None,
    ) -> ScreeningResult:
        """
        전체 시장 스크리닝 (대량)

        Args:
            idea_id: 아이디어 ID
            market: 시장 (korea, us, crypto)
            top_n: 상위 N개 종목만 (시가총액 기준)
            days: 데이터 기간
            workers: 병렬 워커 수
            progress_callback: 진행률 콜백
        """
        from data.fast_fetcher import PreFilter

        # 시장별 종목 가져오기
        if market == "korea":
            symbols = PreFilter.filter_korea_top_n(top_n)
        elif market == "us":
            symbols = PreFilter.filter_us_by_index("sp500")[:top_n]
        else:
            symbols = []

        if not symbols:
            raise ValueError(f"No symbols found for market: {market}")

        logger.info(f"Full market screening: {market} top {len(symbols)} symbols")

        return self.run_quick(
            idea_id, symbols,
            days=days, workers=workers,
            progress_callback=progress_callback,
        )

    def get_cache_stats(self) -> Dict:
        """캐시 통계"""
        return self.fast_fetcher.get_cache_stats()

    def clear_cache(self, older_than_hours: int = None):
        """캐시 정리"""
        self.fast_fetcher.clear_cache(older_than_hours)
        logger.info(f"Cache cleared (older_than_hours={older_than_hours})")
