"""
Pipeline System - 데이터 처리 파이프라인

데이터 수집 → 지표 계산 → 분석 → 신호 생성 → 의사결정의 흐름을 관리합니다.
각 단계는 플러그인으로 교체/확장 가능합니다.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import logging
from abc import ABC, abstractmethod

from .events import EventBus, Event, EventType, get_event_bus
from .interfaces import (
    Symbol, Timeframe, AnalysisResult, Signal,
    DataSource, Storage, Indicator, Strategy, DecisionEngine
)

logger = logging.getLogger(__name__)


# ============================================================================
# Pipeline Context
# ============================================================================

@dataclass
class PipelineContext:
    """
    파이프라인 컨텍스트 - 파이프라인 실행 중 공유되는 상태

    각 단계에서 데이터를 추가/수정하며 다음 단계로 전달됩니다.
    """
    # 입력
    symbols: List[Symbol] = field(default_factory=list)
    timeframe: Timeframe = Timeframe.D1
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # 데이터 (단계별로 채워짐)
    raw_data: Dict[str, Any] = field(default_factory=dict)  # symbol -> OHLCV df
    indicators_data: Dict[str, Any] = field(default_factory=dict)  # symbol -> 지표 포함 df
    analysis_results: List[AnalysisResult] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)

    # 메타데이터
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict] = field(default_factory=list)

    # 실행 정보
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def add_error(self, stage: str, error: str, symbol: Optional[str] = None):
        """에러 기록"""
        self.errors.append({
            "stage": stage,
            "error": error,
            "symbol": symbol,
            "timestamp": datetime.now()
        })

    def get_execution_time(self) -> Optional[float]:
        """실행 시간 (초)"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# ============================================================================
# Pipeline Stage (Base)
# ============================================================================

