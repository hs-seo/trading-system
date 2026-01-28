"""
Data Metadata - 데이터 투명성을 위한 메타데이터 관리

모든 분석 결과에 데이터 출처, 기간, 신선도 등을 추적
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum
import json


class DataFreshness(Enum):
    """데이터 신선도"""
    REALTIME = "realtime"      # 실시간
    TODAY = "today"            # 오늘 데이터
    RECENT = "recent"          # 1주일 이내
    STALE = "stale"            # 1주일 이상
    VERY_STALE = "very_stale"  # 1개월 이상


@dataclass
class DataMeta:
    """개별 데이터셋 메타데이터"""
    symbol: str
    source: str                    # yfinance, krx, binance 등
    timeframe: str

    # 기간
    data_start: datetime           # 데이터 시작일
    data_end: datetime             # 데이터 종료일
    total_bars: int                # 전체 캔들 수
    trading_days: int              # 실제 거래일 수

    # 캐시/갱신
    fetched_at: datetime           # 데이터 수집 시점
    cached: bool = False           # 캐시된 데이터인지
    cache_age_minutes: int = 0     # 캐시 나이 (분)

    # 품질
    missing_bars: int = 0          # 누락된 캔들 수
    has_gaps: bool = False         # 갭 존재 여부
    quality_score: float = 100.0   # 데이터 품질 점수 (0-100)

    @property
    def freshness(self) -> DataFreshness:
        """데이터 신선도 판단"""
        age = datetime.now() - self.fetched_at
        if age < timedelta(minutes=5):
            return DataFreshness.REALTIME
        elif age < timedelta(days=1):
            return DataFreshness.TODAY
        elif age < timedelta(days=7):
            return DataFreshness.RECENT
        elif age < timedelta(days=30):
            return DataFreshness.STALE
        return DataFreshness.VERY_STALE

    @property
    def period_str(self) -> str:
        """기간 문자열"""
        days = (self.data_end - self.data_start).days
        if days < 30:
            return f"{days}일"
        elif days < 365:
            return f"{days // 30}개월"
        else:
            years = days / 365
            return f"{years:.1f}년"

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "source": self.source,
            "timeframe": self.timeframe,
            "data_start": self.data_start.isoformat(),
            "data_end": self.data_end.isoformat(),
            "total_bars": self.total_bars,
            "trading_days": self.trading_days,
            "period": self.period_str,
            "fetched_at": self.fetched_at.isoformat(),
            "freshness": self.freshness.value,
            "cached": self.cached,
            "cache_age_minutes": self.cache_age_minutes,
            "quality_score": self.quality_score,
            "missing_bars": self.missing_bars,
        }


@dataclass
class ScreeningMeta:
    """스크리닝 실행 메타데이터"""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # 범위
    market: str = ""
    universe_size: int = 0         # 검색 대상 종목 수
    screened_count: int = 0        # 실제 스크리닝된 수
    passed_count: int = 0          # 통과한 종목 수

    # 전략/필터
    strategy_name: str = ""
    filters_applied: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)

    # 데이터 품질
    data_sources: List[str] = field(default_factory=list)
    avg_data_quality: float = 0.0
    symbols_with_issues: List[str] = field(default_factory=list)

    # 성능
    execution_time_sec: float = 0.0
    errors: List[Dict] = field(default_factory=list)

    # 추가 메타데이터 (fetch_stats 등)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """통과율"""
        if self.screened_count == 0:
            return 0.0
        return (self.passed_count / self.screened_count) * 100

    def to_dict(self) -> Dict:
        result = {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "market": self.market,
            "universe_size": self.universe_size,
            "screened_count": self.screened_count,
            "passed_count": self.passed_count,
            "pass_rate": f"{self.pass_rate:.1f}%",
            "strategy_name": self.strategy_name,
            "filters_applied": self.filters_applied,
            "data_sources": self.data_sources,
            "avg_data_quality": self.avg_data_quality,
            "execution_time_sec": self.execution_time_sec,
            "error_count": len(self.errors),
        }
        # 추가 메타데이터 포함
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class SymbolAnalysisMeta:
    """개별 종목 분석 메타데이터"""
    symbol: str
    analyzed_at: datetime

    # 데이터
    data_meta: Optional[DataMeta] = None

    # 분석 결과
    indicators_calculated: List[str] = field(default_factory=list)
    signals_generated: int = 0

    # 점수
    scores: Dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    rank: int = 0

    # 컨텍스트
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def to_summary(self) -> str:
        """한 줄 요약"""
        data_info = ""
        if self.data_meta:
            data_info = f"[{self.data_meta.period_str}, {self.data_meta.freshness.value}]"

        warnings = f" ⚠️ {len(self.warnings)}" if self.warnings else ""

        return f"{self.symbol}: {self.final_score:.1f}점 (#{self.rank}) {data_info}{warnings}"


# ============================================================================
# 메타데이터 수집 유틸리티
# ============================================================================

def create_data_meta(
    symbol: str,
    source: str,
    timeframe: str,
    df,  # pandas DataFrame
    fetched_at: Optional[datetime] = None,
    cached: bool = False,
) -> DataMeta:
    """DataFrame에서 DataMeta 생성"""
    import pandas as pd

    if df is None or df.empty:
        return DataMeta(
            symbol=symbol,
            source=source,
            timeframe=timeframe,
            data_start=datetime.now(),
            data_end=datetime.now(),
            total_bars=0,
            trading_days=0,
            fetched_at=fetched_at or datetime.now(),
            cached=cached,
            quality_score=0.0,
        )

    # 기간 계산
    if "timestamp" in df.columns:
        timestamps = pd.to_datetime(df["timestamp"])
        data_start = timestamps.min()
        data_end = timestamps.max()
    else:
        data_start = df.index.min()
        data_end = df.index.max()

    # 예상 거래일 vs 실제
    expected_days = (data_end - data_start).days
    actual_bars = len(df)

    # 품질 점수 계산
    missing = 0
    if "close" in df.columns:
        missing = df["close"].isna().sum()

    quality = 100.0
    if actual_bars > 0:
        quality -= (missing / actual_bars) * 50  # 결측치 패널티

    # 갭 체크
    has_gaps = False
    if "timestamp" in df.columns and len(df) > 1:
        time_diffs = timestamps.diff().dropna()
        if timeframe == "1d":
            # 일봉에서 5일 이상 갭은 비정상
            has_gaps = any(time_diffs > pd.Timedelta(days=5))

    return DataMeta(
        symbol=symbol,
        source=source,
        timeframe=timeframe,
        data_start=data_start,
        data_end=data_end,
        total_bars=actual_bars,
        trading_days=actual_bars,  # 일봉 기준
        fetched_at=fetched_at or datetime.now(),
        cached=cached,
        missing_bars=missing,
        has_gaps=has_gaps,
        quality_score=max(0, quality),
    )
