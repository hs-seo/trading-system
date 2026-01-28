"""
Parquet Storage - 대용량 시계열 데이터 저장소

빅데이터 분석 및 ML 파이프라인에 적합
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging
import json

import pandas as pd

from core.interfaces import Storage, Timeframe, Market, AnalysisResult
from core.registry import register

logger = logging.getLogger(__name__)


@register("storage", "parquet")
class ParquetStorage(Storage):
    """
    Parquet 파일 기반 저장소

    특징:
    - 컬럼 기반 압축 (공간 효율)
    - 빠른 분석 쿼리
    - Pandas/Spark/Polars 호환
    - 파티셔닝 지원

    디렉토리 구조:
        base_path/
        ├── ohlcv/
        │   ├── symbol=AAPL/
        │   │   ├── timeframe=1d/
        │   │   │   └── data.parquet
        │   │   └── timeframe=1h/
        │   │       └── data.parquet
        │   └── symbol=MSFT/
        │       └── ...
        └── analysis/
            └── ...

    사용법:
        storage = ParquetStorage("./data")
        storage.save_ohlcv("AAPL", Timeframe.D1, df)
        df = storage.load_ohlcv("AAPL", Timeframe.D1)
    """

    name = "parquet"

    def __init__(
        self,
        base_path: str = "./data",
        compression: str = "snappy",  # snappy, gzip, zstd
        use_partitioning: bool = True,
    ):
        self.base_path = Path(base_path)
        self.compression = compression
        self.use_partitioning = use_partitioning

        # 디렉토리 생성
        self.ohlcv_path = self.base_path / "ohlcv"
        self.analysis_path = self.base_path / "analysis"
        self.meta_path = self.base_path / "meta"

        for path in [self.ohlcv_path, self.analysis_path, self.meta_path]:
            path.mkdir(parents=True, exist_ok=True)

    def _get_ohlcv_path(self, symbol: str, timeframe: Timeframe) -> Path:
        """OHLCV 파일 경로"""
        if self.use_partitioning:
            return self.ohlcv_path / f"symbol={symbol}" / f"timeframe={timeframe.value}" / "data.parquet"
        return self.ohlcv_path / f"{symbol}_{timeframe.value}.parquet"

    def save_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        data: pd.DataFrame,
    ) -> bool:
        """OHLCV 데이터 저장"""
        if data.empty:
            return False

        try:
            file_path = self._get_ohlcv_path(symbol, timeframe)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 기존 데이터와 병합
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                data = pd.concat([existing, data]).drop_duplicates(
                    subset=["timestamp"],
                    keep="last"
                ).sort_values("timestamp")

            # 저장
            data.to_parquet(
                file_path,
                compression=self.compression,
                index=False,
            )

            logger.debug(f"Saved {len(data)} rows to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save OHLCV: {e}")
            return False

    def load_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """OHLCV 데이터 로드"""
        try:
            file_path = self._get_ohlcv_path(symbol, timeframe)

            if not file_path.exists():
                return pd.DataFrame()

            # PyArrow 필터 사용 (대용량 시 효율적)
            filters = []
            if start:
                filters.append(("timestamp", ">=", start))
            if end:
                filters.append(("timestamp", "<=", end))

            df = pd.read_parquet(
                file_path,
                filters=filters if filters else None,
            )

            if not df.empty:
                df = df.sort_values("timestamp")

            return df

        except Exception as e:
            logger.error(f"Failed to load OHLCV: {e}")
            return pd.DataFrame()

    def save_analysis(self, result: AnalysisResult) -> bool:
        """분석 결과 저장"""
        try:
            file_path = self.analysis_path / f"{result.symbol.ticker}.parquet"

            # DataFrame으로 변환
            row = {
                "symbol": result.symbol.ticker,
                "timestamp": result.timestamp,
                "indicators": json.dumps(result.indicators),
                "scores": json.dumps(result.scores),
                "final_score": result.final_score,
                "rank": result.rank,
                "metadata": json.dumps(result.metadata),
            }
            df = pd.DataFrame([row])

            # 기존 데이터와 병합
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                df = pd.concat([existing, df])

            df.to_parquet(file_path, compression=self.compression, index=False)
            return True

        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
            return False

    def load_analysis(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[AnalysisResult]:
        """분석 결과 로드"""
        try:
            file_path = self.analysis_path / f"{symbol}.parquet"

            if not file_path.exists():
                return []

            df = pd.read_parquet(file_path)

            if start:
                df = df[df["timestamp"] >= start]
            if end:
                df = df[df["timestamp"] <= end]

            return []  # AnalysisResult 변환 (필요시 구현)

        except Exception as e:
            logger.error(f"Failed to load analysis: {e}")
            return []

    def get_last_update(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Optional[datetime]:
        """마지막 업데이트 시간"""
        df = self.load_ohlcv(symbol, timeframe)
        if df.empty:
            return None
        return df["timestamp"].max()

    def list_symbols(self, market: Optional[Market] = None) -> List[str]:
        """저장된 종목 목록"""
        symbols = set()

        if self.use_partitioning:
            for symbol_dir in self.ohlcv_path.glob("symbol=*"):
                symbol = symbol_dir.name.replace("symbol=", "")
                symbols.add(symbol)
        else:
            for file in self.ohlcv_path.glob("*.parquet"):
                symbol = file.stem.rsplit("_", 1)[0]
                symbols.add(symbol)

        return list(symbols)

    def delete_symbol(self, symbol: str) -> bool:
        """종목 데이터 삭제"""
        try:
            import shutil

            if self.use_partitioning:
                symbol_dir = self.ohlcv_path / f"symbol={symbol}"
                if symbol_dir.exists():
                    shutil.rmtree(symbol_dir)
            else:
                for file in self.ohlcv_path.glob(f"{symbol}_*.parquet"):
                    file.unlink()

            # 분석 결과도 삭제
            analysis_file = self.analysis_path / f"{symbol}.parquet"
            if analysis_file.exists():
                analysis_file.unlink()

            return True

        except Exception as e:
            logger.error(f"Failed to delete symbol {symbol}: {e}")
            return False

    def get_stats(self) -> dict:
        """저장소 통계"""
        def get_dir_size(path: Path) -> int:
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

        symbols = self.list_symbols()

        return {
            "base_path": str(self.base_path),
            "total_size_mb": get_dir_size(self.base_path) / (1024 * 1024),
            "ohlcv_size_mb": get_dir_size(self.ohlcv_path) / (1024 * 1024),
            "analysis_size_mb": get_dir_size(self.analysis_path) / (1024 * 1024),
            "unique_symbols": len(symbols),
            "compression": self.compression,
        }

    def optimize(self):
        """저장소 최적화 (재압축, 파티션 정리)"""
        logger.info("Optimizing parquet storage...")

        for symbol in self.list_symbols():
            for tf in Timeframe:
                file_path = self._get_ohlcv_path(symbol, tf)
                if file_path.exists():
                    try:
                        df = pd.read_parquet(file_path)
                        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
                        df.to_parquet(file_path, compression=self.compression, index=False)
                    except Exception as e:
                        logger.error(f"Failed to optimize {file_path}: {e}")

        logger.info("Optimization complete")


# ============================================================================
# Hybrid Storage (SQLite + Parquet)
# ============================================================================

class HybridStorage(Storage):
    """
    하이브리드 저장소

    - 메타데이터, 분석 결과: SQLite (빠른 쿼리)
    - OHLCV 시계열: Parquet (효율적 저장)

    사용법:
        storage = HybridStorage("./data")
    """

    name = "hybrid"

    def __init__(self, base_path: str = "./data"):
        from .sqlite_storage import SQLiteStorage

        self.parquet = ParquetStorage(base_path)
        self.sqlite = SQLiteStorage(f"{base_path}/meta.db")

    def save_ohlcv(self, symbol: str, timeframe: Timeframe, data: pd.DataFrame) -> bool:
        return self.parquet.save_ohlcv(symbol, timeframe, data)

    def load_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        return self.parquet.load_ohlcv(symbol, timeframe, start, end)

    def save_analysis(self, result: AnalysisResult) -> bool:
        return self.sqlite.save_analysis(result)

    def load_analysis(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[AnalysisResult]:
        return self.sqlite.load_analysis(symbol, start, end)

    def get_last_update(self, symbol: str, timeframe: Timeframe) -> Optional[datetime]:
        return self.parquet.get_last_update(symbol, timeframe)

    def list_symbols(self, market: Optional[Market] = None) -> List[str]:
        return self.parquet.list_symbols(market)
