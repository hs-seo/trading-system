"""
Fast Data Fetcher - 대량 데이터 고속 수집

병렬 처리 + 캐싱 + 사전 필터링으로 성능 최적화
"""
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import time

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FetchStats:
    """수집 통계"""
    total: int = 0
    success: int = 0
    cached: int = 0
    failed: int = 0
    elapsed_sec: float = 0.0

    @property
    def success_rate(self) -> float:
        return (self.success / self.total * 100) if self.total > 0 else 0


class FastFetcher:
    """
    고속 데이터 수집기

    특징:
    - 병렬 처리 (ThreadPoolExecutor)
    - SQLite 캐싱 (당일 데이터 재사용)
    - 사전 필터링 (시가총액/거래량)
    - 진행률 콜백

    사용법:
        fetcher = FastFetcher(cache_dir="./data/cache")
        data = fetcher.fetch_many(symbols, days=365, workers=10)
    """

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        cache_hours: int = 12,  # 캐시 유효 시간
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_hours = cache_hours
        self.db_path = self.cache_dir / "ohlcv_cache.db"
        self._init_cache_db()

    def _init_cache_db(self):
        """캐시 DB 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_cache (
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    fetched_at TEXT,
                    PRIMARY KEY (symbol, date)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_date
                ON ohlcv_cache(symbol, date)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fetch_log (
                    symbol TEXT PRIMARY KEY,
                    last_fetch TEXT,
                    data_start TEXT,
                    data_end TEXT,
                    row_count INTEGER
                )
            """)

    def _is_cache_valid(self, symbol: str) -> bool:
        """캐시 유효성 확인"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT last_fetch FROM fetch_log WHERE symbol = ?",
                (symbol,)
            ).fetchone()

            if not result:
                return False

            last_fetch = datetime.fromisoformat(result[0])
            return (datetime.now() - last_fetch).total_seconds() < self.cache_hours * 3600

    def _load_from_cache(self, symbol: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """캐시에서 로드"""
        if not self._is_cache_valid(symbol):
            return None

        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                """
                SELECT date as timestamp, open, high, low, close, volume
                FROM ohlcv_cache
                WHERE symbol = ? AND date >= ? AND date <= ?
                ORDER BY date
                """,
                conn,
                params=(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            )

        if df.empty:
            return None

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def _save_to_cache(self, symbol: str, df: pd.DataFrame):
        """캐시에 저장"""
        if df.empty:
            return

        with sqlite3.connect(self.db_path) as conn:
            # 기존 데이터 삭제
            conn.execute("DELETE FROM ohlcv_cache WHERE symbol = ?", (symbol,))

            # 새 데이터 삽입
            for _, row in df.iterrows():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO ohlcv_cache
                    (symbol, date, open, high, low, close, volume, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        row["timestamp"].strftime("%Y-%m-%d") if hasattr(row["timestamp"], "strftime") else str(row["timestamp"])[:10],
                        row["open"],
                        row["high"],
                        row["low"],
                        row["close"],
                        row["volume"],
                        datetime.now().isoformat(),
                    )
                )

            # 로그 업데이트
            conn.execute(
                """
                INSERT OR REPLACE INTO fetch_log
                (symbol, last_fetch, data_start, data_end, row_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    datetime.now().isoformat(),
                    df["timestamp"].min().isoformat() if len(df) > 0 else None,
                    df["timestamp"].max().isoformat() if len(df) > 0 else None,
                    len(df),
                )
            )

    def _is_korean_stock(self, symbol: str) -> bool:
        """한국 주식 여부 판단"""
        if not symbol:
            return False

        # .KS (코스피) 또는 .KQ (코스닥) 접미사
        if symbol.endswith(".KS") or symbol.endswith(".KQ"):
            return True

        # 6자리 숫자 (일반 종목: 005930)
        if len(symbol) == 6 and symbol.isdigit():
            return True

        # 5자리 숫자 + 접미사 (우선주: 00680K, 005935)
        # K = 우선주, L = 2우선주, M = 3우선주
        if len(symbol) == 6 and symbol[:5].isdigit() and symbol[5] in "0123456789KLM":
            return True

        # 신주인수권/워런트 등 (0120G0, 0030R0)
        if len(symbol) == 6 and symbol[:4].isdigit():
            return True

        # ETN, 스팩 등 추가 패턴
        if len(symbol) == 6 and symbol[:3].isdigit():
            return True

        return False

    def _normalize_korean_symbol(self, symbol: str) -> str:
        """한국 주식 심볼 정규화 (fdr용)"""
        # .KS, .KQ 제거 -> 6자리 코드만 추출
        if symbol.endswith(".KS") or symbol.endswith(".KQ"):
            return symbol[:-3]
        return symbol

    def fetch_one(
        self,
        symbol: str,
        days: int = 365,
        source: str = "auto",  # auto, yfinance, fdr
        use_cache: bool = True,
    ) -> Tuple[str, Optional[pd.DataFrame], str]:
        """단일 종목 수집"""
        end = datetime.now()
        start = end - timedelta(days=days)

        # 캐시 확인
        if use_cache:
            cached = self._load_from_cache(symbol, start, end)
            if cached is not None and len(cached) > days * 0.5:  # 50% 이상 있으면 사용
                return symbol, cached, "cached"

        # 소스 자동 선택
        if source == "auto":
            # 크립토: BTCUSDT, BTC/USDT, BTC-USD 등
            if symbol.endswith("/USDT") or symbol.endswith("/USD"):
                source = "ccxt"
            elif symbol.endswith("USDT") and len(symbol) <= 12:  # BTCUSDT, ETHUSDT 형식
                source = "ccxt"
            elif self._is_korean_stock(symbol):
                source = "fdr"  # 한국 주식
            else:
                source = "yfinance"

        try:
            df = self._fetch_from_source(symbol, start, end, source)

            if df is not None and not df.empty:
                self._save_to_cache(symbol, df)
                return symbol, df, "fetched"
            else:
                return symbol, None, "empty"

        except Exception as e:
            logger.debug(f"Failed to fetch {symbol}: {e}")
            return symbol, None, f"error: {str(e)[:50]}"

    def _fetch_from_source(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        source: str,
    ) -> Optional[pd.DataFrame]:
        """소스에서 데이터 가져오기"""
        if source == "yfinance":
            import yfinance as yf
            import logging as _logging
            import sys
            import io

            # yfinance 경고 메시지 숨기기
            _logging.getLogger("yfinance").setLevel(_logging.CRITICAL)

            try:
                # stderr 임시 숨기기 (yfinance가 404 에러를 stderr로 출력함)
                old_stderr = sys.stderr
                sys.stderr = io.StringIO()
                try:
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(start=start, end=end)
                finally:
                    sys.stderr = old_stderr
            except Exception:
                return None

            if df.empty:
                return None

            df = df.reset_index()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            df = df.rename(columns={
                "Date": "timestamp",
                "Datetime": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            })
            return df[["timestamp", "open", "high", "low", "close", "volume"]]

        elif source == "fdr":
            try:
                import FinanceDataReader as fdr
            except ImportError:
                logger.warning("FinanceDataReader not installed, falling back to yfinance")
                return self._fetch_from_source(symbol, start, end, "yfinance")

            try:
                # .KS, .KQ 접미사 제거 (fdr은 6자리 코드 사용)
                fdr_symbol = self._normalize_korean_symbol(symbol)
                df = fdr.DataReader(fdr_symbol, start, end)

                if df is None or df.empty:
                    # fdr 실패 시 yfinance 시도 (005930.KS 형식)
                    logger.debug(f"{symbol}: FDR returned empty, trying yfinance")
                    return self._fetch_from_source(symbol, start, end, "yfinance")

                df = df.reset_index()
                df = df.rename(columns={
                    "Date": "timestamp",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                })

                # 필수 컬럼 확인
                required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
                available_cols = [c for c in required_cols if c in df.columns]
                if len(available_cols) < 5:
                    logger.debug(f"{symbol}: FDR missing columns, trying yfinance")
                    return self._fetch_from_source(symbol, start, end, "yfinance")

                return df[available_cols]
            except Exception as e:
                logger.debug(f"{symbol}: FDR error ({e}), trying yfinance")
                return self._fetch_from_source(symbol, start, end, "yfinance")

        elif source == "ccxt":
            try:
                import ccxt
            except ImportError:
                logger.warning("ccxt not installed, falling back to yfinance")
                # BTC/USDT -> BTC-USD for yfinance
                yf_symbol = symbol.replace("/USDT", "-USD").replace("USDT", "-USD")
                return self._fetch_from_source(yf_symbol, start, end, "yfinance")

            try:
                exchange = ccxt.binance({"enableRateLimit": True})
                since = int(start.timestamp() * 1000)

                # BTCUSDT -> BTC/USDT 형식으로 변환
                ccxt_symbol = symbol
                if symbol.endswith("USDT") and "/" not in symbol:
                    base = symbol[:-4]  # USDT 제거
                    ccxt_symbol = f"{base}/USDT"

                ohlcv = exchange.fetch_ohlcv(ccxt_symbol, "1d", since=since, limit=1000)
                if not ohlcv:
                    return None

                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                return df
            except Exception as e:
                logger.debug(f"{symbol}: ccxt error ({e}), trying yfinance")
                yf_symbol = symbol.replace("/USDT", "-USD").replace("USDT", "-USD")
                return self._fetch_from_source(yf_symbol, start, end, "yfinance")

        return None

    def fetch_many(
        self,
        symbols: List[str],
        days: int = 365,
        workers: int = 10,
        use_cache: bool = True,
        progress_callback=None,  # fn(current, total, symbol, status)
    ) -> Tuple[Dict[str, pd.DataFrame], FetchStats]:
        """
        다중 종목 병렬 수집

        Args:
            symbols: 종목 리스트
            days: 데이터 기간
            workers: 병렬 워커 수
            use_cache: 캐시 사용 여부
            progress_callback: 진행률 콜백

        Returns:
            (데이터 딕셔너리, 통계)
        """
        start_time = time.time()
        results: Dict[str, pd.DataFrame] = {}
        stats = FetchStats(total=len(symbols))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self.fetch_one, sym, days, "auto", use_cache): sym
                for sym in symbols
            }

            for i, future in enumerate(as_completed(futures), 1):
                symbol, df, status = future.result()

                if df is not None:
                    results[symbol] = df
                    stats.success += 1
                    if status == "cached":
                        stats.cached += 1
                else:
                    stats.failed += 1

                if progress_callback:
                    progress_callback(i, len(symbols), symbol, status)

        stats.elapsed_sec = time.time() - start_time
        return results, stats

    def get_cache_stats(self) -> Dict:
        """캐시 통계"""
        with sqlite3.connect(self.db_path) as conn:
            total_symbols = conn.execute(
                "SELECT COUNT(DISTINCT symbol) FROM ohlcv_cache"
            ).fetchone()[0]

            total_rows = conn.execute(
                "SELECT COUNT(*) FROM ohlcv_cache"
            ).fetchone()[0]

            cache_size = self.db_path.stat().st_size / (1024 * 1024)

        return {
            "total_symbols": total_symbols,
            "total_rows": total_rows,
            "cache_size_mb": round(cache_size, 2),
            "cache_hours": self.cache_hours,
        }

    def clear_cache(self, older_than_hours: int = None):
        """캐시 정리"""
        with sqlite3.connect(self.db_path) as conn:
            if older_than_hours:
                cutoff = datetime.now() - timedelta(hours=older_than_hours)
                conn.execute(
                    "DELETE FROM ohlcv_cache WHERE fetched_at < ?",
                    (cutoff.isoformat(),)
                )
            else:
                conn.execute("DELETE FROM ohlcv_cache")
                conn.execute("DELETE FROM fetch_log")
            conn.commit()

        # VACUUM은 트랜잭션 밖에서 실행
        conn = sqlite3.connect(self.db_path)
        conn.execute("VACUUM")
        conn.close()


