"""
Binance Data Source - 암호화폐 데이터 수집

CCXT 라이브러리를 사용하여 다양한 거래소 지원 가능
"""
from datetime import datetime
from typing import Dict, List, Optional
import logging

import pandas as pd

from core.interfaces import DataSource, Symbol, Market, Timeframe, OHLCV
from core.registry import register

logger = logging.getLogger(__name__)

# Timeframe 매핑
TIMEFRAME_MAP = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1d",
    Timeframe.W1: "1w",
    Timeframe.MN1: "1M",
}


@register("source", "binance")
class BinanceSource(DataSource):
    """
    Binance 암호화폐 데이터 소스 (CCXT 기반)

    다른 거래소도 쉽게 확장 가능 (upbit, bybit 등)

    사용법:
        source = BinanceSource()
        df = source.fetch_ohlcv("BTC/USDT", Timeframe.H4, start, end)
    """

    name = "binance"
    supported_markets = [Market.CRYPTO]

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        """
        Args:
            exchange_id: CCXT 거래소 ID (binance, upbit, bybit 등)
            api_key: API 키 (선택)
            secret: API 시크릿 (선택)
        """
        try:
            import ccxt
            self.ccxt = ccxt
        except ImportError:
            raise ImportError("ccxt not installed. Run: pip install ccxt")

        exchange_class = getattr(self.ccxt, exchange_id, None)
        if not exchange_class:
            raise ValueError(f"Exchange {exchange_id} not supported by CCXT")

        config = {"enableRateLimit": True}
        if api_key and secret:
            config["apiKey"] = api_key
            config["secret"] = secret

        self.exchange = exchange_class(config)
        self.exchange_id = exchange_id

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        try:
            tf = TIMEFRAME_MAP.get(timeframe, "1d")
            since = int(start.timestamp() * 1000)  # milliseconds
            end_ts = int(end.timestamp() * 1000)

            all_ohlcv = []
            current = since

            # 페이지네이션 처리 (한 번에 최대 1000개)
            while current < end_ts:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol,
                    tf,
                    since=current,
                    limit=1000
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # 다음 페이지
                current = ohlcv[-1][0] + 1

                # 끝에 도달하면 중단
                if ohlcv[-1][0] >= end_ts:
                    break

            if not all_ohlcv:
                return pd.DataFrame()

            df = pd.DataFrame(
                all_ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

            # timestamp 변환
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # 범위 필터링
            df = df[(df["timestamp"] >= start) & (df["timestamp"] <= end)]

            return df

        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            return pd.DataFrame()

    def fetch_symbols(self, market: Market) -> List[Symbol]:
        """거래 가능한 심볼 목록"""
        if market != Market.CRYPTO:
            return []

        try:
            self.exchange.load_markets()
            symbols = []

            for symbol_name, market_info in self.exchange.markets.items():
                if market_info.get("active", True):
                    symbols.append(Symbol(
                        ticker=symbol_name,
                        name=symbol_name,
                        market=Market.CRYPTO,
                        meta={
                            "base": market_info.get("base"),
                            "quote": market_info.get("quote"),
                            "type": market_info.get("type"),
                        }
                    ))

            return symbols

        except Exception as e:
            logger.error(f"Failed to fetch symbols: {e}")
            return []

    def fetch_realtime(self, symbol: str) -> Optional[OHLCV]:
        """실시간 가격"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return OHLCV(
                timestamp=datetime.now(),
                open=ticker.get("open", 0),
                high=ticker.get("high", 0),
                low=ticker.get("low", 0),
                close=ticker.get("last", 0),
                volume=ticker.get("baseVolume", 0),
            )
        except Exception as e:
            logger.error(f"Failed to fetch realtime {symbol}: {e}")
            return None

    def fetch_orderbook(self, symbol: str) -> Optional[Dict]:
        """호가창 데이터"""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=20)
            return {
                "bids": orderbook.get("bids", []),
                "asks": orderbook.get("asks", []),
                "timestamp": datetime.now(),
            }
        except Exception as e:
            logger.error(f"Failed to fetch orderbook {symbol}: {e}")
            return None

    def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """최근 체결 내역"""
        try:
            trades = self.exchange.fetch_trades(symbol, limit=limit)
            return [
                {
                    "timestamp": datetime.fromtimestamp(t["timestamp"] / 1000),
                    "price": t["price"],
                    "amount": t["amount"],
                    "side": t["side"],
                }
                for t in trades
            ]
        except Exception as e:
            logger.error(f"Failed to fetch trades {symbol}: {e}")
            return []

    def health_check(self) -> bool:
        """연결 상태 확인"""
        try:
            self.exchange.fetch_ticker("BTC/USDT")
            return True
        except Exception:
            return False


# ============================================================================
# Factory for Multiple Exchanges
# ============================================================================

class CryptoSourceFactory:
    """
    여러 암호화폐 거래소 소스 생성 팩토리

    사용법:
        factory = CryptoSourceFactory()
        binance = factory.create("binance")
        upbit = factory.create("upbit")
    """

    SUPPORTED_EXCHANGES = [
        "binance",
        "upbit",
        "bybit",
        "okx",
        "bitget",
        "bithumb",
    ]

    @classmethod
    def create(
        cls,
        exchange_id: str,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> BinanceSource:
        """거래소 소스 생성"""
        if exchange_id not in cls.SUPPORTED_EXCHANGES:
            logger.warning(
                f"{exchange_id} not in recommended list, "
                f"but attempting to create anyway"
            )

        return BinanceSource(exchange_id, api_key, secret)

    @classmethod
    def list_exchanges(cls) -> List[str]:
        """지원 거래소 목록"""
        return cls.SUPPORTED_EXCHANGES
