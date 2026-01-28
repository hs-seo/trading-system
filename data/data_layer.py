"""
Data Layer Manager - 데이터 레이어 통합 관리

주요 기능:
1. 프리페칭: 자주 사용하는 유니버스 미리 로드
2. 지표 캐싱: RSI, MACD, MA 등 사전 계산
3. 스마트 캐시: 시장 시간 기반 만료 정책
4. 백그라운드 갱신: 스케줄러 기반 자동 업데이트
"""
import sqlite3
import threading
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MarketSession(Enum):
    """시장 세션"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


@dataclass
class CachePolicy:
    """캐시 정책"""
    ttl_regular: int = 300          # 정규장 중 TTL (초) - 5분
    ttl_after_hours: int = 1800     # 장후 TTL (초) - 30분
    ttl_closed: int = 43200         # 장 마감 후 TTL (초) - 12시간
    ttl_indicators: int = 3600      # 지표 캐시 TTL (초) - 1시간
    max_cache_size_mb: int = 500    # 최대 캐시 크기 (MB)
    eviction_threshold: float = 0.9 # 캐시 정리 시작 임계값


@dataclass
class PrefetchConfig:
    """프리페칭 설정"""
    enabled: bool = True
    universes: List[str] = field(default_factory=lambda: ["sp500", "kospi200", "nasdaq100"])
    priority_symbols: List[str] = field(default_factory=list)  # 우선 로드 심볼
    workers: int = 5
    batch_size: int = 50
    interval_minutes: int = 30      # 자동 갱신 주기


@dataclass
class IndicatorCache:
    """지표 캐시 항목"""
    symbol: str
    indicator_name: str
    params_hash: str
    data: pd.DataFrame
    computed_at: datetime
    data_hash: str  # 원본 데이터 해시 (변경 감지용)


class MarketHours:
    """시장 시간 관리"""

    # 시장별 거래 시간 (UTC 기준)
    MARKET_HOURS = {
        "us": {
            "pre_market": (9, 0),    # 09:00 UTC = 04:00 EST
            "open": (14, 30),        # 14:30 UTC = 09:30 EST
            "close": (21, 0),        # 21:00 UTC = 16:00 EST
            "after_hours_end": (1, 0),  # 01:00 UTC = 20:00 EST
            "timezone": "America/New_York",
        },
        "korea": {
            "open": (0, 0),          # 00:00 UTC = 09:00 KST
            "close": (6, 30),        # 06:30 UTC = 15:30 KST
            "timezone": "Asia/Seoul",
        },
        "crypto": {
            "open": (0, 0),
            "close": (23, 59),       # 24시간
            "timezone": "UTC",
        },
    }

    @classmethod
    def get_session(cls, market: str = "us") -> MarketSession:
        """현재 시장 세션 반환"""
        now = datetime.utcnow()
        hours = cls.MARKET_HOURS.get(market, cls.MARKET_HOURS["us"])

        if market == "crypto":
            return MarketSession.REGULAR

        hour, minute = now.hour, now.minute
        current_time = hour * 60 + minute

        open_time = hours["open"][0] * 60 + hours["open"][1]
        close_time = hours["close"][0] * 60 + hours["close"][1]

        # 주말 체크
        if now.weekday() >= 5:
            return MarketSession.CLOSED

        if market == "us":
            pre_market = hours["pre_market"][0] * 60 + hours["pre_market"][1]
            if pre_market <= current_time < open_time:
                return MarketSession.PRE_MARKET
            elif open_time <= current_time < close_time:
                return MarketSession.REGULAR
            elif close_time <= current_time:
                return MarketSession.AFTER_HOURS
            else:
                return MarketSession.CLOSED
        else:
            if open_time <= current_time < close_time:
                return MarketSession.REGULAR
            else:
                return MarketSession.CLOSED

    @classmethod
    def get_ttl(cls, market: str, policy: CachePolicy) -> int:
        """현재 세션에 맞는 TTL 반환"""
        session = cls.get_session(market)

        if session == MarketSession.REGULAR:
            return policy.ttl_regular
        elif session == MarketSession.AFTER_HOURS:
            return policy.ttl_after_hours
        else:
            return policy.ttl_closed


class IndicatorComputer:
    """지표 계산기"""

    @staticmethod
    def compute_all(df: pd.DataFrame, indicators: List[str] = None) -> pd.DataFrame:
        """
        모든 기본 지표 계산

        Args:
            df: OHLCV DataFrame
            indicators: 계산할 지표 목록 (None이면 전체)

        Returns:
            지표가 추가된 DataFrame
        """
        if df is None or df.empty:
            return df

        result = df.copy()
        all_indicators = indicators or ["ma", "rsi", "macd", "bb", "atr", "volume"]

        try:
            if "ma" in all_indicators:
                result = IndicatorComputer._add_ma(result)
            if "rsi" in all_indicators:
                result = IndicatorComputer._add_rsi(result)
            if "macd" in all_indicators:
                result = IndicatorComputer._add_macd(result)
            if "bb" in all_indicators:
                result = IndicatorComputer._add_bollinger(result)
            if "atr" in all_indicators:
                result = IndicatorComputer._add_atr(result)
            if "volume" in all_indicators:
                result = IndicatorComputer._add_volume_indicators(result)
            if "momentum" in all_indicators:
                result = IndicatorComputer._add_momentum(result)
        except Exception as e:
            logger.warning(f"Indicator computation error: {e}")

        return result

    @staticmethod
    def _add_ma(df: pd.DataFrame) -> pd.DataFrame:
        """이동평균 추가"""
        for period in [5, 10, 20, 50, 100, 150, 200]:
            df[f"ma{period}"] = df["close"].rolling(window=period).mean()
        # 이동평균 기울기
        df["ma20_slope"] = df["ma20"].diff(5) / 5
        df["ma50_slope"] = df["ma50"].diff(10) / 10
        return df

    @staticmethod
    def _add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI 추가"""
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.inf)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50)
        return df

    @staticmethod
    def _add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """MACD 추가"""
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        return df

    @staticmethod
    def _add_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """볼린저 밴드 추가"""
        ma = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()
        df["bb_upper"] = ma + (std * std_dev)
        df["bb_middle"] = ma
        df["bb_lower"] = ma - (std * std_dev)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
        df["bb_pct"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
        return df

    @staticmethod
    def _add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """ATR 추가"""
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=period).mean()
        df["atr_pct"] = df["atr"] / df["close"] * 100
        return df

    @staticmethod
    def _add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """거래량 지표 추가"""
        df["volume_ma20"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma20"]
        # OBV
        df["obv"] = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
        return df

    @staticmethod
    def _add_momentum(df: pd.DataFrame) -> pd.DataFrame:
        """모멘텀 지표 추가"""
        # 수익률
        for period in [5, 10, 20, 60, 120, 250]:
            df[f"return_{period}d"] = df["close"].pct_change(period) * 100

        # 52주 고/저점
        df["high_52w"] = df["high"].rolling(window=250).max()
        df["low_52w"] = df["low"].rolling(window=250).min()
        df["from_52w_high"] = (df["close"] / df["high_52w"] - 1) * 100
        df["from_52w_low"] = (df["close"] / df["low_52w"] - 1) * 100

        return df

    @staticmethod
    def get_data_hash(df: pd.DataFrame) -> str:
        """DataFrame 해시 생성 (변경 감지용)"""
        if df is None or df.empty:
            return ""
        # 마지막 행의 데이터로 해시 생성
        last_row = df.iloc[-1].to_string()
        return hashlib.md5(last_row.encode()).hexdigest()[:16]


class DataLayerManager:
    """데이터 레이어 통합 관리자"""

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        cache_policy: CachePolicy = None,
        prefetch_config: PrefetchConfig = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_policy = cache_policy or CachePolicy()
        self.prefetch_config = prefetch_config or PrefetchConfig()

        # 캐시 DB
        self.cache_db_path = self.cache_dir / "data_layer.db"
        self._init_db()

        # 인메모리 캐시
        self._indicator_cache: Dict[str, IndicatorCache] = {}
        self._ohlcv_cache: Dict[str, pd.DataFrame] = {}

        # 상태
        self._prefetch_thread: Optional[threading.Thread] = None
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # 통계
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "prefetch_count": 0,
            "indicator_cache_hits": 0,
        }

        # FastFetcher 참조
        self._fast_fetcher = None

    def _init_db(self):
        """DB 초기화"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # 지표 캐시 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicator_cache (
                symbol TEXT,
                indicator_name TEXT,
                params_hash TEXT,
                data BLOB,
                computed_at TEXT,
                data_hash TEXT,
                PRIMARY KEY (symbol, indicator_name, params_hash)
            )
        """)

        # 프리페치 상태 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prefetch_status (
                universe_id TEXT PRIMARY KEY,
                last_prefetch TEXT,
                symbol_count INTEGER,
                success_count INTEGER,
                duration_sec REAL
            )
        """)

        # 사용 통계 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                symbol TEXT PRIMARY KEY,
                access_count INTEGER DEFAULT 0,
                last_access TEXT,
                avg_response_ms REAL
            )
        """)

        conn.commit()
        conn.close()

    @property
    def fast_fetcher(self):
        """FastFetcher 지연 로딩"""
        if self._fast_fetcher is None:
            from data.fast_fetcher import FastFetcher
            self._fast_fetcher = FastFetcher(cache_dir=str(self.cache_dir))
        return self._fast_fetcher

    # =========================================================================
    # 프리페칭
    # =========================================================================

    def prefetch_universe(
        self,
        universe_id: str,
        symbols: List[str] = None,
        days: int = 365,
        compute_indicators: bool = True,
        progress_callback: Callable = None,
    ) -> Dict[str, Any]:
        """
        유니버스 프리페칭

        Args:
            universe_id: 유니버스 ID
            symbols: 심볼 목록 (None이면 자동 로드)
            days: 데이터 기간
            compute_indicators: 지표 사전 계산 여부
            progress_callback: 진행률 콜백

        Returns:
            프리페칭 결과
        """
        start_time = time.time()

        # 심볼 목록 로드
        if symbols is None:
            symbols = self._load_universe_symbols(universe_id)

        if not symbols:
            return {"success": False, "error": "No symbols found"}

        logger.info(f"Prefetching {len(symbols)} symbols for {universe_id}")

        # 데이터 페칭
        data, fetch_stats = self.fast_fetcher.fetch_many(
            symbols=symbols,
            days=days,
            workers=self.prefetch_config.workers,
            use_cache=True,
            progress_callback=progress_callback,
        )

        # 지표 사전 계산
        if compute_indicators and data:
            self._precompute_indicators(data, progress_callback)

        duration = time.time() - start_time

        # 상태 저장
        self._save_prefetch_status(
            universe_id=universe_id,
            symbol_count=len(symbols),
            success_count=fetch_stats.success,
            duration=duration,
        )

        self.stats["prefetch_count"] += len(symbols)

        return {
            "success": True,
            "universe_id": universe_id,
            "total": len(symbols),
            "fetched": fetch_stats.success,
            "cached": fetch_stats.cached,
            "failed": fetch_stats.failed,
            "duration_sec": duration,
            "indicators_computed": compute_indicators,
        }

    def _load_universe_symbols(self, universe_id: str) -> List[str]:
        """유니버스 심볼 로드"""
        # 내장 유니버스
        builtin = {
            "sp500": self._load_sp500,
            "nasdaq100": self._load_nasdaq100,
            "kospi200": self._load_kospi200,
            "kosdaq150": self._load_kosdaq150,
        }

        if universe_id in builtin:
            return builtin[universe_id]()

        # 커스텀 유니버스는 UniverseManager에서 로드
        try:
            from screener.universe import UniverseManager
            um = UniverseManager()
            universe = um.get(universe_id)
            if universe:
                return [s.ticker for s in universe.symbols]
        except Exception:
            pass

        return []

    def _load_sp500(self) -> List[str]:
        """S&P 500 심볼 로드"""
        json_path = self.cache_dir.parent / "universe_symbols.json"
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
                return data.get("sp500", [])
        return []

    def _load_nasdaq100(self) -> List[str]:
        """NASDAQ 100 심볼 로드"""
        json_path = self.cache_dir.parent / "universe_symbols.json"
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
                return data.get("nasdaq100", [])
        return []

    def _load_kospi200(self) -> List[str]:
        """KOSPI 200 심볼 로드"""
        try:
            import FinanceDataReader as fdr
            df = fdr.StockListing("KOSPI")
            # 시가총액 상위 200개
            return df.nlargest(200, "Marcap")["Code"].tolist()
        except Exception:
            return []

    def _load_kosdaq150(self) -> List[str]:
        """KOSDAQ 150 심볼 로드"""
        try:
            import FinanceDataReader as fdr
            df = fdr.StockListing("KOSDAQ")
            return df.nlargest(150, "Marcap")["Code"].tolist()
        except Exception:
            return []

    def _precompute_indicators(
        self,
        data: Dict[str, pd.DataFrame],
        progress_callback: Callable = None,
    ):
        """지표 사전 계산"""
        total = len(data)
        for i, (symbol, df) in enumerate(data.items()):
            try:
                # 지표 계산
                df_with_indicators = IndicatorComputer.compute_all(df)

                # 캐시 저장
                self._save_indicator_cache(symbol, "all", df_with_indicators)

                if progress_callback and i % 10 == 0:
                    progress_callback(i, total, symbol, "indicators")

            except Exception as e:
                logger.warning(f"Indicator computation failed for {symbol}: {e}")

    def _save_indicator_cache(self, symbol: str, indicator_name: str, df: pd.DataFrame):
        """지표 캐시 저장"""
        data_hash = IndicatorComputer.get_data_hash(df)

        # 인메모리 캐시
        cache_key = f"{symbol}_{indicator_name}"
        self._indicator_cache[cache_key] = IndicatorCache(
            symbol=symbol,
            indicator_name=indicator_name,
            params_hash="default",
            data=df,
            computed_at=datetime.now(),
            data_hash=data_hash,
        )

        # DB 저장 (선택적)
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO indicator_cache
                (symbol, indicator_name, params_hash, data, computed_at, data_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                indicator_name,
                "default",
                df.to_json().encode(),
                datetime.now().isoformat(),
                data_hash,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to save indicator cache: {e}")

    def _save_prefetch_status(
        self,
        universe_id: str,
        symbol_count: int,
        success_count: int,
        duration: float,
    ):
        """프리페치 상태 저장"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prefetch_status
            (universe_id, last_prefetch, symbol_count, success_count, duration_sec)
            VALUES (?, ?, ?, ?, ?)
        """, (
            universe_id,
            datetime.now().isoformat(),
            symbol_count,
            success_count,
            duration,
        ))
        conn.commit()
        conn.close()

    # =========================================================================
    # 데이터 조회 (캐시 통합)
    # =========================================================================

    def get_data(
        self,
        symbol: str,
        days: int = 365,
        with_indicators: bool = True,
        indicators: List[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        데이터 조회 (캐시 우선)

        Args:
            symbol: 심볼
            days: 기간
            with_indicators: 지표 포함 여부
            indicators: 특정 지표만 (None이면 전체)

        Returns:
            DataFrame (OHLCV + 지표)
        """
        start_time = time.time()

        # 1. 지표 캐시 확인
        if with_indicators:
            cache_key = f"{symbol}_all"
            if cache_key in self._indicator_cache:
                cache = self._indicator_cache[cache_key]
                # TTL 확인
                if (datetime.now() - cache.computed_at).seconds < self.cache_policy.ttl_indicators:
                    self.stats["indicator_cache_hits"] += 1
                    self._record_access(symbol, time.time() - start_time)
                    return cache.data

        # 2. OHLCV 데이터 페칭
        data, _ = self.fast_fetcher.fetch_many(
            symbols=[symbol],
            days=days,
            use_cache=True,
        )

        if symbol not in data:
            self.stats["cache_misses"] += 1
            return None

        df = data[symbol]
        self.stats["cache_hits"] += 1

        # 3. 지표 계산
        if with_indicators:
            df = IndicatorComputer.compute_all(df, indicators)
            self._save_indicator_cache(symbol, "all", df)

        self._record_access(symbol, time.time() - start_time)
        return df

    def get_data_batch(
        self,
        symbols: List[str],
        days: int = 365,
        with_indicators: bool = True,
        workers: int = 10,
        progress_callback: Callable = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        배치 데이터 조회

        Args:
            symbols: 심볼 목록
            days: 기간
            with_indicators: 지표 포함
            workers: 병렬 워커
            progress_callback: 진행률 콜백

        Returns:
            {symbol: DataFrame} 딕셔너리
        """
        # OHLCV 페칭
        data, _ = self.fast_fetcher.fetch_many(
            symbols=symbols,
            days=days,
            workers=workers,
            use_cache=True,
            progress_callback=progress_callback,
        )

        # 지표 계산
        if with_indicators:
            result = {}
            for i, (symbol, df) in enumerate(data.items()):
                df_with_ind = IndicatorComputer.compute_all(df)
                result[symbol] = df_with_ind
                self._save_indicator_cache(symbol, "all", df_with_ind)

                if progress_callback and i % 20 == 0:
                    progress_callback(i, len(data), symbol, "indicators")

            return result

        return data

    def _record_access(self, symbol: str, response_time_ms: float):
        """접근 통계 기록"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_stats (symbol, access_count, last_access, avg_response_ms)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    access_count = access_count + 1,
                    last_access = ?,
                    avg_response_ms = (avg_response_ms + ?) / 2
            """, (
                symbol,
                datetime.now().isoformat(),
                response_time_ms * 1000,
                datetime.now().isoformat(),
                response_time_ms * 1000,
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    # =========================================================================
    # 백그라운드 스케줄러
    # =========================================================================

    def start_background_tasks(self):
        """백그라운드 작업 시작"""
        if self._running:
            return

        self._running = True

        # 프리페치 스레드
        if self.prefetch_config.enabled:
            self._prefetch_thread = threading.Thread(
                target=self._prefetch_worker,
                daemon=True,
            )
            self._prefetch_thread.start()

        # 스케줄러 스레드
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_worker,
            daemon=True,
        )
        self._scheduler_thread.start()

        logger.info("Background tasks started")

    def stop_background_tasks(self):
        """백그라운드 작업 중지"""
        self._running = False
        logger.info("Background tasks stopped")

    def _prefetch_worker(self):
        """프리페치 워커"""
        while self._running:
            try:
                for universe_id in self.prefetch_config.universes:
                    if not self._running:
                        break

                    # 마지막 프리페치 시간 확인
                    if self._should_prefetch(universe_id):
                        logger.info(f"Auto-prefetching {universe_id}")
                        self.prefetch_universe(universe_id)

                # 대기
                for _ in range(self.prefetch_config.interval_minutes * 60):
                    if not self._running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Prefetch worker error: {e}")
                time.sleep(60)

    def _should_prefetch(self, universe_id: str) -> bool:
        """프리페치 필요 여부"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_prefetch FROM prefetch_status WHERE universe_id = ?
            """, (universe_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return True

            last_prefetch = datetime.fromisoformat(row[0])
            elapsed = (datetime.now() - last_prefetch).total_seconds() / 60

            return elapsed >= self.prefetch_config.interval_minutes

        except Exception:
            return True

    def _scheduler_worker(self):
        """스케줄러 워커 (캐시 정리 등)"""
        while self._running:
            try:
                # 캐시 크기 확인 및 정리
                self._check_and_cleanup_cache()

                # 1시간마다 실행
                for _ in range(3600):
                    if not self._running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Scheduler worker error: {e}")
                time.sleep(60)

    def _check_and_cleanup_cache(self):
        """캐시 정리"""
        try:
            # 캐시 크기 확인
            cache_size_mb = sum(
                f.stat().st_size for f in self.cache_dir.glob("*.db")
            ) / (1024 * 1024)

            if cache_size_mb > self.cache_policy.max_cache_size_mb * self.cache_policy.eviction_threshold:
                logger.info(f"Cache size ({cache_size_mb:.1f}MB) exceeds threshold, cleaning up")

                # 오래된 지표 캐시 정리
                cutoff = datetime.now() - timedelta(hours=24)
                with self._lock:
                    keys_to_remove = [
                        k for k, v in self._indicator_cache.items()
                        if v.computed_at < cutoff
                    ]
                    for k in keys_to_remove:
                        del self._indicator_cache[k]

                logger.info(f"Removed {len(keys_to_remove)} expired indicator caches")

        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

    # =========================================================================
    # 상태 조회
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        # 캐시 크기
        cache_size_mb = sum(
            f.stat().st_size for f in self.cache_dir.glob("*.db")
        ) / (1024 * 1024)

        # 프리페치 상태
        prefetch_status = {}
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prefetch_status")
            for row in cursor.fetchall():
                prefetch_status[row[0]] = {
                    "last_prefetch": row[1],
                    "symbol_count": row[2],
                    "success_count": row[3],
                    "duration_sec": row[4],
                }
            conn.close()
        except Exception:
            pass

        return {
            "cache_size_mb": cache_size_mb,
            "indicator_cache_count": len(self._indicator_cache),
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "hit_rate": self.stats["cache_hits"] / max(1, self.stats["cache_hits"] + self.stats["cache_misses"]) * 100,
            "indicator_cache_hits": self.stats["indicator_cache_hits"],
            "prefetch_count": self.stats["prefetch_count"],
            "prefetch_status": prefetch_status,
            "background_running": self._running,
        }

    def get_top_accessed_symbols(self, limit: int = 20) -> List[Dict]:
        """가장 많이 접근된 심볼"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, access_count, last_access, avg_response_ms
                FROM usage_stats
                ORDER BY access_count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "symbol": r[0],
                    "access_count": r[1],
                    "last_access": r[2],
                    "avg_response_ms": r[3],
                }
                for r in rows
            ]
        except Exception:
            return []


# 싱글톤 인스턴스
_data_layer_manager: Optional[DataLayerManager] = None


def get_data_layer_manager(
    cache_dir: str = "./data/cache",
    cache_policy: CachePolicy = None,
    prefetch_config: PrefetchConfig = None,
) -> DataLayerManager:
    """DataLayerManager 싱글톤 반환"""
    global _data_layer_manager

    if _data_layer_manager is None:
        _data_layer_manager = DataLayerManager(
            cache_dir=cache_dir,
            cache_policy=cache_policy,
            prefetch_config=prefetch_config,
        )

    return _data_layer_manager
