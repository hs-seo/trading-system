"""
Universe Manager - 스크리닝 대상 종목 그룹 관리

시장, 섹터, 테마, 워치리스트 등 다양한 유니버스 정의 및 관리
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import json
import logging

from core.interfaces import Symbol, Market

logger = logging.getLogger(__name__)


class UniverseType(Enum):
    """유니버스 타입"""
    MARKET = "market"           # 전체 시장
    INDEX = "index"             # 지수 구성
    SECTOR = "sector"           # 섹터
    THEME = "theme"             # 테마
    WATCHLIST = "watchlist"     # 관심 종목
    CUSTOM = "custom"           # 커스텀


@dataclass
class Universe:
    """종목 유니버스"""
    id: str
    name: str
    type: UniverseType
    description: str = ""

    # 종목
    symbols: List[Symbol] = field(default_factory=list)
    symbol_count: int = 0

    # 필터
    market: Optional[Market] = None
    min_market_cap: float = 0
    max_market_cap: float = float('inf')
    sectors: List[str] = field(default_factory=list)
    exclude_sectors: List[str] = field(default_factory=list)

    # 메타
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source: str = ""  # 데이터 소스

    def add_symbol(self, symbol: Symbol):
        """종목 추가"""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.symbol_count = len(self.symbols)

    def remove_symbol(self, ticker: str):
        """종목 제거"""
        self.symbols = [s for s in self.symbols if s.ticker != ticker]
        self.symbol_count = len(self.symbols)

    def get_tickers(self) -> List[str]:
        """티커 목록"""
        return [s.ticker for s in self.symbols]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "symbol_count": self.symbol_count,
            "market": self.market.value if self.market else None,
        }


# ============================================================================
# 사전 정의된 유니버스
# ============================================================================

BUILT_IN_UNIVERSES: Dict[str, Dict] = {
    # 한국 시장
    "kospi_all": {
        "name": "🇰🇷 코스피 전체",
        "type": UniverseType.MARKET,
        "market": Market.KOSPI,
        "description": "코스피 전 종목",
    },
    "kosdaq_all": {
        "name": "🇰🇷 코스닥 전체",
        "type": UniverseType.MARKET,
        "market": Market.KOSDAQ,
        "description": "코스닥 전 종목",
    },
    "kospi200": {
        "name": "🇰🇷 코스피 200",
        "type": UniverseType.INDEX,
        "market": Market.KOSPI,
        "description": "코스피 200 지수 구성 종목",
    },
    "korea_growth": {
        "name": "🇰🇷 한국 성장주",
        "type": UniverseType.THEME,
        "market": Market.KOSDAQ,
        "description": "코스닥 성장 기업 (바이오, IT, 콘텐츠)",
        "sectors": ["바이오", "IT", "게임", "엔터테인먼트"],
    },

    # 미국 시장 - 전체
    "nyse_all": {
        "name": "🇺🇸 NYSE 전체",
        "type": UniverseType.MARKET,
        "market": Market.NYSE,
        "description": "뉴욕증권거래소 전 종목",
    },
    "nasdaq_all": {
        "name": "🇺🇸 NASDAQ 전체",
        "type": UniverseType.MARKET,
        "market": Market.NASDAQ,
        "description": "나스닥 전 종목",
    },

    # 미국 시장 - 지수
    "nasdaq100": {
        "name": "🇺🇸 나스닥 100",
        "type": UniverseType.INDEX,
        "market": Market.NASDAQ,
        "description": "나스닥 100 지수 구성 종목",
    },
    "sp500": {
        "name": "🇺🇸 S&P 500",
        "type": UniverseType.INDEX,
        "market": Market.NYSE,
        "description": "S&P 500 지수 구성 종목",
    },

    # 미국 시장 - 테마
    "us_mega_tech": {
        "name": "🇺🇸 메가테크",
        "type": UniverseType.THEME,
        "market": Market.NASDAQ,
        "description": "빅테크 기업 (FAANG+)",
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    },
    "us_semiconductor": {
        "name": "🇺🇸 반도체",
        "type": UniverseType.SECTOR,
        "market": Market.NASDAQ,
        "description": "미국 반도체 기업",
        "symbols": ["NVDA", "AMD", "INTC", "AVGO", "QCOM", "MU", "AMAT", "LRCX", "KLAC", "MRVL"],
    },
    "us_ai_leaders": {
        "name": "🤖 AI 리더",
        "type": UniverseType.THEME,
        "market": Market.NASDAQ,
        "description": "AI 관련 핵심 기업",
        "symbols": ["NVDA", "MSFT", "GOOGL", "META", "AMD", "PLTR", "SNOW", "CRWD", "MDB"],
    },

    # 암호화폐 - 전체
    "crypto_top200": {
        "name": "₿ 거래량 상위 200",
        "type": UniverseType.MARKET,
        "market": Market.CRYPTO,
        "description": "바이낸스 USDT 거래량 상위 200개",
    },

    # 암호화폐 - 섹터별
    "crypto_major": {
        "name": "₿ 메이저",
        "type": UniverseType.INDEX,
        "market": Market.CRYPTO,
        "description": "시가총액 상위 (BTC, ETH, BNB 등)",
    },
    "crypto_layer1": {
        "name": "🔗 레이어1",
        "type": UniverseType.THEME,
        "market": Market.CRYPTO,
        "description": "메인넷 블록체인 (SOL, AVAX, NEAR 등)",
    },
    "crypto_layer2": {
        "name": "⚡ 레이어2",
        "type": UniverseType.THEME,
        "market": Market.CRYPTO,
        "description": "확장성 솔루션 (ARB, OP, MATIC 등)",
    },
    "crypto_defi": {
        "name": "🏦 DeFi",
        "type": UniverseType.THEME,
        "market": Market.CRYPTO,
        "description": "탈중앙 금융 (UNI, AAVE, MKR 등)",
    },
    "crypto_gaming": {
        "name": "🎮 게이밍/메타버스",
        "type": UniverseType.THEME,
        "market": Market.CRYPTO,
        "description": "게임/메타버스 (AXS, SAND, MANA 등)",
    },
    "crypto_ai": {
        "name": "🤖 AI/데이터",
        "type": UniverseType.THEME,
        "market": Market.CRYPTO,
        "description": "AI 관련 (FET, RNDR, TAO 등)",
    },
    "crypto_meme": {
        "name": "🐕 밈코인",
        "type": UniverseType.THEME,
        "market": Market.CRYPTO,
        "description": "밈/커뮤니티 (DOGE, SHIB, PEPE 등)",
    },
    "crypto_infra": {
        "name": "🔧 인프라",
        "type": UniverseType.THEME,
        "market": Market.CRYPTO,
        "description": "인프라/유틸리티 (LINK, FIL, AR 등)",
    },

    # ===== ETF - 미국 =====
    "us_sector_etf": {
        "name": "🇺🇸 섹터 ETF",
        "type": UniverseType.SECTOR,
        "market": Market.ETF,
        "description": "미국 섹터별 ETF (XLK, XLF 등)",
    },
    "us_index_etf": {
        "name": "🇺🇸 지수 ETF",
        "type": UniverseType.INDEX,
        "market": Market.ETF,
        "description": "미국 지수 추종 (SPY, QQQ 등)",
    },
    "us_leveraged_etf": {
        "name": "🇺🇸 레버리지",
        "type": UniverseType.THEME,
        "market": Market.ETF,
        "description": "미국 레버리지/인버스 (TQQQ, SOXL 등)",
    },
    "us_thematic_etf": {
        "name": "🇺🇸 테마 ETF",
        "type": UniverseType.THEME,
        "market": Market.ETF,
        "description": "미국 테마 ETF (ARKK, SOXX 등)",
    },
    "us_bond_etf": {
        "name": "🇺🇸 채권 ETF",
        "type": UniverseType.SECTOR,
        "market": Market.ETF,
        "description": "미국 채권 ETF (TLT, BND 등)",
    },
    "us_commodity_etf": {
        "name": "🇺🇸 원자재 ETF",
        "type": UniverseType.SECTOR,
        "market": Market.ETF,
        "description": "원자재 ETF (GLD, SLV, USO 등)",
    },

    # ===== ETF - 한국 =====
    "kr_leveraged_etf": {
        "name": "🇰🇷 레버리지 ETF",
        "type": UniverseType.THEME,
        "market": Market.ETF,
        "description": "한국 레버리지 (KODEX 레버리지, 인버스2X 등)",
    },
    "kr_overseas_etf": {
        "name": "🇰🇷 해외지수 ETF",
        "type": UniverseType.INDEX,
        "market": Market.ETF,
        "description": "한국 상장 해외지수 (TIGER 나스닥100 등)",
    },
    "kr_sector_etf": {
        "name": "🇰🇷 섹터 ETF",
        "type": UniverseType.SECTOR,
        "market": Market.ETF,
        "description": "한국 섹터 (2차전지, 반도체, 바이오 등)",
    },
    "kr_bond_etf": {
        "name": "🇰🇷 채권/배당 ETF",
        "type": UniverseType.SECTOR,
        "market": Market.ETF,
        "description": "한국 채권/배당 ETF",
    },
    "kr_etn": {
        "name": "🇰🇷 ETN",
        "type": UniverseType.THEME,
        "market": Market.ETF,
        "description": "한국 ETN (레버리지, 원자재 등)",
    },
}


class UniverseManager:
    """유니버스 관리자"""

    def __init__(self, symbols_file: str = None):
        self.universes: Dict[str, Universe] = {}
        self.watchlists: Dict[str, Universe] = {}
        self.symbols_data: Dict = {}

        # 심볼 파일 로드
        if symbols_file is None:
            symbols_file = Path(__file__).parent.parent / "data" / "universe_symbols.json"

        self._load_symbols_file(symbols_file)
        self._load_built_in()

    def _load_symbols_file(self, filepath):
        """JSON 심볼 파일 로드"""
        try:
            with open(filepath, "r") as f:
                self.symbols_data = json.load(f)
            logger.info(f"Loaded symbols from {filepath}")
        except FileNotFoundError:
            logger.warning(f"Symbols file not found: {filepath}")
            logger.info("Run: python scripts/populate_universe.py")
        except Exception as e:
            logger.error(f"Failed to load symbols: {e}")

    def _load_built_in(self):
        """기본 유니버스 로드"""
        # 심볼 데이터 매핑
        symbols_mapping = {
            # 미국 시장
            "nyse_all": ("us", "nyse_all"),
            "nasdaq_all": ("us", "nasdaq_all"),
            "nasdaq100": ("us", "nasdaq100"),
            "sp500": ("us", "sp500"),
            "us_mega_tech": ("us", "mega_tech"),
            "us_semiconductor": ("us", "semiconductor"),
            "us_ai_leaders": ("us", "ai_leaders"),
            # 한국 시장
            "kospi_all": ("korea", "kospi"),
            "kosdaq_all": ("korea", "kosdaq"),
            "kospi200": ("korea", "kospi200"),
            # 암호화폐
            "crypto_top200": ("crypto", "top200_volume"),
            "crypto_major": ("crypto", "major"),
            "crypto_layer1": ("crypto", "layer1"),
            "crypto_layer2": ("crypto", "layer2"),
            "crypto_defi": ("crypto", "defi"),
            "crypto_gaming": ("crypto", "gaming"),
            "crypto_ai": ("crypto", "ai"),
            "crypto_meme": ("crypto", "meme"),
            "crypto_infra": ("crypto", "infra"),
            # ETF - 미국
            "us_sector_etf": ("etf", "us_sector"),
            "us_index_etf": ("etf", "us_index"),
            "us_leveraged_etf": ("etf", "us_leveraged"),
            "us_thematic_etf": ("etf", "us_thematic"),
            "us_bond_etf": ("etf", "us_bond"),
            "us_commodity_etf": ("etf", "us_commodity"),
            # ETF - 한국
            "kr_leveraged_etf": ("etf", "kr_leveraged"),
            "kr_overseas_etf": ("etf", "kr_overseas"),
            "kr_sector_etf": ("etf", "kr_sector"),
            "kr_bond_etf": ("etf", "kr_bond"),
            "kr_etn": ("etf", "kr_etn"),
        }

        for uid, config in BUILT_IN_UNIVERSES.items():
            universe = Universe(
                id=uid,
                name=config["name"],
                type=config["type"],
                description=config.get("description", ""),
                market=config.get("market"),
                sectors=config.get("sectors", []),
            )

            # 심볼 데이터에서 종목 가져오기
            if uid in symbols_mapping:
                market_key, category = symbols_mapping[uid]
                symbols_list = self.symbols_data.get(market_key, {}).get(category, [])
                for ticker in symbols_list:
                    universe.add_symbol(Symbol(
                        ticker=ticker,
                        name=ticker,
                        market=config.get("market"),
                    ))

            # 하드코딩된 심볼 (fallback)
            elif "symbols" in config:
                for ticker in config["symbols"]:
                    universe.add_symbol(Symbol(
                        ticker=ticker,
                        name=ticker,
                        market=config.get("market"),
                    ))

            self.universes[uid] = universe

    def get(self, universe_id: str) -> Optional[Universe]:
        """유니버스 조회"""
        return self.universes.get(universe_id) or self.watchlists.get(universe_id)

    def list_all(self) -> List[Universe]:
        """전체 유니버스 목록"""
        return list(self.universes.values()) + list(self.watchlists.values())

    def list_by_market(self, market: Market) -> List[Universe]:
        """시장별 유니버스"""
        return [u for u in self.universes.values() if u.market == market]

    def list_by_type(self, utype: UniverseType) -> List[Universe]:
        """타입별 유니버스"""
        return [u for u in self.universes.values() if u.type == utype]

    def create_watchlist(
        self,
        name: str,
        symbols: List[str],
        description: str = "",
    ) -> Universe:
        """워치리스트 생성"""
        wl_id = f"watchlist_{len(self.watchlists) + 1}"

        universe = Universe(
            id=wl_id,
            name=f"⭐ {name}",
            type=UniverseType.WATCHLIST,
            description=description,
        )

        for ticker in symbols:
            universe.add_symbol(Symbol(ticker=ticker, name=ticker, market=None))

        self.watchlists[wl_id] = universe
        return universe

    def combine(self, universe_ids: List[str], name: str) -> Universe:
        """여러 유니버스 결합"""
        combined = Universe(
            id=f"combined_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            type=UniverseType.CUSTOM,
        )

        seen_tickers: Set[str] = set()

        for uid in universe_ids:
            universe = self.get(uid)
            if universe:
                for symbol in universe.symbols:
                    if symbol.ticker not in seen_tickers:
                        combined.add_symbol(symbol)
                        seen_tickers.add(symbol.ticker)

        return combined

    def filter_universe(
        self,
        universe: Universe,
        min_market_cap: float = 0,
        sectors: Optional[List[str]] = None,
        exclude_sectors: Optional[List[str]] = None,
    ) -> Universe:
        """유니버스 필터링"""
        filtered = Universe(
            id=f"{universe.id}_filtered",
            name=f"{universe.name} (필터)",
            type=universe.type,
            market=universe.market,
        )

        for symbol in universe.symbols:
            # 섹터 필터
            if sectors and symbol.sector not in sectors:
                continue
            if exclude_sectors and symbol.sector in exclude_sectors:
                continue

            filtered.add_symbol(symbol)

        return filtered

    async def load_from_source(
        self,
        universe_id: str,
        source,  # DataSource
    ) -> Universe:
        """데이터 소스에서 유니버스 로드"""
        universe = self.get(universe_id)
        if not universe or not universe.market:
            raise ValueError(f"Unknown universe or no market: {universe_id}")

        symbols = source.fetch_symbols(universe.market)

        universe.symbols = symbols
        universe.symbol_count = len(symbols)
        universe.updated_at = datetime.now()
        universe.source = source.name

        return universe

    def get_summary(self) -> Dict:
        """유니버스 요약"""
        by_market = {}
        for u in self.universes.values():
            market = u.market.value if u.market else "unknown"
            if market not in by_market:
                by_market[market] = []
            by_market[market].append(u.name)

        return {
            "total_universes": len(self.universes),
            "total_watchlists": len(self.watchlists),
            "by_market": by_market,
        }

    def export_to_json(self, filepath: str):
        """JSON 내보내기"""
        data = {
            "universes": [u.to_dict() for u in self.universes.values()],
            "watchlists": [w.to_dict() for w in self.watchlists.values()],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
