#!/usr/bin/env python3
"""
FastFetcher 통합 스크리닝 테스트

한국 시장 상위 종목으로 스크리닝 실행
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time


def main():
    print("=" * 60)
    print("FastFetcher 통합 스크리닝 테스트")
    print("=" * 60)

    from screener.runner import ScreenerRunner
    from screener.ideas import IdeaManager
    from screener.universe import UniverseManager

    # 러너 초기화
    runner = ScreenerRunner()

    # 사용 가능한 아이디어 확인
    print("\n📋 사용 가능한 아이디어:")
    for idea in runner.idea_manager.list_all()[:5]:
        print(f"  - {idea.id}: {idea.name}")

    # 사용 가능한 유니버스 확인
    print("\n🌍 사용 가능한 유니버스:")
    for universe in runner.universe_manager.list_all()[:8]:
        print(f"  - {universe.id}: {universe.name} ({universe.symbol_count} symbols)")

    # 진행률 콜백
    def progress(current, total, symbol, status):
        pct = current / total * 100
        print(f"\r  [{pct:5.1f}%] {current}/{total} - {symbol}: {status}    ", end="", flush=True)

    # 테스트 1: 미국 메가테크 스크리닝 (작은 유니버스)
    print("\n\n" + "=" * 60)
    print("테스트 1: 미국 메가테크 (pullback_in_uptrend)")
    print("=" * 60)

    start = time.time()
    result = runner.run(
        idea_id="pullback_in_uptrend",
        universe_id="us_mega_tech",
        workers=5,
        use_cache=True,
        progress_callback=progress,
    )
    elapsed = time.time() - start

    print(f"\n\n  결과:")
    print(f"  - 스크리닝: {result.meta.screened_count}/{result.meta.universe_size}")
    print(f"  - 통과: {result.meta.passed_count}")
    print(f"  - 시간: {elapsed:.2f}초")
    if result.meta.metadata.get("fetch_stats"):
        stats = result.meta.metadata["fetch_stats"]
        print(f"  - 캐시: {stats['cached']}/{stats['total']}")

    if result.candidates:
        print(f"\n  Top 5:")
        for c in result.candidates[:5]:
            print(f"    {c.rank}. {c.symbol.ticker}: {c.final_score:.1f}점")

    # 테스트 2: 한국 시장 상위 100개 스크리닝
    print("\n\n" + "=" * 60)
    print("테스트 2: 한국 시총 상위 100개 (pullback_in_uptrend)")
    print("=" * 60)

    start = time.time()
    try:
        result = runner.run_full_market(
            idea_id="pullback_in_uptrend",
            market="korea",
            top_n=100,
            workers=15,
            progress_callback=progress,
        )
        elapsed = time.time() - start

        print(f"\n\n  결과:")
        print(f"  - 스크리닝: {result.meta.screened_count}/{result.meta.universe_size}")
        print(f"  - 통과: {result.meta.passed_count}")
        print(f"  - 시간: {elapsed:.2f}초")
        print(f"  - 속도: {result.meta.universe_size / elapsed:.1f} 종목/초")
        if result.meta.metadata.get("fetch_stats"):
            stats = result.meta.metadata["fetch_stats"]
            print(f"  - 캐시: {stats['cached']}/{stats['total']}")

        if result.candidates:
            print(f"\n  Top 10:")
            for c in result.candidates[:10]:
                print(f"    {c.rank}. {c.symbol.ticker}: {c.final_score:.1f}점")

    except Exception as e:
        print(f"\n  에러: {e}")
        import traceback
        traceback.print_exc()

    # 캐시 통계
    print("\n\n" + "=" * 60)
    print("캐시 통계")
    print("=" * 60)
    cache_stats = runner.get_cache_stats()
    print(f"  - 총 종목: {cache_stats['total_symbols']}")
    print(f"  - 총 행: {cache_stats['total_rows']:,}")
    print(f"  - 캐시 크기: {cache_stats['cache_size_mb']:.2f} MB")

    print("\n✅ 테스트 완료")


if __name__ == "__main__":
    main()
