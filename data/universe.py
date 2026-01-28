"""
Universe Manager - 시장별 종목 리스트 관리

지원 유니버스:
- US: S&P 500, NASDAQ 100, Russell 2000, Dow 30
- Korea: KOSPI 200, KOSDAQ 150
- Crypto: Top 100 by market cap

캐싱 전략:
- 종목 리스트: 1일 캐시
- 로컬 파일 백업으로 API 장애 대응
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

import pandas as pd

logger = logging.getLogger(__name__)


class Market(Enum):
    """시장 구분"""
    US = "us"
    KOREA = "korea"
    CRYPTO = "crypto"


class Universe(Enum):
    """유니버스 종류"""
    # US
    SP500 = "sp500"
    NASDAQ100 = "nasdaq100"
    DOW30 = "dow30"
    RUSSELL2000 = "russell2000"

    # Korea
    KOSPI200 = "kospi200"
    KOSDAQ150 = "kosdaq150"
    KOSPI_ALL = "kospi_all"
    KOSDAQ_ALL = "kosdaq_all"

    # Crypto
    CRYPTO_TOP100 = "crypto_top100"
    CRYPTO_TOP50 = "crypto_top50"


@dataclass
class UniverseInfo:
    """유니버스 정보"""
    name: str
    market: Market
    description: str
    estimated_count: int


UNIVERSE_INFO: Dict[Universe, UniverseInfo] = {
    Universe.SP500: UniverseInfo("S&P 500", Market.US, "미국 대형주 500", 500),
    Universe.NASDAQ100: UniverseInfo("NASDAQ 100", Market.US, "나스닥 상위 100", 100),
    Universe.DOW30: UniverseInfo("Dow Jones 30", Market.US, "다우존스 30", 30),
    Universe.RUSSELL2000: UniverseInfo("Russell 2000", Market.US, "미국 소형주 2000", 2000),
    Universe.KOSPI200: UniverseInfo("KOSPI 200", Market.KOREA, "코스피 대형 200", 200),
    Universe.KOSDAQ150: UniverseInfo("KOSDAQ 150", Market.KOREA, "코스닥 대형 150", 150),
    Universe.KOSPI_ALL: UniverseInfo("KOSPI 전체", Market.KOREA, "코스피 전체", 800),
    Universe.KOSDAQ_ALL: UniverseInfo("KOSDAQ 전체", Market.KOREA, "코스닥 전체", 1500),
    Universe.CRYPTO_TOP100: UniverseInfo("Crypto Top 100", Market.CRYPTO, "시총 상위 100", 100),
    Universe.CRYPTO_TOP50: UniverseInfo("Crypto Top 50", Market.CRYPTO, "시총 상위 50", 50),
}


class UniverseManager:
    """유니버스 관리자"""

    CACHE_DIR = Path("./data/universe_cache")
    CACHE_HOURS = 24  # 종목 리스트 캐시 유효 시간

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Tuple[List[str], datetime]] = {}

    def get_symbols(
        self,
        universe: Universe,
        limit: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[str]:
        """
        유니버스 종목 리스트 가져오기

        Args:
            universe: 유니버스 종류
            limit: 최대 종목 수 (None=전체)
            use_cache: 캐시 사용 여부
        """
        cache_key = universe.value

        # 메모리 캐시 확인
        if use_cache and cache_key in self._cache:
            symbols, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < timedelta(hours=self.CACHE_HOURS):
                return symbols[:limit] if limit else symbols

        # 파일 캐시 확인
        cache_file = self.CACHE_DIR / f"{cache_key}.json"
        if use_cache and cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    cached_at = datetime.fromisoformat(data['cached_at'])
                    if datetime.now() - cached_at < timedelta(hours=self.CACHE_HOURS):
                        symbols = data['symbols']
                        self._cache[cache_key] = (symbols, cached_at)
                        return symbols[:limit] if limit else symbols
            except Exception as e:
                logger.warning(f"Cache read error: {e}")

        # 새로 가져오기
        symbols = self._fetch_symbols(universe)

        if symbols:
            # 캐시 저장
            self._cache[cache_key] = (symbols, datetime.now())
            try:
                with open(cache_file, 'w') as f:
                    json.dump({
                        'universe': cache_key,
                        'cached_at': datetime.now().isoformat(),
                        'count': len(symbols),
                        'symbols': symbols,
                    }, f, indent=2)
            except Exception as e:
                logger.warning(f"Cache write error: {e}")

        return symbols[:limit] if limit else symbols

    def _fetch_symbols(self, universe: Universe) -> List[str]:
        """유니버스별 종목 가져오기"""
        fetchers = {
            Universe.SP500: self._fetch_sp500,
            Universe.NASDAQ100: self._fetch_nasdaq100,
            Universe.DOW30: self._fetch_dow30,
            Universe.RUSSELL2000: self._fetch_russell2000,
            Universe.KOSPI200: self._fetch_kospi200,
            Universe.KOSDAQ150: self._fetch_kosdaq150,
            Universe.KOSPI_ALL: self._fetch_kospi_all,
            Universe.KOSDAQ_ALL: self._fetch_kosdaq_all,
            Universe.CRYPTO_TOP100: lambda: self._fetch_crypto_top(100),
            Universe.CRYPTO_TOP50: lambda: self._fetch_crypto_top(50),
        }

        fetcher = fetchers.get(universe)
        if fetcher:
            try:
                return fetcher()
            except Exception as e:
                logger.error(f"Failed to fetch {universe.value}: {e}")
                return self._get_fallback(universe)

        return []

    def _fetch_sp500(self) -> List[str]:
        """S&P 500 종목 가져오기 (Wikipedia)"""
        try:
            import urllib.request
            from io import StringIO

            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8')

            tables = pd.read_html(StringIO(html))
            df = tables[0]
            symbols = df['Symbol'].tolist()
            # 특수문자 정리 (BRK.B -> BRK-B)
            symbols = [s.replace('.', '-') for s in symbols]
            logger.info(f"Fetched {len(symbols)} S&P 500 symbols")
            return symbols
        except Exception as e:
            logger.warning(f"S&P 500 fetch failed: {e}")
            return self._get_fallback(Universe.SP500)

    def _fetch_nasdaq100(self) -> List[str]:
        """NASDAQ 100 종목 가져오기 (Wikipedia)"""
        try:
            import urllib.request
            from io import StringIO

            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8')

            tables = pd.read_html(StringIO(html))
            # 테이블 구조가 바뀔 수 있어 여러 테이블 확인
            for table in tables:
                if 'Ticker' in table.columns:
                    symbols = table['Ticker'].tolist()
                    logger.info(f"Fetched {len(symbols)} NASDAQ 100 symbols")
                    return symbols
                elif 'Symbol' in table.columns:
                    symbols = table['Symbol'].tolist()
                    logger.info(f"Fetched {len(symbols)} NASDAQ 100 symbols")
                    return symbols

            # 대안: 하드코딩된 리스트
            return self._get_fallback(Universe.NASDAQ100)
        except Exception as e:
            logger.warning(f"NASDAQ 100 fetch failed: {e}")
            return self._get_fallback(Universe.NASDAQ100)

    def _fetch_dow30(self) -> List[str]:
        """Dow Jones 30 종목"""
        try:
            import urllib.request
            from io import StringIO

            url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8')

            tables = pd.read_html(StringIO(html))
            for table in tables:
                if 'Symbol' in table.columns:
                    symbols = table['Symbol'].tolist()
                    if len(symbols) >= 25:  # Dow는 30개
                        logger.info(f"Fetched {len(symbols)} Dow 30 symbols")
                        return symbols
            return self._get_fallback(Universe.DOW30)
        except Exception as e:
            logger.warning(f"Dow 30 fetch failed: {e}")
            return self._get_fallback(Universe.DOW30)

    def _fetch_russell2000(self) -> List[str]:
        """Russell 2000 (주요 종목만 - 전체는 너무 많음)"""
        # Russell 2000 전체는 API로 가져오기 어려움
        # 대신 Russell 2000 ETF의 상위 홀딩스 사용
        logger.info("Russell 2000: Using top holdings (full list requires paid API)")
        return self._get_fallback(Universe.RUSSELL2000)

    def _fetch_kospi200(self) -> List[str]:
        """KOSPI 200 종목 (시총 상위 200)"""
        try:
            import FinanceDataReader as fdr

            # KOSPI 전체 -> 시총 상위 200개
            df = fdr.StockListing('KOSPI')
            if df is not None and not df.empty:
                # 시총 기준 상위 200개 (기본 정렬이 시총순)
                top_200 = df.head(200)
                symbols = [f"{code}.KS" for code in top_200['Code'].tolist()]
                logger.info(f"Fetched {len(symbols)} KOSPI 200 symbols via FDR")
                return symbols
        except ImportError:
            logger.warning("FinanceDataReader not installed")
        except Exception as e:
            logger.warning(f"KOSPI 200 fetch failed: {e}")

        return self._get_fallback(Universe.KOSPI200)

    def _fetch_kosdaq150(self) -> List[str]:
        """KOSDAQ 150 종목 (시총 상위 150)"""
        try:
            import FinanceDataReader as fdr

            # KOSDAQ 전체 -> 시총 상위 150개
            df = fdr.StockListing('KOSDAQ')
            if df is not None and not df.empty:
                top_150 = df.head(150)
                symbols = [f"{code}.KQ" for code in top_150['Code'].tolist()]
                logger.info(f"Fetched {len(symbols)} KOSDAQ 150 symbols via FDR")
                return symbols
        except ImportError:
            logger.warning("FinanceDataReader not installed")
        except Exception as e:
            logger.warning(f"KOSDAQ 150 fetch failed: {e}")

        return self._get_fallback(Universe.KOSDAQ150)

    def _fetch_kospi_all(self) -> List[str]:
        """KOSPI 전체 종목"""
        try:
            import FinanceDataReader as fdr

            df = fdr.StockListing('KOSPI')
            if df is not None and not df.empty:
                symbols = [f"{code}.KS" for code in df['Code'].tolist()]
                logger.info(f"Fetched {len(symbols)} KOSPI symbols via FDR")
                return symbols
        except ImportError:
            logger.warning("FinanceDataReader not installed")
        except Exception as e:
            logger.warning(f"KOSPI fetch failed: {e}")

        return self._get_fallback(Universe.KOSPI_ALL)

    def _fetch_kosdaq_all(self) -> List[str]:
        """KOSDAQ 전체 종목"""
        try:
            import FinanceDataReader as fdr

            df = fdr.StockListing('KOSDAQ')
            if df is not None and not df.empty:
                symbols = [f"{code}.KQ" for code in df['Code'].tolist()]
                logger.info(f"Fetched {len(symbols)} KOSDAQ symbols via FDR")
                return symbols
        except ImportError:
            logger.warning("FinanceDataReader not installed")
        except Exception as e:
            logger.warning(f"KOSDAQ fetch failed: {e}")

        return self._get_fallback(Universe.KOSDAQ_ALL)

    def _fetch_crypto_top(self, limit: int = 100) -> List[str]:
        """시총 상위 크립토 (CoinGecko 무료 API)"""
        try:
            import urllib.request

            # CoinGecko 무료 API (rate limit: 10-30 calls/min)
            url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1"

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())

            # Binance 심볼 형식으로 변환
            symbols = []
            for coin in data:
                symbol = coin['symbol'].upper()
                # 스테이블코인 제외
                if symbol not in ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP']:
                    symbols.append(f"{symbol}USDT")

            logger.info(f"Fetched {len(symbols)} crypto symbols")
            return symbols[:limit]

        except Exception as e:
            logger.warning(f"Crypto fetch failed: {e}")
            return self._get_fallback(Universe.CRYPTO_TOP100 if limit >= 100 else Universe.CRYPTO_TOP50)

    def _get_fallback(self, universe: Universe) -> List[str]:
        """폴백 데이터 (하드코딩)"""
        fallbacks = {
            Universe.SP500: [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
                "V", "XOM", "JPM", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "PEP",
                "KO", "COST", "AVGO", "LLY", "WMT", "MCD", "CSCO", "TMO", "ABT", "ACN",
                "DHR", "NEE", "VZ", "ADBE", "NKE", "CRM", "TXN", "PM", "LIN", "RTX",
                "ORCL", "BMY", "CMCSA", "UPS", "QCOM", "HON", "LOW", "MS", "SCHW", "GS",
                "INTC", "AMD", "CAT", "INTU", "AMGN", "BA", "IBM", "DE", "AXP", "SBUX",
                "SPGI", "MDLZ", "BLK", "ISRG", "GILD", "ADI", "PLD", "REGN", "BKNG", "VRTX",
                "SYK", "ADP", "MMC", "TJX", "ZTS", "CI", "LRCX", "CVS", "CB", "MO",
                "ELV", "NOW", "TMUS", "SO", "DUK", "CL", "FIS", "BSX", "CME", "EOG",
                "PNC", "ICE", "ITW", "APD", "SHW", "EMR", "WM", "GD", "NOC", "HUM",
            ],
            Universe.NASDAQ100: [
                "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST",
                "PEP", "ADBE", "CMCSA", "NFLX", "CSCO", "AMD", "INTC", "QCOM", "TXN", "INTU",
                "AMGN", "HON", "AMAT", "SBUX", "ISRG", "BKNG", "ADI", "GILD", "MDLZ", "VRTX",
                "REGN", "ADP", "LRCX", "PYPL", "MU", "CSX", "PANW", "SNPS", "CDNS", "ORLY",
                "KLAC", "MNST", "MAR", "ASML", "MELI", "KDP", "FTNT", "CHTR", "CTAS", "WDAY",
                "KHC", "AEP", "EXC", "DXCM", "MRVL", "PAYX", "AZN", "ODFL", "XEL", "PCAR",
                "EA", "ROST", "CPRT", "IDXX", "BIIB", "VRSK", "CTSH", "FAST", "DLTR", "WBD",
                "ILMN", "CRWD", "SGEN", "ANSS", "ALGN", "EBAY", "TEAM", "ZS", "DDOG", "LCID",
                "CEG", "ENPH", "ZM", "JD", "PDD", "LULU", "RIVN", "ABNB", "FANG", "GFS",
                "MRNA", "NXPI", "GEHC", "ON", "TTD", "SPLK", "OKTA", "SIRI", "TCOM", "WBA",
            ],
            Universe.DOW30: [
                "AAPL", "MSFT", "UNH", "GS", "HD", "MCD", "CAT", "AMGN", "V", "CRM",
                "BA", "HON", "TRV", "AXP", "JPM", "IBM", "JNJ", "WMT", "PG", "CVX",
                "MRK", "DIS", "NKE", "KO", "CSCO", "VZ", "DOW", "MMM", "INTC", "WBA",
            ],
            Universe.RUSSELL2000: [
                # Russell 2000 상위 100개 (시총 기준)
                "SMCI", "MSTR", "SFM", "CVNA", "CORT", "FTAI", "INSM", "RMBS", "ELF", "TXRH",
                "FN", "PCVX", "POWL", "SPSC", "ONTO", "ANF", "CSWI", "BMI", "KTOS", "UFPT",
                "CRS", "DY", "LNTH", "IESC", "PIPR", "CALM", "CPRX", "CRVL", "ALKS", "AVAV",
                "HLIT", "NNE", "COOP", "RBC", "MATX", "VCYT", "CCS", "TDW", "GKOS", "HLNE",
                "SG", "PTGX", "FSS", "ARCB", "SKY", "AROC", "AMPH", "PDCO", "SKWD", "BRBR",
            ],
            Universe.KOSPI200: [
                # KOSPI 200 상위 종목 (시총 기준)
                "005930.KS", "000660.KS", "373220.KS", "005380.KS", "035420.KS",
                "000270.KS", "068270.KS", "051910.KS", "006400.KS", "035720.KS",
                "207940.KS", "005490.KS", "028260.KS", "105560.KS", "012330.KS",
                "055550.KS", "066570.KS", "003670.KS", "096770.KS", "034730.KS",
                "032830.KS", "003550.KS", "009150.KS", "086790.KS", "011200.KS",
                "017670.KS", "018260.KS", "000810.KS", "010130.KS", "033780.KS",
                "015760.KS", "024110.KS", "090430.KS", "034020.KS", "003490.KS",
                "036570.KS", "009540.KS", "010950.KS", "051900.KS", "016360.KS",
            ],
            Universe.KOSDAQ150: [
                # KOSDAQ 150 상위 종목
                "247540.KQ", "086520.KQ", "035760.KQ", "041510.KQ", "293490.KQ",
                "145020.KQ", "091990.KQ", "328130.KQ", "357780.KQ", "215600.KQ",
                "039030.KQ", "112040.KQ", "263750.KQ", "095340.KQ", "036930.KQ",
                "067160.KQ", "214150.KQ", "196170.KQ", "053800.KQ", "033640.KQ",
                "141080.KQ", "222080.KQ", "054950.KQ", "058470.KQ", "298380.KQ",
                "140410.KQ", "078600.KQ", "084370.KQ", "060280.KQ", "068760.KQ",
            ],
            Universe.KOSPI_ALL: [],  # 너무 많아서 폴백 없음, KOSPI200 사용 권장
            Universe.KOSDAQ_ALL: [],  # 너무 많아서 폴백 없음, KOSDAQ150 사용 권장
            Universe.CRYPTO_TOP100: [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SOLUSDT",
                "TRXUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT", "SHIBUSDT", "AVAXUSDT", "LINKUSDT",
                "ATOMUSDT", "UNIUSDT", "ETCUSDT", "XMRUSDT", "XLMUSDT", "BCHUSDT",
                "APTUSDT", "FILUSDT", "LDOUSDT", "HBARUSDT", "NEARUSDT", "VETUSDT", "QNTUSDT",
                "ALGOUSDT", "ICPUSDT", "GRTUSDT", "FTMUSDT", "AAVEUSDT", "EGLDUSDT", "EOSUSDT",
                "SANDUSDT", "MANAUSDT", "THETAUSDT", "AXSUSDT", "XTZUSDT", "FLOWUSDT",
                "CHZUSDT", "SNXUSDT", "MKRUSDT", "MINAUSDT", "NEOUSDT", "CAKEUSDT", "KAVAUSDT",
                "DASHUSDT", "KLAYUSDT", "COMPUSDT", "ZILUSDT", "ENJUSDT", "1INCHUSDT", "BATUSDT",
                "ZECUSDT", "WAVESUSDT", "STXUSDT", "CRVUSDT", "APEUSDT", "LRCUSDT",
                "GALAUSDT", "GMTUSDT", "WOOUSDT", "RUNEUSDT", "CFXUSDT", "RNDRUSDT", "IMXUSDT",
                "FETUSDT", "AGIXUSDT", "OCEANUSDT", "INJUSDT", "OPUSDT", "ARBUSDT", "SUIUSDT",
                "SEIUSDT", "TIAUSDT", "JUPUSDT", "WLDUSDT", "STRKUSDT", "PYTHUSDT", "PENDLEUSDT",
            ],
            Universe.CRYPTO_TOP50: [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SOLUSDT",
                "TRXUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT", "SHIBUSDT", "AVAXUSDT", "LINKUSDT",
                "ATOMUSDT", "UNIUSDT", "ETCUSDT", "XMRUSDT", "XLMUSDT", "BCHUSDT",
                "APTUSDT", "FILUSDT", "LDOUSDT", "HBARUSDT", "NEARUSDT", "VETUSDT", "QNTUSDT",
                "ALGOUSDT", "ICPUSDT", "GRTUSDT", "FTMUSDT", "AAVEUSDT", "EGLDUSDT", "EOSUSDT",
                "SANDUSDT", "MANAUSDT", "THETAUSDT", "AXSUSDT", "XTZUSDT", "FLOWUSDT",
                "CHZUSDT", "SNXUSDT", "MKRUSDT", "OPUSDT", "ARBUSDT", "INJUSDT", "SUIUSDT",
                "RNDRUSDT", "FETUSDT", "IMXUSDT",
            ],
        }

        return fallbacks.get(universe, [])

    def get_all_universes(self) -> Dict[Universe, UniverseInfo]:
        """모든 유니버스 정보"""
        return UNIVERSE_INFO

    def get_universes_by_market(self, market: Market) -> List[Universe]:
        """시장별 유니버스 목록"""
        return [u for u, info in UNIVERSE_INFO.items() if info.market == market]

    def get_combined_symbols(
        self,
        universes: List[Universe],
        limit_per_universe: Optional[int] = None,
    ) -> List[str]:
        """여러 유니버스 종목 합치기 (중복 제거)"""
        all_symbols = []
        seen = set()

        for universe in universes:
            symbols = self.get_symbols(universe, limit=limit_per_universe)
            for s in symbols:
                if s not in seen:
                    all_symbols.append(s)
                    seen.add(s)

        return all_symbols

    def clear_cache(self, universe: Optional[Universe] = None):
        """캐시 삭제"""
        if universe:
            cache_file = self.CACHE_DIR / f"{universe.value}.json"
            if cache_file.exists():
                cache_file.unlink()
            if universe.value in self._cache:
                del self._cache[universe.value]
        else:
            # 전체 삭제
            for f in self.CACHE_DIR.glob("*.json"):
                f.unlink()
            self._cache.clear()

        logger.info(f"Cache cleared: {universe.value if universe else 'all'}")


# 싱글톤 인스턴스
_universe_manager: Optional[UniverseManager] = None


def get_universe_manager() -> UniverseManager:
    """유니버스 매니저 싱글톤 가져오기"""
    global _universe_manager
    if _universe_manager is None:
        _universe_manager = UniverseManager()
    return _universe_manager


# 편의 함수
def get_symbols(universe: Universe, limit: Optional[int] = None) -> List[str]:
    """유니버스 종목 가져오기"""
    return get_universe_manager().get_symbols(universe, limit)


def get_sp500() -> List[str]:
    """S&P 500 종목"""
    return get_symbols(Universe.SP500)


def get_nasdaq100() -> List[str]:
    """NASDAQ 100 종목"""
    return get_symbols(Universe.NASDAQ100)


def get_kospi200() -> List[str]:
    """KOSPI 200 종목"""
    return get_symbols(Universe.KOSPI200)


def get_crypto_top100() -> List[str]:
    """Crypto Top 100"""
    return get_symbols(Universe.CRYPTO_TOP100)


# 종목명 조회 캐시
_stock_names_cache: Dict[str, str] = {}
_stock_names_loaded: bool = False


def _load_stock_names():
    """한국 종목명 로드 (캐시)"""
    global _stock_names_cache, _stock_names_loaded

    if _stock_names_loaded:
        return

    try:
        import FinanceDataReader as fdr

        # KOSPI
        kospi = fdr.StockListing('KOSPI')
        if kospi is not None and not kospi.empty:
            for _, row in kospi.iterrows():
                code = row['Code']
                name = row['Name']
                _stock_names_cache[code] = name
                _stock_names_cache[f"{code}.KS"] = name

        # KOSDAQ
        kosdaq = fdr.StockListing('KOSDAQ')
        if kosdaq is not None and not kosdaq.empty:
            for _, row in kosdaq.iterrows():
                code = row['Code']
                name = row['Name']
                _stock_names_cache[code] = name
                _stock_names_cache[f"{code}.KQ"] = name

        _stock_names_loaded = True
        logger.info(f"Loaded {len(_stock_names_cache)} stock names")

    except Exception as e:
        logger.warning(f"Failed to load stock names: {e}")


def get_stock_name(symbol: str) -> str:
    """
    종목 코드로 종목명 조회

    Args:
        symbol: 종목 코드 (예: 005930.KS, 005930, AAPL)

    Returns:
        종목명 (없으면 원래 심볼 반환)
    """
    global _stock_names_cache, _stock_names_loaded

    # 한국 종목이 아니면 그대로 반환
    if not (symbol.endswith('.KS') or symbol.endswith('.KQ') or
            (len(symbol) == 6 and symbol.isdigit())):
        return symbol

    # 캐시 로드
    if not _stock_names_loaded:
        _load_stock_names()

    return _stock_names_cache.get(symbol, symbol)


def get_symbol_with_name(symbol: str) -> str:
    """
    종목 코드 + 종목명 반환

    Args:
        symbol: 종목 코드

    Returns:
        "종목명 (코드)" 또는 원래 심볼
    """
    name = get_stock_name(symbol)
    if name != symbol:
        # 한국 종목: 이름 (코드)
        code = symbol.replace('.KS', '').replace('.KQ', '')
        return f"{name} ({code})"
    return symbol


# CLI 테스트
if __name__ == "__main__":
    import sys

    manager = UniverseManager()

    if len(sys.argv) > 1:
        universe_name = sys.argv[1].upper()
        try:
            universe = Universe[universe_name]
            symbols = manager.get_symbols(universe)
            print(f"\n{universe.value}: {len(symbols)} symbols")
            print(symbols[:20])
        except KeyError:
            print(f"Unknown universe: {universe_name}")
            print(f"Available: {[u.value for u in Universe]}")
    else:
        print("Available universes:")
        for universe, info in UNIVERSE_INFO.items():
            symbols = manager.get_symbols(universe)
            print(f"  {universe.value:15} - {info.description:20} ({len(symbols)} symbols)")
