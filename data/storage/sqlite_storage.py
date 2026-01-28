"""
SQLite Storage - 경량 로컬 데이터베이스 저장소

개발 및 소규모 사용에 적합
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging
import json

import pandas as pd

from core.interfaces import Storage, Timeframe, Market, AnalysisResult, Signal
from core.registry import register

logger = logging.getLogger(__name__)


@register("storage", "sqlite")
class SQLiteStorage(Storage):
    """
    SQLite 저장소

    특징:
    - 설치 불필요 (Python 내장)
    - 파일 기반 (쉬운 백업/이동)
    - 중소규모 데이터에 적합

    사용법:
        storage = SQLiteStorage("./data/trading.db")
        storage.save_ohlcv("AAPL", Timeframe.D1, df)
        df = storage.load_ohlcv("AAPL", Timeframe.D1)
    """

    name = "sqlite"

    def __init__(self, db_path: str = "./data/trading.db"):
        import sqlite3
        self.sqlite3 = sqlite3

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self):
        """DB 연결"""
        return self.sqlite3.connect(self.db_path)

    def _init_db(self):
        """테이블 초기화"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # OHLCV 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, timestamp)
                )
            """)

            # 인덱스
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_tf_ts
                ON ohlcv(symbol, timeframe, timestamp)
            """)

            # 분석 결과 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    strategy TEXT,
                    indicators_json TEXT,
                    signals_json TEXT,
                    scores_json TEXT,
                    final_score REAL,
                    rank INTEGER,
                    metadata_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_symbol_ts
                ON analysis_results(symbol, timestamp)
            """)

            # 종목 메타데이터 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    ticker TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT,
                    sector TEXT,
                    industry TEXT,
                    meta_json TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

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
            with self._get_connection() as conn:
                # UPSERT 처리
                for _, row in data.iterrows():
                    conn.execute("""
                        INSERT OR REPLACE INTO ohlcv
                        (symbol, timeframe, timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        timeframe.value,
                        str(row["timestamp"]),
                        row["open"],
                        row["high"],
                        row["low"],
                        row["close"],
                        row["volume"],
                    ))

                conn.commit()
                logger.debug(f"Saved {len(data)} rows for {symbol}/{timeframe.value}")
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
            query = """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
            """
            params = [symbol, timeframe.value]

            if start:
                query += " AND timestamp >= ?"
                params.append(start)
            if end:
                query += " AND timestamp <= ?"
                params.append(end)

            query += " ORDER BY timestamp"

            with self._get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)

            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            return df

        except Exception as e:
            logger.error(f"Failed to load OHLCV: {e}")
            return pd.DataFrame()

    def save_analysis(self, result: AnalysisResult) -> bool:
        """분석 결과 저장"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO analysis_results
                    (symbol, timestamp, indicators_json, signals_json,
                     scores_json, final_score, rank, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.symbol.ticker,
                    result.timestamp,
                    json.dumps(result.indicators),
                    json.dumps([self._signal_to_dict(s) for s in result.signals]),
                    json.dumps(result.scores),
                    result.final_score,
                    result.rank,
                    json.dumps(result.metadata),
                ))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
            return False

    def _signal_to_dict(self, signal: Signal) -> dict:
        """Signal을 dict로 변환"""
        return {
            "symbol": signal.symbol.ticker,
            "signal_type": signal.signal_type.value,
            "confidence": signal.confidence.value,
            "source": signal.source,
            "timestamp": signal.timestamp.isoformat(),
            "price": signal.price,
            "reason": signal.reason,
        }

    def load_analysis(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[AnalysisResult]:
        """분석 결과 로드"""
        try:
            query = """
                SELECT * FROM analysis_results
                WHERE symbol = ?
            """
            params = [symbol]

            if start:
                query += " AND timestamp >= ?"
                params.append(start)
            if end:
                query += " AND timestamp <= ?"
                params.append(end)

            query += " ORDER BY timestamp DESC"

            with self._get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)

            # AnalysisResult로 변환 (생략, 필요시 구현)
            return []

        except Exception as e:
            logger.error(f"Failed to load analysis: {e}")
            return []

    def get_last_update(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Optional[datetime]:
        """마지막 업데이트 시간"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT MAX(timestamp) FROM ohlcv
                    WHERE symbol = ? AND timeframe = ?
                """, (symbol, timeframe.value))
                result = cursor.fetchone()

                if result and result[0]:
                    return pd.to_datetime(result[0])
                return None

        except Exception as e:
            logger.error(f"Failed to get last update: {e}")
            return None

    def list_symbols(self, market: Optional[Market] = None) -> List[str]:
        """저장된 종목 목록"""
        try:
            query = "SELECT DISTINCT symbol FROM ohlcv"
            params = []

            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to list symbols: {e}")
            return []

    def save_symbols_metadata(self, symbols: list) -> bool:
        """종목 메타데이터 저장"""
        try:
            with self._get_connection() as conn:
                for s in symbols:
                    conn.execute("""
                        INSERT OR REPLACE INTO symbols
                        (ticker, name, market, sector, industry, meta_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        s.ticker,
                        s.name,
                        s.market.value if s.market else None,
                        s.sector,
                        s.industry,
                        json.dumps(s.meta),
                        datetime.now(),
                    ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save symbols metadata: {e}")
            return False

    def vacuum(self):
        """DB 최적화"""
        with self._get_connection() as conn:
            conn.execute("VACUUM")

    def get_stats(self) -> dict:
        """저장소 통계"""
        with self._get_connection() as conn:
            ohlcv_count = conn.execute(
                "SELECT COUNT(*) FROM ohlcv"
            ).fetchone()[0]

            symbol_count = conn.execute(
                "SELECT COUNT(DISTINCT symbol) FROM ohlcv"
            ).fetchone()[0]

            analysis_count = conn.execute(
                "SELECT COUNT(*) FROM analysis_results"
            ).fetchone()[0]

        return {
            "db_path": str(self.db_path),
            "db_size_mb": self.db_path.stat().st_size / (1024 * 1024),
            "ohlcv_rows": ohlcv_count,
            "unique_symbols": symbol_count,
            "analysis_results": analysis_count,
        }
