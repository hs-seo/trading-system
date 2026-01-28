"""
FinanceDataReader Data Source - 미국 주식 데이터 수집

Yahoo Finance 데이터를 FinanceDataReader로 수집
"""
from datetime import datetime
from typing import Dict, List, Optional
import logging

import pandas as pd

from core.interfaces import (
    DataSource, FinancialDataSource,
    Symbol, Market, Timeframe, OHLCV
)
from core.registry import register

logger = logging.getLogger(__name__)

# Timeframe 매핑 (FinanceDataReader는 일봉만 지원, 다른 timeframe은 리샘플링)
TIMEFRAME_MAP = {
    Timeframe.D1: "D",
    Timeframe.W1: "W",
    Timeframe.MN1: "M",
}


@register("source", "fdr")
class FDRSource(FinancialDataSource):
    """
    FinanceDataReader 데이터 소스 (미국 주식)

    Yahoo Finance 데이터를 FinanceDataReader로 수집

    사용법:
        source = FDRSource()
        df = source.fetch_ohlcv("AAPL", Timeframe.D1, start, end)
    """

    name = "fdr"
    supported_markets = [Market.NASDAQ, Market.NYSE, Market.ETF]

    def __init__(self):
        try:
            import FinanceDataReader as fdr
            self.fdr = fdr
        except ImportError:
            raise ImportError("FinanceDataReader not installed. Run: pip install finance-datareader")

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

            df = self.fdr.DataReader(symbol, start_str, end_str)

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # 컬럼 표준화
            df = df.reset_index()
            df = df.rename(columns={
                "Date": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
                "Adj Close": "adj_close",  # 추가
            })

            # 필요한 컬럼만 유지
            columns = ["timestamp", "open", "high", "low", "close", "volume"]
            df = df[[c for c in columns if c in df.columns]]

            # timeframe 처리 (일봉 외)
            if timeframe != Timeframe.D1:
                df = self._resample(df, timeframe)

            return df

        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            return pd.DataFrame()

    def _resample(self, df: pd.DataFrame, timeframe: Timeframe) -> pd.DataFrame:
        """데이터 리샘플링"""
        if timeframe not in TIMEFRAME_MAP:
            logger.warning(f"Unsupported timeframe {timeframe}, using D1")
            return df

        rule = TIMEFRAME_MAP[timeframe]
        df = df.set_index("timestamp")
        df = df.resample(rule).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()
        df = df.reset_index()
        return df

    def fetch_symbols(self, market: Market) -> List[Symbol]:
        """종목 목록 조회 (미구현)"""
        logger.warning("fetch_symbols not implemented for FDRSource")
        return []

    def fetch_financials(self, symbol: str) -> Dict:
        """재무 데이터 조회 (미구현)"""
        logger.warning("fetch_financials not implemented for FDRSource")
        return {}