# ============================================================================
# 사전 필터링
# ============================================================================

class PreFilter:
    """
    사전 필터링 - 스크리닝 전 대상 종목 축소

    시가총액, 거래량 등으로 먼저 걸러서 실제 분석 대상 축소
    """

    @staticmethod
    def filter_by_market_cap(
        symbols: List[str],
        min_cap: float = 0,
        max_cap: float = float('inf'),
        market: str = "korea",
    ) -> List[str]:
        """시가총액 필터"""
        if market == "korea":
            try:
                import FinanceDataReader as fdr

                # 코스피/코스닥 시가총액 조회
                kospi = fdr.StockListing("KOSPI")[["Code", "Marcap"]]
                kosdaq = fdr.StockListing("KOSDAQ")[["Code", "Marcap"]]
                all_stocks = pd.concat([kospi, kosdaq])

                filtered = all_stocks[
                    (all_stocks["Marcap"] >= min_cap) &
                    (all_stocks["Marcap"] <= max_cap)
                ]["Code"].tolist()

                return [s for s in symbols if s in filtered]

            except Exception as e:
                logger.error(f"Market cap filter failed: {e}")
                return symbols

        return symbols

    @staticmethod
    def filter_korea_top_n(n: int = 500, by: str = "Marcap") -> List[str]:
        """한국 주식 상위 N개"""
        try:
            import FinanceDataReader as fdr

            kospi = fdr.StockListing("KOSPI")
            kosdaq = fdr.StockListing("KOSDAQ")
            all_stocks = pd.concat([kospi, kosdaq])

            # 정렬 및 상위 N개
            top_n = all_stocks.nlargest(n, by)["Code"].tolist()
            return top_n

        except Exception as e:
            logger.error(f"Top N filter failed: {e}")
            return []

    @staticmethod
    def filter_us_by_index(index: str = "sp500") -> List[str]:
        """미국 지수 구성종목"""
        # universe_symbols.json에서 로드
        import json
        symbols_file = Path(__file__).parent / "universe_symbols.json"

        try:
            with open(symbols_file) as f:
                data = json.load(f)
            return data.get("us", {}).get(index, [])
        except:
            return []


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI 테스트"""
    import argparse

    parser = argparse.ArgumentParser(description="Fast Data Fetcher")
    parser.add_argument("--symbols", nargs="+", help="Symbols to fetch")
    parser.add_argument("--market", default="us", help="Market (us/korea/crypto)")
    parser.add_argument("--top", type=int, default=100, help="Top N symbols")
    parser.add_argument("--days", type=int, default=365, help="Days of data")
    parser.add_argument("--workers", type=int, default=10, help="Parallel workers")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cache")

    args = parser.parse_args()

    fetcher = FastFetcher()

    if args.clear_cache:
        fetcher.clear_cache()
        print("Cache cleared")
        return

    # 종목 결정
    if args.symbols:
        symbols = args.symbols
    elif args.market == "korea":
        symbols = PreFilter.filter_korea_top_n(args.top)
        print(f"한국 시총 상위 {len(symbols)}개")
    elif args.market == "us":
        symbols = PreFilter.filter_us_by_index("sp500")[:args.top]
        print(f"S&P 500 중 {len(symbols)}개")
    else:
        symbols = []

    if not symbols:
        print("No symbols to fetch")
        return

    # 수집
    def progress(current, total, symbol, status):
        pct = current / total * 100
        print(f"\r[{pct:5.1f}%] {current}/{total} - {symbol}: {status}    ", end="", flush=True)

    print(f"\n수집 시작: {len(symbols)}개 종목, {args.workers} workers")
    data, stats = fetcher.fetch_many(
        symbols,
        days=args.days,
        workers=args.workers,
        use_cache=not args.no_cache,
        progress_callback=progress,
    )

    print(f"\n\n=== 완료 ===")
    print(f"성공: {stats.success}/{stats.total} ({stats.success_rate:.1f}%)")
    print(f"캐시: {stats.cached}개")
    print(f"실패: {stats.failed}개")
    print(f"시간: {stats.elapsed_sec:.1f}초")
    print(f"속도: {stats.total / stats.elapsed_sec:.1f} 종목/초")


if __name__ == "__main__":
    main()
