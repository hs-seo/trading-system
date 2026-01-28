#!/usr/bin/env python3
"""
Data Layer CLI - 데이터 레이어 관리 도구

사용법:
    python scripts/data_cli.py warmup sp500          # S&P 500 프리페치
    python scripts/data_cli.py warmup --all          # 모든 유니버스 프리페치
    python scripts/data_cli.py status                # 캐시 상태 확인
    python scripts/data_cli.py clean --hours 24      # 24시간 이상 오래된 캐시 정리
    python scripts/data_cli.py daemon start          # 백그라운드 데몬 시작
"""
import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.data_layer import (
    get_data_layer_manager,
    CachePolicy,
    PrefetchConfig,
)


def print_header(text: str):
    """헤더 출력"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_progress(current: int, total: int, symbol: str, status: str):
    """진행률 출력"""
    pct = current / total * 100 if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f"\r  [{bar}] {pct:5.1f}% ({current}/{total}) {symbol[:15]:<15} {status:<10}", end='', flush=True)


def cmd_warmup(args):
    """캐시 워밍업"""
    print_header("캐시 워밍업")

    dlm = get_data_layer_manager()

    universes = args.universes
    if args.all:
        universes = ["sp500", "nasdaq100", "kospi200", "kosdaq150"]

    if not universes:
        print("  유니버스를 지정하세요 (예: sp500, nasdaq100)")
        print("  또는 --all 옵션으로 모든 유니버스 워밍업")
        return

    for universe_id in universes:
        print(f"\n  [{universe_id}] 프리페칭 시작...")
        start = time.time()

        result = dlm.prefetch_universe(
            universe_id=universe_id,
            days=args.days,
            compute_indicators=not args.no_indicators,
            progress_callback=print_progress,
        )

        print()  # 줄바꿈

        if result["success"]:
            duration = time.time() - start
            print(f"  ✓ 완료: {result['fetched']}/{result['total']}개 종목")
            print(f"    - 캐시 히트: {result['cached']}개")
            print(f"    - 실패: {result['failed']}개")
            print(f"    - 지표 계산: {'Yes' if result['indicators_computed'] else 'No'}")
            print(f"    - 소요 시간: {duration:.1f}초")
        else:
            print(f"  ✗ 실패: {result.get('error', 'Unknown error')}")

    print("\n  워밍업 완료!")


def cmd_status(args):
    """캐시 상태 확인"""
    print_header("데이터 레이어 상태")

    dlm = get_data_layer_manager()
    stats = dlm.get_stats()

    print(f"  캐시 크기:       {stats['cache_size_mb']:.1f} MB")
    print(f"  지표 캐시:       {stats['indicator_cache_count']}개")
    print(f"  캐시 히트:       {stats['cache_hits']:,}회")
    print(f"  캐시 미스:       {stats['cache_misses']:,}회")
    print(f"  히트율:          {stats['hit_rate']:.1f}%")
    print(f"  프리페치 횟수:   {stats['prefetch_count']:,}")
    print(f"  백그라운드:      {'실행 중' if stats['background_running'] else '중지됨'}")

    # 프리페치 상태
    prefetch_status = stats.get("prefetch_status", {})
    if prefetch_status:
        print(f"\n  프리페치 상태:")
        for uid, info in prefetch_status.items():
            last = info.get("last_prefetch", "N/A")
            if last != "N/A":
                try:
                    last_dt = datetime.fromisoformat(last)
                    last = last_dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            print(f"    - {uid}: {info.get('success_count', 0)}/{info.get('symbol_count', 0)}개, {info.get('duration_sec', 0):.1f}초, 마지막: {last}")

    # 자주 접근하는 종목
    top_symbols = dlm.get_top_accessed_symbols(10)
    if top_symbols:
        print(f"\n  자주 접근하는 종목 Top 10:")
        for i, s in enumerate(top_symbols, 1):
            print(f"    {i:2}. {s['symbol']:<10} - {s['access_count']}회, {s['avg_response_ms']:.1f}ms")


def cmd_clean(args):
    """캐시 정리"""
    print_header("캐시 정리")

    dlm = get_data_layer_manager()

    if args.all:
        print("  전체 캐시 삭제 중...")
        dlm.fast_fetcher.clear_cache()
        print("  ✓ 완료")
    else:
        print(f"  {args.hours}시간 이상 오래된 캐시 정리 중...")
        dlm.fast_fetcher.clear_cache(older_than_hours=args.hours)
        print("  ✓ 완료")


def cmd_daemon(args):
    """백그라운드 데몬"""
    print_header("백그라운드 데몬")

    dlm = get_data_layer_manager()

    if args.action == "start":
        if dlm._running:
            print("  이미 실행 중입니다.")
            return

        print("  백그라운드 작업 시작...")
        dlm.start_background_tasks()
        print("  ✓ 시작됨 (자동 프리페치 및 캐시 정리)")

        # 대기
        print("\n  Ctrl+C로 종료")
        try:
            while True:
                time.sleep(60)
                stats = dlm.get_stats()
                now = datetime.now().strftime("%H:%M:%S")
                print(f"\r  [{now}] 히트: {stats['cache_hits']}, 미스: {stats['cache_misses']}, 프리페치: {stats['prefetch_count']}    ", end='', flush=True)
        except KeyboardInterrupt:
            print("\n\n  종료 중...")
            dlm.stop_background_tasks()
            print("  ✓ 종료됨")

    elif args.action == "stop":
        dlm.stop_background_tasks()
        print("  ✓ 백그라운드 작업 중지됨")

    elif args.action == "status":
        status = "실행 중" if dlm._running else "중지됨"
        print(f"  상태: {status}")


def cmd_indicators(args):
    """지표 계산"""
    print_header("지표 계산")

    dlm = get_data_layer_manager()

    symbols = args.symbols
    if not symbols:
        print("  종목을 지정하세요 (예: AAPL MSFT NVDA)")
        return

    print(f"  {len(symbols)}개 종목 지표 계산 중...")

    for symbol in symbols:
        print(f"    - {symbol}...", end='', flush=True)
        try:
            df = dlm.get_data(symbol, days=args.days, with_indicators=True)
            if df is not None:
                print(f" ✓ ({len(df)}행, {len(df.columns)}컬럼)")
            else:
                print(" ✗ 데이터 없음")
        except Exception as e:
            print(f" ✗ 오류: {e}")

    print("\n  완료!")


def main():
    parser = argparse.ArgumentParser(
        description="Data Layer CLI - 데이터 레이어 관리 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # warmup
    warmup_parser = subparsers.add_parser("warmup", help="캐시 워밍업")
    warmup_parser.add_argument("universes", nargs="*", help="유니버스 ID (sp500, nasdaq100, kospi200, kosdaq150)")
    warmup_parser.add_argument("--all", action="store_true", help="모든 유니버스 워밍업")
    warmup_parser.add_argument("--days", type=int, default=365, help="데이터 기간 (일)")
    warmup_parser.add_argument("--no-indicators", action="store_true", help="지표 계산 안함")

    # status
    subparsers.add_parser("status", help="캐시 상태 확인")

    # clean
    clean_parser = subparsers.add_parser("clean", help="캐시 정리")
    clean_parser.add_argument("--hours", type=int, default=24, help="시간 기준 (기본: 24)")
    clean_parser.add_argument("--all", action="store_true", help="전체 캐시 삭제")

    # daemon
    daemon_parser = subparsers.add_parser("daemon", help="백그라운드 데몬")
    daemon_parser.add_argument("action", choices=["start", "stop", "status"], help="동작")

    # indicators
    ind_parser = subparsers.add_parser("indicators", help="지표 계산")
    ind_parser.add_argument("symbols", nargs="*", help="종목 (예: AAPL MSFT)")
    ind_parser.add_argument("--days", type=int, default=365, help="데이터 기간")

    args = parser.parse_args()

    if args.command == "warmup":
        cmd_warmup(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "clean":
        cmd_clean(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "indicators":
        cmd_indicators(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
