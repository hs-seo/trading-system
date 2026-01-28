#!/usr/bin/env python3
"""
유니버스 종목 채우기 스크립트

각 시장에서 실제 종목 목록을 가져와서 유니버스를 채웁니다.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime


def fetch_us_stocks():
    """미국 주식 종목 가져오기 - 확장 버전"""
    print("\n🇺🇸 미국 주식 종목 수집 중...")
    import pandas as pd

    symbols = {
        "nasdaq100": [],
        "sp500": [],
        "nyse_all": [],
        "nasdaq_all": [],
        "mega_tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "COST", "NFLX"],
        "semiconductor": ["NVDA", "AMD", "INTC", "AVGO", "QCOM", "MU", "AMAT", "LRCX", "KLAC", "MRVL", "TSM", "ASML",
                         "ON", "MCHP", "ADI", "TXN", "NXPI", "SWKS", "QRVO", "MPWR", "CRUS", "SLAB"],
        "ai_leaders": ["NVDA", "MSFT", "GOOGL", "META", "AMD", "PLTR", "SNOW", "CRWD", "MDB", "DDOG", "NOW",
                      "AI", "PATH", "CFLT", "ESTC", "SPLK", "OKTA", "ZS", "NET", "S", "PANW"],
    }

    # S&P 500
    print("  - S&P 500 가져오는 중...")
    try:
        sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(sp500_url)
        sp500_df = tables[0]
        symbols["sp500"] = sp500_df["Symbol"].str.replace(".", "-").tolist()
        print(f"    ✓ S&P 500: {len(symbols['sp500'])}개")
    except Exception as e:
        print(f"    ✗ S&P 500 위키 실패: {e}, 백업 사용")
        symbols["sp500"] = _get_sp500_backup()

    # NASDAQ 100
    print("  - NASDAQ 100 가져오는 중...")
    try:
        nasdaq_url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(nasdaq_url)
        for table in tables:
            if "Ticker" in table.columns:
                symbols["nasdaq100"] = table["Ticker"].tolist()
                break
            elif "Symbol" in table.columns:
                symbols["nasdaq100"] = table["Symbol"].tolist()
                break
        if not symbols["nasdaq100"]:
            raise ValueError("NASDAQ 100 테이블 찾기 실패")
        print(f"    ✓ NASDAQ 100: {len(symbols['nasdaq100'])}개")
    except Exception as e:
        print(f"    ✗ NASDAQ 100 위키 실패: {e}, 백업 사용")
        symbols["nasdaq100"] = _get_nasdaq100_backup()

    # NYSE 전체 종목 (FinanceDataReader 사용)
    print("  - NYSE 전 종목 가져오는 중...")
    try:
        import FinanceDataReader as fdr
        nyse = fdr.StockListing("NYSE")
        symbols["nyse_all"] = nyse["Symbol"].tolist()
        print(f"    ✓ NYSE: {len(symbols['nyse_all'])}개")
    except Exception as e:
        print(f"    ✗ NYSE 실패: {e}")
        symbols["nyse_all"] = []

    # NASDAQ 전체 종목
    print("  - NASDAQ 전 종목 가져오는 중...")
    try:
        import FinanceDataReader as fdr
        nasdaq = fdr.StockListing("NASDAQ")
        symbols["nasdaq_all"] = nasdaq["Symbol"].tolist()
        print(f"    ✓ NASDAQ: {len(symbols['nasdaq_all'])}개")
    except Exception as e:
        print(f"    ✗ NASDAQ 실패: {e}")
        symbols["nasdaq_all"] = []

    # FinanceDataReader 실패 시 대안
    if not symbols["nyse_all"] and not symbols["nasdaq_all"]:
        print("  - 대안: S&P 500 + 추가 대형주로 확장...")
        symbols["nyse_all"], symbols["nasdaq_all"] = _get_us_stocks_alternative()

    return symbols


def _get_sp500_backup():
    """S&P 500 백업 목록 (2024년 기준)"""
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "BRK-B", "UNH",
        "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY",
        "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO", "ACN", "TMO", "ABT",
        "DHR", "NKE", "VZ", "ADBE", "CRM", "INTC", "AMD", "PM", "CMCSA", "TXN",
        "QCOM", "NEE", "UNP", "HON", "LOW", "IBM", "AMGN", "BA", "SPGI", "RTX",
        "GE", "INTU", "CAT", "SBUX", "DE", "BKNG", "ISRG", "MDLZ", "PLD", "GILD",
        "ADP", "AMAT", "ADI", "VRTX", "TJX", "NOW", "MMC", "BLK", "SYK", "ETN",
        "REGN", "LMT", "ZTS", "CVS", "SCHW", "AMT", "DUK", "PGR", "CI", "CB",
        "PANW", "LRCX", "MO", "BSX", "SO", "SNPS", "CDNS", "KLAC", "FI", "CME",
        "AON", "CL", "ICE", "NOC", "EQIX", "MCK", "ITW", "SHW", "ORLY", "MU",
        "GD", "WM", "HUM", "PYPL", "USB", "PNC", "APD", "FCX", "NSC", "EMR",
        "CTAS", "MCO", "MSI", "MAR", "ROP", "COP", "SLB", "TGT", "AZO", "PCAR",
        "PSX", "OXY", "MPC", "VLO", "EOG", "HES", "DVN", "FANG", "HAL", "BKR",
        "GM", "F", "TM", "HMC", "RIVN", "LCID", "NIO", "XPEV", "LI",
        "DIS", "NFLX", "PARA", "WBD", "CMCSA", "T", "VZ", "TMUS", "CHTR",
        "BAC", "WFC", "C", "MS", "GS", "AXP", "COF", "BK", "TFC", "PNC",
        "JCI", "LEN", "DHI", "PHM", "NVR", "TOL", "MTH", "KBH", "MDC",
        "XOM", "CVX", "BP", "SHEL", "TTE", "COP", "EOG", "PXD", "MRO", "APA",
        "LIN", "APD", "SHW", "ECL", "PPG", "DD", "DOW", "LYB", "CE", "EMN",
        "CAT", "DE", "AGCO", "CNHI", "PII", "OSK", "TTC", "PCAR", "CMI", "ETN",
        "UPS", "FDX", "XPO", "CHRW", "EXPD", "JBHT", "LSTR", "ODFL", "SAIA", "KNX",
        "WMT", "COST", "TGT", "DG", "DLTR", "FIVE", "OLLI", "BJ", "PSMT",
        "AMZN", "EBAY", "ETSY", "W", "CHWY", "CVNA", "CARG", "KMX", "AN", "LAD",
        "SPG", "O", "VICI", "WELL", "EQR", "AVB", "MAA", "UDR", "ESS", "CPT",
        "AMT", "CCI", "SBAC", "EQIX", "DLR", "ARE", "BXP", "VNO", "SLG", "CBRE",
        "PLD", "PSA", "EXR", "CUBE", "LSI", "NSA", "COLD", "REXR", "FR", "STAG"
    ]


def _get_nasdaq100_backup():
    """NASDAQ 100 백업 목록 (2024년 기준)"""
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST",
        "NFLX", "AMD", "ADBE", "PEP", "CSCO", "INTC", "CMCSA", "TMUS", "INTU", "QCOM",
        "TXN", "AMGN", "ISRG", "AMAT", "HON", "BKNG", "SBUX", "VRTX", "LRCX", "ADI",
        "GILD", "MDLZ", "ADP", "REGN", "PANW", "KLAC", "SNPS", "CDNS", "PYPL", "MELI",
        "CRWD", "MRVL", "ABNB", "MAR", "CTAS", "ORLY", "MNST", "CSX", "WDAY", "PCAR",
        "KDP", "FTNT", "ROST", "NXPI", "KHC", "DXCM", "PAYX", "AEP", "ODFL", "FAST",
        "EXC", "CPRT", "LULU", "IDXX", "XEL", "CTSH", "CEG", "EA", "VRSK", "MCHP",
        "AZN", "ANSS", "GEHC", "ZS", "ON", "BKR", "TTD", "FANG", "CSGP", "GFS",
        "TEAM", "DDOG", "DASH", "BIIB", "MDB", "WBD", "LCID", "RIVN", "SIRI", "WBA",
        "JD", "PDD", "BIDU", "NTES", "BILI", "TME", "IQ", "VIPS", "ZTO", "BABA"
    ]


def _get_us_stocks_alternative():
    """대안: 주요 미국 주식 목록 (섹터별 대표 종목)"""
    print("    섹터별 대표 종목으로 확장 중...")

    # 섹터별 주요 종목
    tech = [
        "AAPL", "MSFT", "GOOGL", "GOOG", "META", "NVDA", "AMD", "INTC", "AVGO", "QCOM",
        "TXN", "MU", "AMAT", "LRCX", "KLAC", "SNPS", "CDNS", "MRVL", "ON", "NXPI",
        "ADI", "MCHP", "SWKS", "QRVO", "MPWR", "CRUS", "SLAB", "ALGM", "FORM", "POWI",
        "CRM", "ORCL", "SAP", "NOW", "INTU", "ADBE", "WDAY", "TEAM", "SNOW", "PLTR",
        "DDOG", "MDB", "CRWD", "ZS", "OKTA", "NET", "CFLT", "ESTC", "PATH", "AI",
        "UBER", "LYFT", "ABNB", "DASH", "DKNG", "RBLX", "U", "TTWO", "EA", "ATVI"
    ]

    healthcare = [
        "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY",
        "AMGN", "GILD", "VRTX", "REGN", "BIIB", "MRNA", "BNTX", "ZTS", "ISRG", "SYK",
        "MDT", "BDX", "BSX", "EW", "DXCM", "ALGN", "IDXX", "A", "IQV", "CI",
        "CVS", "HUM", "CNC", "MOH", "ANTM", "MCK", "CAH", "ABC", "WBA", "RAD"
    ]

    finance = [
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP", "COF",
        "USB", "PNC", "TFC", "BK", "STT", "NTRS", "KEY", "RF", "CFG", "FITB",
        "V", "MA", "PYPL", "SQ", "FIS", "FISV", "ADP", "PAYX", "GPN", "FLT",
        "BRK-B", "PGR", "ALL", "TRV", "CB", "MET", "PRU", "AFL", "AIG", "MMC"
    ]

    consumer = [
        "AMZN", "TSLA", "HD", "LOW", "WMT", "COST", "TGT", "DG", "DLTR", "ROST",
        "TJX", "NKE", "LULU", "DECK", "CROX", "SBUX", "MCD", "YUM", "CMG", "DPZ",
        "DIS", "NFLX", "CMCSA", "PARA", "WBD", "FOXA", "VIAC", "CHTR", "T", "VZ",
        "PG", "KO", "PEP", "MDLZ", "KHC", "GIS", "K", "CPB", "SJM", "HSY"
    ]

    industrial = [
        "CAT", "DE", "HON", "GE", "MMM", "RTX", "LMT", "NOC", "GD", "BA",
        "UNP", "UPS", "FDX", "CSX", "NSC", "JBHT", "ODFL", "XPO", "CHRW", "EXPD",
        "ETN", "EMR", "ITW", "PH", "ROK", "CMI", "PCAR", "GNRC", "IR", "DOV",
        "WM", "RSG", "WCN", "CLH", "SRCL", "ECOL", "MEG", "ADSW", "CWST", "GFL"
    ]

    energy = [
        "XOM", "CVX", "COP", "EOG", "SLB", "PXD", "MPC", "VLO", "PSX", "OXY",
        "DVN", "FANG", "HES", "HAL", "BKR", "MRO", "APA", "OVV", "CTRA", "EQT",
        "WMB", "KMI", "OKE", "ET", "MPLX", "PAA", "EPD", "ENLC", "TRGP", "LNG"
    ]

    reits = [
        "PLD", "AMT", "CCI", "EQIX", "PSA", "SPG", "O", "VICI", "WELL", "DLR",
        "AVB", "EQR", "MAA", "UDR", "ESS", "CPT", "INVH", "AMH", "SUI", "ELS"
    ]

    materials = [
        "LIN", "APD", "SHW", "ECL", "PPG", "DD", "DOW", "LYB", "CE", "EMN",
        "FCX", "NEM", "GOLD", "AEM", "WPM", "RGLD", "FNV", "KL", "BTG", "HL",
        "NUE", "STLD", "CLF", "X", "CMC", "RS", "ATI", "CRS", "HAYN", "ZEUS"
    ]

    utilities = [
        "NEE", "DUK", "SO", "D", "AEP", "SRE", "XEL", "EXC", "ED", "WEC",
        "ES", "DTE", "PPL", "FE", "CMS", "AES", "NRG", "VST", "OGE", "ALE"
    ]

    # Growth & Small Cap
    growth = [
        "SHOP", "SE", "MELI", "SPOT", "SQ", "COIN", "AFRM", "UPST", "SOFI", "HOOD",
        "ROKU", "PINS", "SNAP", "TWTR", "ZM", "DOCU", "ASAN", "MNDY", "BILL", "PCTY",
        "HUBS", "ZI", "GTLB", "SUMO", "ESTC", "NEWR", "SPLK", "DOMO", "ALTR", "AYX"
    ]

    # China ADRs
    china_adr = [
        "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "NTES", "BILI", "TME",
        "IQ", "VIPS", "ZTO", "YUMC", "TCOM", "EDU", "TAL", "GOTU", "YMM", "VNET"
    ]

    # Combine all
    nyse_list = list(set(finance + industrial + energy + consumer[:20] + materials + utilities + reits))
    nasdaq_list = list(set(tech + healthcare[:20] + growth + consumer[20:] + china_adr))

    print(f"    ✓ NYSE 대표: {len(nyse_list)}개")
    print(f"    ✓ NASDAQ 대표: {len(nasdaq_list)}개")

    return nyse_list, nasdaq_list


def fetch_korean_stocks():
    """한국 주식 종목 가져오기"""
    print("\n🇰🇷 한국 주식 종목 수집 중...")

    symbols = {
        "kospi": [],
        "kosdaq": [],
        "kospi200": [],
    }

    try:
        import FinanceDataReader as fdr

        # 코스피
        print("  - 코스피 전 종목 가져오는 중...")
        kospi = fdr.StockListing("KOSPI")
        symbols["kospi"] = kospi["Code"].tolist()
        print(f"    ✓ 코스피: {len(symbols['kospi'])}개")

        # 코스닥
        print("  - 코스닥 전 종목 가져오는 중...")
        kosdaq = fdr.StockListing("KOSDAQ")
        symbols["kosdaq"] = kosdaq["Code"].tolist()
        print(f"    ✓ 코스닥: {len(symbols['kosdaq'])}개")

        # 코스피 200
        print("  - 코스피 200 가져오는 중...")
        try:
            kospi200 = fdr.StockListing("KOSPI200")
            symbols["kospi200"] = kospi200["Code"].tolist()
        except:
            # 시가총액 상위로 대체
            symbols["kospi200"] = symbols["kospi"][:200]
        print(f"    ✓ 코스피 200: {len(symbols['kospi200'])}개")

    except ImportError:
        print("  ⚠️ FinanceDataReader 없음")
        print("     pip install finance-datareader")

    return symbols


def fetch_crypto():
    """암호화폐 종목 가져오기 - 섹터별 분류 + 거래량 상위 200개"""
    print("\n₿ 암호화폐 종목 수집 중...")

    # 섹터별 코인 매핑 (수동 분류)
    SECTOR_MAPPING = {
        # 메이저 (시총 상위)
        "major": [
            "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "TRX",
            "TON", "SHIB", "DOGE", "MATIC", "LTC", "BCH", "ATOM", "UNI", "XLM", "ETC"
        ],
        # Layer 1 (메인넷)
        "layer1": [
            "ETH", "SOL", "AVAX", "NEAR", "APT", "SUI", "SEI", "INJ", "FTM", "ALGO",
            "HBAR", "ICP", "EGLD", "FLOW", "MINA", "KAVA", "ONE", "ROSE", "CELO", "KDA",
            "ATOM", "DOT", "ADA", "TRX", "XTZ", "EOS", "NEO", "VET", "IOTA", "XLM"
        ],
        # Layer 2 (확장성)
        "layer2": [
            "ARB", "OP", "MATIC", "IMX", "STRK", "MNT", "METIS", "ZK", "MANTA", "BLAST",
            "LRC", "BOBA", "SKL", "CTSI", "OMG", "CELR"
        ],
        # DeFi
        "defi": [
            "UNI", "AAVE", "MKR", "CRV", "COMP", "SUSHI", "YFI", "SNX", "DYDX", "1INCH",
            "BAL", "CAKE", "JOE", "GMX", "PENDLE", "RUNE", "LQTY", "SPELL", "ALPHA", "PERP",
            "RAY", "SRM", "ORCA", "JUP", "PYTH", "DRIFT"
        ],
        # 게이밍/메타버스
        "gaming": [
            "AXS", "SAND", "MANA", "ENJ", "GALA", "IMX", "ILV", "RONIN", "MAGIC", "PRIME",
            "YGG", "ALICE", "TLM", "GODS", "PYR", "UFO", "HERO", "REVV", "SOUL", "DVI",
            "PIXEL", "PORTAL", "BIGTIME", "BEAM", "XAI", "MYRIA", "NAKA", "SUPER", "ATLAS"
        ],
        # AI/데이터
        "ai": [
            "FET", "AGIX", "OCEAN", "RNDR", "TAO", "ARKM", "WLD", "AI", "NMR", "GRT",
            "CTXC", "DBC", "AGI", "PHB", "MDT", "RSS3", "AIOZ", "ORAI", "ALI", "OLAS"
        ],
        # 밈코인
        "meme": [
            "DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "COQ", "MYRO", "SATS",
            "ORDI", "RATS", "BOME", "SLERF", "BRETT", "MEW", "POPCAT", "TURBO", "BABYDOGE"
        ],
        # 인프라/유틸리티
        "infra": [
            "LINK", "FIL", "AR", "THETA", "HNT", "AKT", "STX", "QNT", "GRT", "API3",
            "BAND", "TRB", "DIA", "UMA", "RLC", "NKN", "STORJ", "SC", "ANKR", "GLM"
        ],
        # 결제/스테이블 관련
        "payment": [
            "XRP", "XLM", "ALGO", "HBAR", "XDC", "CELO", "ACH", "AMP", "REQ", "OMG",
            "PAXG", "TUSD", "USDP"
        ],
        # 프라이버시
        "privacy": [
            "XMR", "ZEC", "DASH", "SCRT", "ROSE", "KEEP", "TORN", "NYM", "RAIL"
        ],
        # RWA (실물자산 토큰화)
        "rwa": [
            "ONDO", "POLYX", "MPL", "CFG", "MAPLE", "RIO", "PROPS", "PROPY"
        ],
        # 팬토큰/소셜
        "social": [
            "CHZ", "BAR", "PSG", "JUV", "ACM", "ATM", "ASR", "CITY", "SANTOS", "LAZIO",
            "PORTO", "ALPINE", "GAL", "CYBER", "ID", "HOOK"
        ],
    }

    symbols = {
        "major": [],
        "layer1": [],
        "layer2": [],
        "defi": [],
        "gaming": [],
        "ai": [],
        "meme": [],
        "infra": [],
        "payment": [],
        "privacy": [],
        "rwa": [],
        "social": [],
        "top200_volume": [],  # 거래량 상위 200
    }

    try:
        import ccxt
        print("  - Binance 거래량 데이터 가져오는 중...")

        exchange = ccxt.binance()
        exchange.load_markets()

        # 24시간 거래량 데이터 가져오기
        tickers = exchange.fetch_tickers()

        # USDT 페어만 필터링하고 거래량 기준 정렬
        usdt_tickers = []
        for symbol, ticker in tickers.items():
            if symbol.endswith("/USDT") and ticker.get("quoteVolume"):
                usdt_tickers.append({
                    "symbol": symbol,
                    "volume": ticker.get("quoteVolume", 0),  # USDT 기준 거래량
                    "base": symbol.split("/")[0]
                })

        # 거래량 기준 내림차순 정렬
        usdt_tickers.sort(key=lambda x: x["volume"], reverse=True)

        # 상위 200개
        top200 = usdt_tickers[:200]
        symbols["top200_volume"] = [t["symbol"] for t in top200]
        print(f"    ✓ 거래량 상위 200: {len(symbols['top200_volume'])}개")

        # 거래량 상위 200에서 섹터별 분류
        top200_bases = {t["base"] for t in top200}

        for sector, coins in SECTOR_MAPPING.items():
            sector_symbols = []
            for coin in coins:
                if coin in top200_bases:
                    sector_symbols.append(f"{coin}/USDT")
            symbols[sector] = sector_symbols
            print(f"    ✓ {sector}: {len(sector_symbols)}개")

        # 섹터 미분류 코인 (기타)
        classified = set()
        for sector_coins in SECTOR_MAPPING.values():
            classified.update(sector_coins)

        others = []
        for t in top200:
            if t["base"] not in classified:
                others.append(t["symbol"])
        symbols["others"] = others
        print(f"    ✓ 기타 (미분류): {len(others)}개")

    except ImportError:
        print("  ⚠️ ccxt 없음, 기본 목록 사용")
        # 백업 목록
        symbols["major"] = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
        symbols["layer1"] = ["SOL/USDT", "AVAX/USDT", "NEAR/USDT", "APT/USDT", "SUI/USDT"]
        symbols["layer2"] = ["ARB/USDT", "OP/USDT", "MATIC/USDT", "IMX/USDT"]
        symbols["defi"] = ["UNI/USDT", "AAVE/USDT", "MKR/USDT", "CRV/USDT"]
        symbols["gaming"] = ["AXS/USDT", "SAND/USDT", "MANA/USDT", "GALA/USDT"]
        symbols["ai"] = ["FET/USDT", "AGIX/USDT", "OCEAN/USDT", "RNDR/USDT"]
        symbols["meme"] = ["DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "FLOKI/USDT"]

    except Exception as e:
        print(f"  ⚠️ 에러: {e}")

    return symbols


def fetch_etf():
    """ETF/ETN 종목 가져오기 - 미국 + 한국"""
    print("\n📊 ETF/ETN 종목 수집 중...")

    symbols = {
        # ===== 미국 ETF =====
        # 섹터
        "us_sector": [
            "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLB", "XLRE", "XLU", "XLC",
            "VGT", "VFH", "VDE", "VHT", "VIS", "VDC", "VCR", "VAW", "VNQ", "VOX"
        ],
        # 지수 추종
        "us_index": [
            "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "IVV", "VTV", "VUG", "VXUS",
            "EFA", "EEM", "VWO", "IEMG", "VEA", "SCHF", "IXUS"
        ],
        # 채권
        "us_bond": [
            "TLT", "IEF", "SHY", "BND", "LQD", "HYG", "AGG", "VCIT", "VCSH", "GOVT",
            "TIP", "BNDX", "EMB", "JNK", "MUB", "VTEB"
        ],
        # 원자재
        "us_commodity": [
            "GLD", "SLV", "USO", "UNG", "IAU", "PDBC", "DBC", "GSG", "GLDM", "SIVR",
            "COPX", "CPER", "WEAT", "CORN", "SOYB"
        ],
        # 레버리지 (미국)
        "us_leveraged": [
            # 지수 레버리지/인버스
            "TQQQ", "SQQQ", "QLD", "QID", "PSQ",           # 나스닥
            "SPXL", "SPXS", "UPRO", "SPXU", "SSO", "SDS", "SH",  # S&P 500
            "UDOW", "SDOW", "DDM", "DXD", "DOG",           # 다우
            "TNA", "TZA", "UWM", "TWM", "RWM",             # 러셀 2000
            # 섹터 레버리지
            "SOXL", "SOXS", "USD", "SSG",                  # 반도체
            "TECL", "TECS",                                # 기술
            "LABU", "LABD",                                # 바이오
            "FAS", "FAZ",                                  # 금융
            "ERX", "ERY",                                  # 에너지
            "NUGT", "DUST", "JNUG", "JDST",               # 금광주
            "UVXY", "SVXY", "VXX", "VIXY",                # VIX
            # 채권 레버리지
            "TMF", "TMV", "TBT", "TYD", "TYO"             # 국채
        ],
        # 테마 ETF
        "us_thematic": [
            "ARKK", "ARKG", "ARKF", "ARKW", "ARKQ",        # ARK
            "BOTZ", "ROBO", "IRBO",                        # 로봇/AI
            "HACK", "BUG", "CIBR",                         # 사이버보안
            "SOXX", "SMH", "XSD", "PSI",                   # 반도체
            "XBI", "IBB", "LABU",                          # 바이오
            "TAN", "ICLN", "QCLN", "PBW",                  # 친환경
            "BLOK", "BITO", "GBTC",                        # 블록체인/비트코인
            "KWEB", "MCHI", "FXI", "CQQQ",                 # 중국
            "JETS", "UFO", "MOON"                          # 기타 테마
        ],

        # ===== 한국 ETF =====
        # 레버리지/인버스
        "kr_leveraged": [
            # 코스피 레버리지
            "122630",  # KODEX 레버리지
            "252670",  # KODEX 200선물인버스2X
            "123310",  # TIGER 200선물레버리지
            "252710",  # TIGER 200선물인버스2X
            "278540",  # KODEX 200선물인버스2X(H)
            "253250",  # KBSTAR 200선물레버리지
            "253240",  # KBSTAR 200선물인버스2X
            # 코스닥 레버리지
            "233740",  # KODEX 코스닥150레버리지
            "251340",  # KODEX 코스닥150선물인버스
            "278530",  # TIGER 코스닥150레버리지
            "232080",  # TIGER 코스닥150
            # 섹터 레버리지
            "091180",  # KODEX 자동차
            "091170",  # KODEX 반도체
            "091160",  # KODEX 은행
            "091230",  # TIGER 반도체
            "139290",  # TIGER 2차전지테마
            "305720",  # KODEX 2차전지산업
            "091220",  # TIGER 은행
            "140710",  # KODEX 운송
            "157500",  # TIGER 소프트웨어
            "091240",  # TIGER 2차전지테마
        ],
        # 해외지수 추종 (한국 상장)
        "kr_overseas": [
            # 미국 지수
            "360750",  # TIGER 미국S&P500
            "381170",  # TIGER 미국나스닥100
            "133690",  # TIGER 나스닥100
            "143850",  # TIGER 미국S&P500선물(H)
            "379800",  # KODEX 미국S&P500TR
            "379810",  # KODEX 미국나스닥100TR
            "401400",  # TIGER 미국테크TOP10 INDXX
            "409820",  # KODEX 미국빅테크10(H)
            # 미국 레버리지 (한국상장)
            "225060",  # KINDEX 미국S&P500레버리지(H)
            "225050",  # KINDEX 미국S&P500인버스(H)
            "409810",  # KODEX 미국나스닥100레버리지(H)
            "261220",  # KODEX 미국나스닥바이오
            # 중국
            "192090",  # TIGER 차이나CSI300
            "453810",  # TIGER 차이나항셍테크
            "371450",  # TIGER 차이나전기차SOLACTIVE
            # 일본
            "238720",  # KINDEX 일본Nikkei225(H)
            "241390",  # TIGER 일본TOPIX(H)
            # 기타
            "195930",  # TIGER 유로스탁스50(H)
            "225030",  # TIGER 인도니프티50
        ],
        # 섹터/테마 (한국)
        "kr_sector": [
            # 2차전지/배터리
            "305720",  # KODEX 2차전지산업
            "364970",  # TIGER 2차전지TOP10
            "371460",  # TIGER 2차전지테마
            "394670",  # KODEX 2차전지핵심소재10
            # 반도체
            "091160",  # KODEX 반도체
            "395160",  # KODEX AI반도체핵심장비
            "469150",  # TIGER Fn반도체
            # 바이오
            "244580",  # KODEX 바이오
            "227540",  # TIGER 바이오
            # 자동차/모빌리티
            "091180",  # KODEX 자동차
            "394660",  # TIGER 글로벌자율주행&전기차
            # 인터넷/플랫폼
            "365000",  # TIGER K게임
            "396510",  # TIGER K인터넷
            # 기타 테마
            "371450",  # TIGER 차이나전기차
            "396500",  # TIGER 미국필라델피아반도체
        ],
        # 채권/배당 ETF (한국)
        "kr_bond": [
            "148070",  # KOSEF 국고채10년
            "114820",  # TIGER 국채3년
            "152380",  # KODEX 국채3년
            "273130",  # KODEX 종합채권(AA-이상)
            "439870",  # TIGER 미국채10년선물
            "304660",  # KODEX 미국채10년선물
            # 배당
            "161510",  # ARIRANG 고배당주
            "211560",  # TIGER 배당성장
            "315930",  # KODEX 고배당
            "104530",  # KODEX 배당성장
        ],

        # ===== 한국 ETN =====
        "kr_etn": [
            # 레버리지 ETN
            "530017",  # TRUE 코스피200선물레버리지
            "530019",  # TRUE 코스피200선물인버스2X
            "570017",  # 신한 코스피200선물레버리지
            "550019",  # QV 코스피200선물인버스2X
            # 해외지수 레버리지 ETN
            "530031",  # TRUE 나스닥100선물레버리지
            "530032",  # TRUE 나스닥100선물인버스
            "570031",  # 신한 S&P500선물레버리지
            # 변동성 ETN
            "530016",  # TRUE KOSPI VIX선물
            "550016",  # QV KOSPI VIX선물
            # 원자재 ETN
            "510440",  # KB 레버리지 금선물
            "520030",  # 삼성 인버스 2X WTI원유 선물
            "540030",  # 미래에셋 WTI원유선물
        ],
    }

    # 통계 출력
    us_total = sum(len(v) for k, v in symbols.items() if k.startswith("us_"))
    kr_total = sum(len(v) for k, v in symbols.items() if k.startswith("kr_"))

    print(f"\n  🇺🇸 미국 ETF:")
    print(f"    ✓ 섹터: {len(symbols['us_sector'])}개")
    print(f"    ✓ 지수: {len(symbols['us_index'])}개")
    print(f"    ✓ 레버리지: {len(symbols['us_leveraged'])}개")
    print(f"    ✓ 테마: {len(symbols['us_thematic'])}개")
    print(f"    ✓ 채권: {len(symbols['us_bond'])}개")
    print(f"    ✓ 원자재: {len(symbols['us_commodity'])}개")
    print(f"    소계: {us_total}개")

    print(f"\n  🇰🇷 한국 ETF/ETN:")
    print(f"    ✓ 레버리지: {len(symbols['kr_leveraged'])}개")
    print(f"    ✓ 해외지수: {len(symbols['kr_overseas'])}개")
    print(f"    ✓ 섹터: {len(symbols['kr_sector'])}개")
    print(f"    ✓ 채권/배당: {len(symbols['kr_bond'])}개")
    print(f"    ✓ ETN: {len(symbols['kr_etn'])}개")
    print(f"    소계: {kr_total}개")

    print(f"\n  총 ETF/ETN: {us_total + kr_total}개")

    return symbols


def save_universe_data(data, filepath):
    """유니버스 데이터 저장"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 저장됨: {filepath}")


def main():
    print("=" * 60)
    print("📊 유니버스 종목 수집 시작")
    print("=" * 60)

    all_data = {
        "updated_at": datetime.now().isoformat(),
        "us": {},
        "korea": {},
        "crypto": {},
        "etf": {},
    }

    # 미국 주식
    all_data["us"] = fetch_us_stocks()

    # 한국 주식
    all_data["korea"] = fetch_korean_stocks()

    # 암호화폐
    all_data["crypto"] = fetch_crypto()

    # ETF
    all_data["etf"] = fetch_etf()

    # 저장
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    save_universe_data(all_data, data_dir / "universe_symbols.json")

    # 요약
    print("\n" + "=" * 60)
    print("📋 수집 요약")
    print("=" * 60)

    total = 0
    for market, categories in all_data.items():
        if market == "updated_at":
            continue
        for cat, symbols in categories.items():
            count = len(symbols)
            total += count
            print(f"  {market}/{cat}: {count}개")

    print(f"\n총 {total}개 종목 수집 완료")


if __name__ == "__main__":
    main()
