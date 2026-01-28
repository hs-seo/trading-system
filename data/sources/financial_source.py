"""
Financial Data Source - 재무 데이터 전문 소스

퀀트 분석에 필요한 상세 재무 데이터 제공
- Financial Modeling Prep (FMP) API
- 향후: Koyfin, SimFin 등 확장 가능
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

import pandas as pd

from core.interfaces import FinancialDataSource, Symbol, Market, Timeframe
from core.registry import register

logger = logging.getLogger(__name__)


@register("source", "fmp")
class FMPSource(FinancialDataSource):
    """
    Financial Modeling Prep API 데이터 소스

    포괄적인 재무 데이터 제공:
    - 재무제표 (Income, Balance, Cash Flow)
    - 비율 분석
    - 밸류에이션
    - 애널리스트 추정치
    - 섹터/산업 데이터

    API 키: https://financialmodelingprep.com/developer/docs/

    사용법:
        source = FMPSource(api_key="your_key")
        ratios = source.fetch_ratios("AAPL")
        growth = source.fetch_growth_metrics("AAPL")
    """

    name = "fmp"
    supported_markets = [Market.NASDAQ, Market.NYSE]

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key

        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError("requests not installed. Run: pip install requests")

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """API 요청"""
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["apikey"] = self.api_key

        try:
            response = self.requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"FMP API error: {e}")
            return None

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        endpoint = f"historical-price-full/{symbol}"
        params = {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
        }

        data = self._request(endpoint, params)
        if not data or "historical" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data["historical"])
        df = df.rename(columns={
            "date": "timestamp",
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    def fetch_symbols(self, market: Market) -> List[Symbol]:
        """종목 목록 조회"""
        if market == Market.NASDAQ:
            endpoint = "nasdaq_constituent"
        elif market == Market.NYSE:
            endpoint = "nyse_constituent"
        else:
            return []

        data = self._request(endpoint)
        if not data:
            return []

        return [
            Symbol(
                ticker=item["symbol"],
                name=item.get("name", ""),
                market=market,
                sector=item.get("sector"),
                industry=item.get("subSector"),
            )
            for item in data
        ]

    def fetch_financials(
        self,
        symbol: str,
        period: str = "annual",
    ) -> pd.DataFrame:
        """재무제표 조회"""
        period_param = "quarter" if period == "quarterly" else "annual"

        # 손익계산서
        income = self._request(
            f"income-statement/{symbol}",
            {"period": period_param, "limit": 10}
        ) or []

        # 재무상태표
        balance = self._request(
            f"balance-sheet-statement/{symbol}",
            {"period": period_param, "limit": 10}
        ) or []

        # 현금흐름표
        cashflow = self._request(
            f"cash-flow-statement/{symbol}",
            {"period": period_param, "limit": 10}
        ) or []

        # 병합
        result = []
        for i, bal in zip(income, balance):
            cf = cashflow[len(result)] if len(result) < len(cashflow) else {}
            merged = {**i, **bal, **cf}
            result.append(merged)

        return pd.DataFrame(result)

    def fetch_ratios(self, symbol: str) -> Dict[str, float]:
        """주요 비율 조회"""
        # Key Metrics
        metrics = self._request(f"key-metrics/{symbol}", {"limit": 1})
        # Ratios
        ratios = self._request(f"ratios/{symbol}", {"limit": 1})
        # Profile
        profile = self._request(f"profile/{symbol}")

        result = {}

        if metrics and len(metrics) > 0:
            m = metrics[0]
            result.update({
                "PER": m.get("peRatio"),
                "PBR": m.get("pbRatio"),
                "PSR": m.get("priceToSalesRatio"),
                "EV_EBITDA": m.get("enterpriseValueOverEBITDA"),
                "EV_Revenue": m.get("evToSales"),
                "FCF_Yield": m.get("freeCashFlowYield"),
                "Dividend_Yield": m.get("dividendYield"),
                "Payout_Ratio": m.get("payoutRatio"),
                "Market_Cap": m.get("marketCap"),
                "Enterprise_Value": m.get("enterpriseValue"),
                "Book_Value_Per_Share": m.get("bookValuePerShare"),
                "Tangible_Book_Value": m.get("tangibleBookValuePerShare"),
            })

        if ratios and len(ratios) > 0:
            r = ratios[0]
            result.update({
                "ROE": r.get("returnOnEquity"),
                "ROA": r.get("returnOnAssets"),
                "ROIC": r.get("returnOnCapitalEmployed"),
                "Gross_Margin": r.get("grossProfitMargin"),
                "Operating_Margin": r.get("operatingProfitMargin"),
                "Net_Margin": r.get("netProfitMargin"),
                "Current_Ratio": r.get("currentRatio"),
                "Quick_Ratio": r.get("quickRatio"),
                "Debt_to_Equity": r.get("debtEquityRatio"),
                "Debt_to_Assets": r.get("debtRatio"),
                "Interest_Coverage": r.get("interestCoverage"),
                "Asset_Turnover": r.get("assetTurnover"),
                "Inventory_Turnover": r.get("inventoryTurnover"),
            })

        if profile and len(profile) > 0:
            p = profile[0]
            result.update({
                "Beta": p.get("beta"),
                "52W_High": p.get("range", "").split("-")[-1] if p.get("range") else None,
                "52W_Low": p.get("range", "").split("-")[0] if p.get("range") else None,
                "Avg_Volume": p.get("volAvg"),
            })

        return {k: v for k, v in result.items() if v is not None}

    def fetch_estimates(self, symbol: str) -> Optional[Dict]:
        """애널리스트 추정치"""
        data = self._request(f"analyst-estimates/{symbol}", {"limit": 4})
        if not data:
            return None

        return {
            "estimates": data,
            "consensus": {
                "avg_eps": sum(d.get("estimatedEpsAvg", 0) for d in data) / len(data),
                "avg_revenue": sum(d.get("estimatedRevenueAvg", 0) for d in data) / len(data),
            }
        }

    def fetch_growth_metrics(self, symbol: str) -> Dict[str, float]:
        """성장 지표 조회"""
        data = self._request(f"financial-growth/{symbol}", {"limit": 1})
        if not data or len(data) == 0:
            return {}

        g = data[0]
        return {
            "Revenue_Growth": g.get("revenueGrowth"),
            "Gross_Profit_Growth": g.get("grossProfitGrowth"),
            "EBITDA_Growth": g.get("ebitdagrowth"),
            "Operating_Income_Growth": g.get("operatingIncomeGrowth"),
            "Net_Income_Growth": g.get("netIncomeGrowth"),
            "EPS_Growth": g.get("epsgrowth"),
            "FCF_Growth": g.get("freeCashFlowGrowth"),
            "Dividend_Growth": g.get("dividendsperShareGrowth"),
            "Book_Value_Growth": g.get("bookValueperShareGrowth"),
            "Asset_Growth": g.get("assetGrowth"),
            "Debt_Growth": g.get("debtGrowth"),
        }

    def fetch_dcf(self, symbol: str) -> Optional[Dict]:
        """DCF 밸류에이션"""
        data = self._request(f"discounted-cash-flow/{symbol}")
        if not data or len(data) == 0:
            return None
        return data[0]

    def fetch_rating(self, symbol: str) -> Optional[Dict]:
        """투자 등급"""
        data = self._request(f"rating/{symbol}")
        if not data or len(data) == 0:
            return None
        return data[0]

    def health_check(self) -> bool:
        """연결 상태 확인"""
        data = self._request("profile/AAPL")
        return data is not None and len(data) > 0


# ============================================================================
# Quant Data Aggregator
# ============================================================================

class QuantDataAggregator:
    """
    퀀트 분석용 데이터 통합 수집기

    여러 소스에서 데이터를 모아 표준화된 형식으로 제공

    사용법:
        aggregator = QuantDataAggregator(fmp_source, yfinance_source)
        data = aggregator.get_full_analysis("AAPL")
    """

    def __init__(
        self,
        financial_source: FinancialDataSource,
        price_source: FinancialDataSource,
    ):
        self.financial_source = financial_source
        self.price_source = price_source

    def get_full_analysis(self, symbol: str) -> Dict[str, Any]:
        """종합 분석 데이터"""
        result = {
            "symbol": symbol,
            "timestamp": datetime.now(),
            "ratios": {},
            "growth": {},
            "momentum": {},
            "valuation": {},
        }

        # 비율
        try:
            result["ratios"] = self.financial_source.fetch_ratios(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch ratios: {e}")

        # 성장 (FMP 전용)
        if hasattr(self.financial_source, "fetch_growth_metrics"):
            try:
                result["growth"] = self.financial_source.fetch_growth_metrics(symbol)
            except Exception as e:
                logger.error(f"Failed to fetch growth: {e}")

        # 모멘텀 (가격 기반 계산)
        try:
            result["momentum"] = self._calculate_momentum(symbol)
        except Exception as e:
            logger.error(f"Failed to calculate momentum: {e}")

        return result

    def _calculate_momentum(self, symbol: str) -> Dict[str, float]:
        """모멘텀 지표 계산"""
        end = datetime.now()
        start = datetime(end.year - 1, end.month, end.day)

        df = self.price_source.fetch_ohlcv(symbol, Timeframe.D1, start, end)
        if df.empty:
            return {}

        close = df["close"]
        current = close.iloc[-1]

        return {
            "Return_1W": (current / close.iloc[-5] - 1) * 100 if len(close) >= 5 else None,
            "Return_1M": (current / close.iloc[-21] - 1) * 100 if len(close) >= 21 else None,
            "Return_3M": (current / close.iloc[-63] - 1) * 100 if len(close) >= 63 else None,
            "Return_6M": (current / close.iloc[-126] - 1) * 100 if len(close) >= 126 else None,
            "Return_12M": (current / close.iloc[0] - 1) * 100,
            "Volatility_1M": close.iloc[-21:].pct_change().std() * (252 ** 0.5) * 100 if len(close) >= 21 else None,
            "From_52W_High": (current / close.max() - 1) * 100,
            "From_52W_Low": (current / close.min() - 1) * 100,
        }