class PipelineStage(ABC):
    """
    파이프라인 단계 추상 베이스 클래스

    새 단계 추가 시 이 클래스를 상속하세요.
    """

    name: str = "base_stage"
    order: int = 0  # 실행 순서 (낮을수록 먼저)

    def __init__(self):
        self.event_bus = get_event_bus()

    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        단계 실행 (동기)

        Args:
            context: 이전 단계에서 전달받은 컨텍스트

        Returns:
            다음 단계로 전달할 컨텍스트
        """
        pass

    async def process_async(self, context: PipelineContext) -> PipelineContext:
        """단계 실행 (비동기) - 기본은 동기 실행"""
        return self.process(context)

    def validate(self, context: PipelineContext) -> bool:
        """입력 검증"""
        return True

    def on_start(self, context: PipelineContext):
        """단계 시작 전 훅"""
        logger.debug(f"Starting stage: {self.name}")

    def on_complete(self, context: PipelineContext):
        """단계 완료 후 훅"""
        logger.debug(f"Completed stage: {self.name}")


# ============================================================================
# Built-in Pipeline Stages
# ============================================================================

class DataFetchStage(PipelineStage):
    """데이터 수집 단계"""

    name = "data_fetch"
    order = 10

    def __init__(self, source: DataSource, storage: Optional[Storage] = None):
        super().__init__()
        self.source = source
        self.storage = storage

    def process(self, context: PipelineContext) -> PipelineContext:
        for symbol in context.symbols:
            try:
                # 캐시 확인
                df = None
                if self.storage:
                    df = self.storage.load_ohlcv(
                        symbol.ticker,
                        context.timeframe,
                        context.start_date,
                        context.end_date
                    )

                # 캐시 없으면 소스에서 조회
                if df is None or df.empty:
                    df = self.source.fetch_ohlcv(
                        symbol.ticker,
                        context.timeframe,
                        context.start_date,
                        context.end_date
                    )

                    # 저장
                    if self.storage and df is not None and not df.empty:
                        self.storage.save_ohlcv(symbol.ticker, context.timeframe, df)

                context.raw_data[symbol.ticker] = df

                self.event_bus.publish(Event(
                    type=EventType.DATA_FETCHED,
                    data={"symbol": symbol.ticker, "rows": len(df) if df is not None else 0},
                    source=self.name
                ))

            except Exception as e:
                context.add_error(self.name, str(e), symbol.ticker)
                logger.error(f"Failed to fetch {symbol.ticker}: {e}")

        return context


class IndicatorStage(PipelineStage):
    """지표 계산 단계"""

    name = "indicator_calculation"
    order = 20

    def __init__(self, indicators: List[Indicator]):
        super().__init__()
        self.indicators = indicators

    def process(self, context: PipelineContext) -> PipelineContext:
        for symbol_ticker, df in context.raw_data.items():
            if df is None or df.empty:
                continue

            try:
                result_df = df.copy()

                for indicator in self.indicators:
                    result_df = indicator.calculate(result_df)

                    self.event_bus.publish(Event(
                        type=EventType.INDICATOR_CALCULATED,
                        data={
                            "symbol": symbol_ticker,
                            "indicator": indicator.name
                        },
                        source=self.name
                    ))

                context.indicators_data[symbol_ticker] = result_df

            except Exception as e:
                context.add_error(self.name, str(e), symbol_ticker)
                logger.error(f"Indicator calculation failed for {symbol_ticker}: {e}")

        return context


class AnalysisStage(PipelineStage):
    """분석/스크리닝 단계"""

    name = "analysis"
    order = 30

    def __init__(self, strategies: List[Strategy]):
        super().__init__()
        self.strategies = strategies

    def process(self, context: PipelineContext) -> PipelineContext:
        for strategy in self.strategies:
            try:
                self.event_bus.publish(Event(
                    type=EventType.ANALYSIS_STARTED,
                    data={"strategy": strategy.name},
                    source=self.name
                ))

                results = strategy.screen(
                    context.symbols,
                    context.indicators_data
                )

                context.analysis_results.extend(results)

                self.event_bus.publish(Event(
                    type=EventType.ANALYSIS_COMPLETED,
                    data={
                        "strategy": strategy.name,
                        "candidates": len(results)
                    },
                    source=self.name
                ))

            except Exception as e:
                context.add_error(self.name, str(e))
                logger.error(f"Analysis failed for strategy {strategy.name}: {e}")

        return context


class DecisionStage(PipelineStage):
    """의사결정 단계"""

    name = "decision"
    order = 40

    def __init__(self, engine: DecisionEngine):
        super().__init__()
        self.engine = engine

    def process(self, context: PipelineContext) -> PipelineContext:
        try:
            signals = self.engine.decide(
                context.analysis_results,
                context.metadata
            )

            context.signals.extend(signals)

            for signal in signals:
                self.event_bus.publish(Event(
                    type=EventType.SIGNAL_GENERATED,
                    data=signal,
                    source=self.name
                ))

            self.event_bus.publish(Event(
                type=EventType.DECISION_MADE,
                data={"signal_count": len(signals)},
                source=self.name
            ))

        except Exception as e:
            context.add_error(self.name, str(e))
            logger.error(f"Decision engine failed: {e}")

        return context


# ============================================================================
# Pipeline
# ============================================================================

class Pipeline:
    """
    메인 파이프라인 클래스

    여러 단계를 조합하여 전체 처리 흐름을 구성합니다.

    사용법:
        pipeline = Pipeline()
        pipeline.add_stage(DataFetchStage(source, storage))
        pipeline.add_stage(IndicatorStage(indicators))
        pipeline.add_stage(AnalysisStage(strategies))
        pipeline.add_stage(DecisionStage(engine))

        context = PipelineContext(symbols=symbols, timeframe=Timeframe.D1)
        result = pipeline.run(context)
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.stages: List[PipelineStage] = []
        self.event_bus = get_event_bus()
        self.hooks: Dict[str, List[Callable]] = {
            "before_pipeline": [],
            "after_pipeline": [],
            "before_stage": [],
            "after_stage": [],
            "on_error": [],
        }

    def add_stage(self, stage: PipelineStage) -> "Pipeline":
        """단계 추가"""
        self.stages.append(stage)
        self.stages.sort(key=lambda s: s.order)
        return self

    def remove_stage(self, stage_name: str) -> "Pipeline":
        """단계 제거"""
        self.stages = [s for s in self.stages if s.name != stage_name]
        return self

    def add_hook(self, hook_type: str, callback: Callable) -> "Pipeline":
        """훅 추가"""
        if hook_type in self.hooks:
            self.hooks[hook_type].append(callback)
        return self

    def _run_hooks(self, hook_type: str, *args, **kwargs):
        """훅 실행"""
        for callback in self.hooks.get(hook_type, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook {hook_type} failed: {e}")

    def run(self, context: PipelineContext) -> PipelineContext:
        """파이프라인 실행 (동기)"""
        context.started_at = datetime.now()

        self.event_bus.publish(Event(
            type=EventType.SYSTEM_STARTED,
            data={"pipeline": self.name, "stages": [s.name for s in self.stages]},
            source="pipeline"
        ))

        self._run_hooks("before_pipeline", context)

        for stage in self.stages:
            try:
                self._run_hooks("before_stage", stage, context)
                stage.on_start(context)

                if not stage.validate(context):
                    logger.warning(f"Validation failed for stage: {stage.name}")
                    continue

                context = stage.process(context)

                stage.on_complete(context)
                self._run_hooks("after_stage", stage, context)

            except Exception as e:
                context.add_error(stage.name, str(e))
                self._run_hooks("on_error", stage, e, context)
                logger.error(f"Pipeline stage {stage.name} failed: {e}")

        context.completed_at = datetime.now()
        self._run_hooks("after_pipeline", context)

        self.event_bus.publish(Event(
            type=EventType.SYSTEM_STOPPED,
            data={
                "pipeline": self.name,
                "execution_time": context.get_execution_time(),
                "signals": len(context.signals),
                "errors": len(context.errors)
            },
            source="pipeline"
        ))

        return context

    async def run_async(self, context: PipelineContext) -> PipelineContext:
        """파이프라인 실행 (비동기)"""
        context.started_at = datetime.now()

        await self.event_bus.publish_async(Event(
            type=EventType.SYSTEM_STARTED,
            data={"pipeline": self.name},
            source="pipeline"
        ))

        self._run_hooks("before_pipeline", context)

        for stage in self.stages:
            try:
                self._run_hooks("before_stage", stage, context)
                stage.on_start(context)

                if not stage.validate(context):
                    continue

                context = await stage.process_async(context)

                stage.on_complete(context)
                self._run_hooks("after_stage", stage, context)

            except Exception as e:
                context.add_error(stage.name, str(e))
                self._run_hooks("on_error", stage, e, context)

        context.completed_at = datetime.now()
        self._run_hooks("after_pipeline", context)

        return context


# ============================================================================
# Pipeline Builder (Fluent API)
# ============================================================================

class PipelineBuilder:
    """
    파이프라인 빌더 - Fluent API로 파이프라인 구성

    사용법:
        pipeline = (PipelineBuilder("my_pipeline")
            .with_source(yfinance_source)
            .with_storage(sqlite_storage)
            .with_indicators([rsi, macd, smc])
            .with_strategies([quant_screener])
            .with_decision_engine(ensemble_engine)
            .build())
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.source: Optional[DataSource] = None
        self.storage: Optional[Storage] = None
        self.indicators: List[Indicator] = []
        self.strategies: List[Strategy] = []
        self.engine: Optional[DecisionEngine] = None

    def with_source(self, source: DataSource) -> "PipelineBuilder":
        """데이터 소스 설정"""
        self.source = source
        return self

    def with_storage(self, storage: Storage) -> "PipelineBuilder":
        """저장소 설정"""
        self.storage = storage
        return self

    def with_indicators(self, indicators: List[Indicator]) -> "PipelineBuilder":
        """인디케이터 설정"""
        self.indicators = indicators
        return self

    def add_indicator(self, indicator: Indicator) -> "PipelineBuilder":
        """인디케이터 추가"""
        self.indicators.append(indicator)
        return self

    def with_strategies(self, strategies: List[Strategy]) -> "PipelineBuilder":
        """전략 설정"""
        self.strategies = strategies
        return self

    def add_strategy(self, strategy: Strategy) -> "PipelineBuilder":
        """전략 추가"""
        self.strategies.append(strategy)
        return self

    def with_decision_engine(self, engine: DecisionEngine) -> "PipelineBuilder":
        """결정 엔진 설정"""
        self.engine = engine
        return self

    def build(self) -> Pipeline:
        """파이프라인 생성"""
        pipeline = Pipeline(self.name)

        if self.source:
            pipeline.add_stage(DataFetchStage(self.source, self.storage))

        if self.indicators:
            pipeline.add_stage(IndicatorStage(self.indicators))

        if self.strategies:
            pipeline.add_stage(AnalysisStage(self.strategies))

        if self.engine:
            pipeline.add_stage(DecisionStage(self.engine))

        return pipeline


# ============================================================================
# Pre-built Pipelines
# ============================================================================

def create_screening_pipeline(
    source: DataSource,
    storage: Storage,
    indicators: List[Indicator],
    strategies: List[Strategy],
    engine: DecisionEngine,
) -> Pipeline:
    """
    표준 스크리닝 파이프라인 생성

    데이터 조회 → 지표 계산 → 분석 → 의사결정
    """
    return (PipelineBuilder("screening")
        .with_source(source)
        .with_storage(storage)
        .with_indicators(indicators)
        .with_strategies(strategies)
        .with_decision_engine(engine)
        .build())
