"""
KRX Data Source - 한국 주식 데이터 수집

코스피, 코스닥 지원 (FinanceDataReader 또는 pykrx 활용)
"""
from datetime import datetime
from typing import Dict, List, Optional
import logging

import pandas as pd

from core.interfaces import (
    DataSource, FinancialDataSource,
    Symbol, Market, Timeframe
)
from core.registry import register

logger = logging.getLogger(__name__)


@register("source", "krx")
class KRXSource(FinancialDataSource):
    """
    한국 주식 데이터 소스

    FinanceDataReader 또는 pykrx 라이브러리 활용

    사용법:
        source = KRXSource()
        df = source.fetch_ohlcv("005930", Timeframe.D1, start, end)  # 삼성전자
    """

    name = "krx"
    supported_markets = [Market.KOSPI, Market.KOSDAQ]

    def __init__(self, use_pykrx: bool = False):
        """
        Args:
            use_pykrx: True면 pykrx 사용, False면 FinanceDataReader 사용
        """
        self.use_pykrx = use_pykrx

        if use_pykrx:
            try:
                from pykrx import stock
                self.stock = stock
                self.fdr = None
            except ImportError:
                raise ImportError("pykrx not installed. Run: pip install pykrx")
        else:
            try:
                import FinanceDataReader as fdr
                self.fdr = fdr
                self.stock = None
            except ImportError:
                raise ImportError(
                    "FinanceDataReader not installed. "
                    "Run: pip install finance-datareader"
                )

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        try:
            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")

            if self.use_pykrx:
                df = self._fetch_pykrx(symbol, start_str, end_str)
            else:
                df = self._fetch_fdr(symbol, start_str, end_str)

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # timeframe 처리 (일봉 외)
            if timeframe != Timeframe.D1:
                df = self._resample(df, timeframe)

            return df

        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            return pd.DataFrame()

    def _fetch_fdr(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """FinanceDataReader로 조회"""
        df = self.fdr.DataReader(symbol, start, end)
        df = df.reset_index()
        df = df.rename(columns={
            "Date": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })
        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    def _fetch_pykrx(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """pykrx로 조회"""
        df = self.stock.get_market_ohlcv_by_date(start, end, symbol)
        df = df.reset_index()
        df = df.rename(columns={
            "날짜": "timestamp",
            "시가": "open",
            "고가": "high",
            "저가": "low",
            "종가": "close",
            "거래량": "volume",
        })
        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    def _resample(self, df: pd.DataFrame, timeframe: Timeframe) -> pd.DataFrame:
        """타임프레임 리샘플링"""
        df = df.set_index("timestamp")

        resample_map = {
            Timeframe.W1: "W",
            Timeframe.MN1: "ME",
        }

        rule = resample_map.get(timeframe)
        if not rule:
            return df.reset_index()

        resampled = df.resample(rule).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()

        return resampled.reset_index()

    def fetch_symbols(self, market: Market) -> List[Symbol]:
        """시장 종목 목록 조회"""
        try:
            if self.fdr:
                if market == Market.KOSPI:
                    listing = self.fdr.StockListing("KOSPI")
                elif market == Market.KOSDAQ:
                    listing = self.fdr.StockListing("KOSDAQ")
                else:
                    return []

                return [
                    Symbol(
                        ticker=row["Code"],
                        name=row["Name"],
                        market=market,
                        sector=row.get("Sector"),
                        industry=row.get("Industry"),
                    )
                    for _, row in listing.iterrows()
                ]

            elif self.stock:
                if market == Market.KOSPI:
                    tickers = self.stock.get_market_ticker_list(market="KOSPI")
                elif market == Market.KOSDAQ:
                    tickers = self.stock.get_market_ticker_list(market="KOSDAQ")
                else:
                    return []

                return [
                    Symbol(
                        ticker=t,
                        name=self.stock.get_market_ticker_name(t),
                        market=market,
                    )
                    for t in tickers
                ]

        except Exception as e:
            logger.error(f"Failed to fetch symbols for {market}: {e}")
            return []

    def fetch_financials(
        self,
        symbol: str,
        period: str = "annual",
    ) -> pd.DataFrame:
        """
        재무제표 조회

        Note: FinanceDataReader/pykrx는 재무제표 지원이 제한적
              OpenDartReader 또는 외부 API 사용 권장
        """
        logger.warning(
            "KRX source has limited financial data. "
            "Consider using OpenDartReader for detailed financials."
        )
        return pd.DataFrame()

    def fetch_ratios(self, symbol: str) -> Dict[str, float]:
        """
        주요 비율 조회

        pykrx 사용 시 일부 지표 조회 가능
        """
        if not self.stock:
            return {}

        try:
            # 오늘 기준 fundamental 조회
            today = datetime.now().strftime("%Y%m%d")
            fund = self.stock.get_market_fundamental_by_ticker(today, market="ALL")

            if symbol in fund.index:
                row = fund.loc[symbol]
                return {
                    "PER": row.get("PER"),
                    "PBR": row.get("PBR"),
                    "Dividend_Yield": row.get("DIV"),
                }
        except Exception as e:
            logger.error(f"Failed to fetch ratios for {symbol}: {e}")

        return {}

    def health_check(self) -> bool:
        """연결 상태 확인"""
        try:
            if self.fdr:
                _ = self.fdr.DataReader("005930", "2024-01-01", "2024-01-02")
            elif self.stock:
                _ = self.stock.get_market_ticker_list()
            return True
        except Exception:
            return False


# ============================================================================
# OpenDART 연동 (선택적)
# ============================================================================

class OpenDartSource:
    """
    OpenDART API를 통한 재무제표 조회

    API 키 필요: https://opendart.fss.or.kr
    """

    def __init__(self, api_key: str):
        try:
            import OpenDartReader
            self.dart = OpenDartReader(api_key)
        except ImportError:
            raise ImportError(
                "OpenDartReader not installed. "
                "Run: pip install opendartreader"
            )

    def fetch_financials(self, corp_code: str, year: int) -> Dict:
        """연간 재무제표 조회"""
        try:
            # 사업보고서 기준
            fs = self.dart.finstate(corp_code, year, reprt_code="11011")
            return fs.to_dict() if fs is not None else {}
        except Exception as e:
            logger.error(f"Failed to fetch DART financials: {e}")
            return {}
