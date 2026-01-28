"""
YFinance Data Source - Yahoo Finance 데이터 수집

미국 주식, ETF, 일부 해외 주식 지원
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

# Timeframe 매핑
TIMEFRAME_MAP = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",  # yfinance doesn't support 4h directly
    Timeframe.D1: "1d",
    Timeframe.W1: "1wk",
    Timeframe.MN1: "1mo",
}


@register("source", "yfinance")
class YFinanceSource(FinancialDataSource):
    """
    Yahoo Finance 데이터 소스

    사용법:
        source = YFinanceSource()
        df = source.fetch_ohlcv("AAPL", Timeframe.D1, start, end)
    """

    name = "yfinance"
    supported_markets = [Market.NASDAQ, Market.NYSE, Market.ETF]

    def __init__(self):
        try:
            import yfinance as yf
            self.yf = yf
        except ImportError:
            raise ImportError("yfinance not installed. Run: pip install yfinance")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        try:
            ticker = self.yf.Ticker(symbol)
            interval = TIMEFRAME_MAP.get(timeframe, "1d")

            df = ticker.history(
                start=start,
                end=end,
                interval=interval,
            )

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # 컬럼 표준화
            df = df.reset_index()
            
            # MultiIndex 컬럼 처리 (yfinance 1.0)
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

            # 필요한 컬럼만 유지
            columns = ["timestamp", "open", "high", "low", "close", "volume"]
            df = df[[c for c in columns if c in df.columns]]

            # timestamp 처리
            if df["timestamp"].dtype == "datetime64[ns, America/New_York]":
                df["timestamp"] = df["timestamp"].dt.tz_localize(None)

            return df

        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            return pd.DataFrame()

    def fetch_symbols(self, market: Market) -> List[Symbol]:
        """
        시장의 종목 목록 조회

        Note: yfinance는 종목 목록 API를 제공하지 않음.
              외부 소스(위키피디아, 거래소 등)에서 가져와야 함.
        """
        # 주요 지수 구성종목 반환 (예시)
        if market == Market.NASDAQ:
            # NASDAQ-100 예시
            symbols_list = [
                "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA",
                "AVGO", "COST", "NFLX", "AMD", "ADBE", "PEP", "CSCO"
            ]
        elif market == Market.NYSE:
            symbols_list = [
                "JPM", "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD",
                "BAC", "XOM", "DIS", "VZ", "KO", "MRK"
            ]
        else:
            return []

        return [
            Symbol(ticker=s, name=s, market=market)
            for s in symbols_list
        ]

    def fetch_realtime(self, symbol: str) -> Optional[OHLCV]:
        """실시간 가격"""
        try:
            ticker = self.yf.Ticker(symbol)
            info = ticker.info
            return OHLCV(
                timestamp=datetime.now(),
                open=info.get("regularMarketOpen", 0),
                high=info.get("regularMarketDayHigh", 0),
                low=info.get("regularMarketDayLow", 0),
                close=info.get("regularMarketPrice", 0),
                volume=info.get("regularMarketVolume", 0),
            )
        except Exception as e:
            logger.error(f"Failed to fetch realtime {symbol}: {e}")
            return None

    def fetch_financials(
        self,
        symbol: str,
        period: str = "annual",
    ) -> pd.DataFrame:
        """재무제표 조회"""
        try:
            ticker = self.yf.Ticker(symbol)

            if period == "annual":
                income = ticker.income_stmt
                balance = ticker.balance_sheet
                cashflow = ticker.cashflow
            else:
                income = ticker.quarterly_income_stmt
                balance = ticker.quarterly_balance_sheet
                cashflow = ticker.quarterly_cashflow

            # 데이터 병합
            result = pd.concat([income, balance, cashflow], axis=0)
            return result

        except Exception as e:
            logger.error(f"Failed to fetch financials for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_ratios(self, symbol: str) -> Dict[str, float]:
        """주요 비율 조회"""
        try:
            ticker = self.yf.Ticker(symbol)
            info = ticker.info

            ratios = {
                "PER": info.get("trailingPE"),
                "Forward_PER": info.get("forwardPE"),
                "PBR": info.get("priceToBook"),
                "PSR": info.get("priceToSalesTrailing12Months"),
                "EV_EBITDA": info.get("enterpriseToEbitda"),
                "EV_Revenue": info.get("enterpriseToRevenue"),
                "Profit_Margin": info.get("profitMargins"),
                "Operating_Margin": info.get("operatingMargins"),
                "ROE": info.get("returnOnEquity"),
                "ROA": info.get("returnOnAssets"),
                "Debt_to_Equity": info.get("debtToEquity"),
                "Current_Ratio": info.get("currentRatio"),
                "Quick_Ratio": info.get("quickRatio"),
                "Revenue_Growth": info.get("revenueGrowth"),
                "Earnings_Growth": info.get("earningsGrowth"),
                "Dividend_Yield": info.get("dividendYield"),
                "Payout_Ratio": info.get("payoutRatio"),
                "Beta": info.get("beta"),
                "52W_High": info.get("fiftyTwoWeekHigh"),
                "52W_Low": info.get("fiftyTwoWeekLow"),
                "50D_MA": info.get("fiftyDayAverage"),
                "200D_MA": info.get("twoHundredDayAverage"),
                "Market_Cap": info.get("marketCap"),
                "Enterprise_Value": info.get("enterpriseValue"),
            }

            # None 값 필터링
            return {k: v for k, v in ratios.items() if v is not None}

        except Exception as e:
            logger.error(f"Failed to fetch ratios for {symbol}: {e}")
            return {}

    def health_check(self) -> bool:
        """연결 상태 확인"""
        try:
            ticker = self.yf.Ticker("AAPL")
            _ = ticker.info
            return True
        except Exception:
            return False
