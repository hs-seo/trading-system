#!/usr/bin/env python3
"""
Trading System - Main Entry Point

종목 스크리닝 및 분석 시스템 실행
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from core.registry import Registry, list_plugins
from core.pipeline import Pipeline, PipelineBuilder, PipelineContext
from core.interfaces import Symbol, Market, Timeframe
from core.events import get_event_bus, EventType, Event
from config.loader import load_config, Config


def setup_logging(level: str = "INFO"):
    """로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )


def discover_plugins():
    """플러그인 자동 발견"""
    Registry.discover_plugins("data.sources")
    Registry.discover_plugins("data.storage")
    Registry.discover_plugins("analysis.indicators")
    Registry.discover_plugins("analysis.strategies")


def create_pipeline_from_config(config: Config) -> Pipeline:
    """설정에서 파이프라인 생성"""
    from data.sources import YFinanceSource, KRXSource, BinanceSource
    from data.storage import SQLiteStorage, ParquetStorage
    from analysis.indicators import (
        MAIndicator, RSIIndicator, MACDIndicator,
        SMCIndicator, SupplyDemandIndicator
    )
    from analysis.strategies import QuantScreener, SwingScreener

    builder = PipelineBuilder("main")

    # 데이터 소스 설정
    source_config = next((s for s in config.sources if s.enabled), None)
    if source_config:
        if source_config.type == "yfinance":
            builder.with_source(YFinanceSource())
        elif source_config.type == "krx":
            builder.with_source(KRXSource(**source_config.params))
        elif source_config.type == "binance":
            builder.with_source(BinanceSource(**source_config.params))

    # 저장소 설정
    if config.storage.type == "sqlite":
        builder.with_storage(SQLiteStorage(config.storage.path + "/trading.db"))
    elif config.storage.type == "parquet":
        builder.with_storage(ParquetStorage(config.storage.path))

    # 인디케이터 설정
    indicator_map = {
        "ma": MAIndicator,
        "rsi": RSIIndicator,
        "macd": MACDIndicator,
        "smc": SMCIndicator,
        "supply_demand": SupplyDemandIndicator,
    }

    for ind_config in config.indicators:
        if ind_config.enabled and ind_config.type in indicator_map:
            builder.add_indicator(indicator_map[ind_config.type](**ind_config.params))

    # 전략 설정
    strategy_map = {
        "quant_screener": QuantScreener,
        "swing_screener": SwingScreener,
    }

    for strat_config in config.strategies:
        if strat_config.enabled and strat_config.type in strategy_map:
            builder.add_strategy(strategy_map[strat_config.type](**strat_config.params))

    return builder.build()


def run_screening(
    config: Config,
    market: str = "nasdaq",
    symbols: Optional[List[str]] = None,
    days: int = 365,
):
    """스크리닝 실행"""
    logger = logging.getLogger(__name__)

    # 파이프라인 생성
    pipeline = create_pipeline_from_config(config)

    # 유니버스 설정
    market_enum = {
        "kospi": Market.KOSPI,
        "kosdaq": Market.KOSDAQ,
        "nasdaq": Market.NASDAQ,
        "nyse": Market.NYSE,
        "crypto": Market.CRYPTO,
    }.get(market.lower())

    if symbols:
        universe = [Symbol(ticker=s, name=s, market=market_enum) for s in symbols]
    else:
        # 소스에서 종목 목록 가져오기
        source = pipeline.stages[0].source if pipeline.stages else None
        if source:
            universe = source.fetch_symbols(market_enum)[:50]  # 테스트용 50개
        else:
            logger.error("No data source configured")
            return

    logger.info(f"Screening {len(universe)} symbols from {market}")

    # 컨텍스트 생성
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    context = PipelineContext(
        symbols=universe,
        timeframe=Timeframe.D1,
        start_date=start_date,
        end_date=end_date,
    )

    # 파이프라인 실행
    result = pipeline.run(context)

    # 결과 출력
    print("\n" + "=" * 60)
    print("SCREENING RESULTS")
    print("=" * 60)

    if result.analysis_results:
        print(f"\nFound {len(result.analysis_results)} candidates:\n")
        for i, ar in enumerate(result.analysis_results[:20], 1):
            print(f"{i:3}. {ar.symbol.ticker:10} Score: {ar.final_score:.1f}")
            if ar.metadata.get("momentum_data"):
                md = ar.metadata["momentum_data"]
                print(f"      1M: {md.get('return_1m', 0):.1f}% | "
                      f"3M: {md.get('return_3m', 0):.1f}% | "
                      f"6M: {md.get('return_6m', 0):.1f}%")
    else:
        print("\nNo candidates found matching criteria.")

    if result.signals:
        print(f"\n{len(result.signals)} signals generated")

    if result.errors:
        print(f"\n{len(result.errors)} errors occurred")

    print(f"\nExecution time: {result.get_execution_time():.2f}s")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Trading System CLI")

    parser.add_argument(
        "--config", "-c",
        default="config/default.yaml",
        help="Configuration file path"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # screen 명령
    screen_parser = subparsers.add_parser("screen", help="Run stock screening")
    screen_parser.add_argument("--market", "-m", default="nasdaq", help="Market to screen")
    screen_parser.add_argument("--symbols", "-s", nargs="+", help="Specific symbols to screen")
    screen_parser.add_argument("--days", "-d", type=int, default=365, help="Days of historical data")

    # plugins 명령
    plugins_parser = subparsers.add_parser("plugins", help="List available plugins")

    # test 명령
    test_parser = subparsers.add_parser("test", help="Run system test")

    args = parser.parse_args()

    # 설정 로드
    config = load_config(args.config)
    setup_logging(config.log_level)

    logger = logging.getLogger(__name__)
    logger.info(f"Starting {config.app_name}")

    # 플러그인 발견
    try:
        discover_plugins()
    except Exception as e:
        logger.warning(f"Plugin discovery failed: {e}")

    # 명령 실행
    if args.command == "screen":
        run_screening(
            config,
            market=args.market,
            symbols=args.symbols,
            days=args.days,
        )

    elif args.command == "plugins":
        print("\nRegistered Plugins:")
        print("-" * 40)
        for category, plugins in list_plugins().items():
            print(f"\n{category}:")
            for plugin in plugins:
                print(f"  - {plugin}")

    elif args.command == "test":
        print("\nRunning system test...")
        # 간단한 테스트
        from analysis.indicators import RSIIndicator
        import pandas as pd
        import numpy as np

        # 테스트 데이터 생성
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "open": np.random.randn(100).cumsum() + 100,
            "high": np.random.randn(100).cumsum() + 102,
            "low": np.random.randn(100).cumsum() + 98,
            "close": np.random.randn(100).cumsum() + 100,
            "volume": np.random.randint(1000000, 5000000, 100),
        })

        rsi = RSIIndicator()
        result = rsi.calculate(df)
        print(f"RSI calculated: {result['rsi'].iloc[-1]:.2f}")
        print("\nSystem test passed!")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
