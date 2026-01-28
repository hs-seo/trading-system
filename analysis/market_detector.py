"""
Market Condition Detector - 시장 상황 자동 감지

주요 지수의 기술적 지표를 분석하여 현재 시장 상황을 판단합니다.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """시장 국면"""
    BULL = "bull"                # 강세장
    BEAR = "bear"                # 약세장
    SIDEWAYS = "sideways"        # 횡보장
    VOLATILE = "volatile"        # 고변동성
    RECOVERY = "recovery"        # 회복기
    CORRECTION = "correction"    # 조정기


@dataclass
class IndexAnalysis:
    """개별 지수 분석 결과"""
    symbol: str
    name: str
    current_price: float
    change_1d: float       # 1일 변화율
    change_1w: float       # 1주 변화율
    change_1m: float       # 1개월 변화율
    change_3m: float       # 3개월 변화율

    # 이동평균 관계
    above_ma20: bool
    above_ma50: bool
    above_ma200: bool
    ma20_above_ma50: bool
    ma50_above_ma200: bool

    # 기술적 지표
    rsi_14: float

    # 52주 대비
    from_52w_high: float   # 52주 고점 대비 (%)
    from_52w_low: float    # 52주 저점 대비 (%)

    # 판단
    trend: str             # uptrend, downtrend, sideways
    strength: str          # strong, moderate, weak


@dataclass
class MarketConditionResult:
    """시장 상황 분석 결과"""
    condition: MarketRegime
    confidence: float           # 신뢰도 (0-100)
    timestamp: datetime

    # 근거
    index_analyses: List[IndexAnalysis] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # 상세 점수
    bull_score: float = 0.0
    bear_score: float = 0.0
    sideways_score: float = 0.0
    volatile_score: float = 0.0

    # VIX (변동성 지수)
    vix_level: Optional[float] = None
    vix_status: str = ""        # low, normal, elevated, high, extreme

    # 요약
    summary: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict:
        return {
            "condition": self.condition.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "signals": self.signals,
            "warnings": self.warnings,
            "vix_level": self.vix_level,
            "vix_status": self.vix_status,
            "summary": self.summary,
            "recommendation": self.recommendation,
            "scores": {
                "bull": self.bull_score,
                "bear": self.bear_score,
                "sideways": self.sideways_score,
                "volatile": self.volatile_score,
            }
        }


class MarketConditionDetector:
    """시장 상황 감지기"""

    # 분석할 주요 지수
    INDICES = {
        "us": [
            ("SPY", "S&P 500 ETF"),
            ("QQQ", "NASDAQ 100 ETF"),
            ("IWM", "Russell 2000 ETF"),
            ("DIA", "Dow Jones ETF"),
        ],
        "korea": [
            ("^KS11", "KOSPI"),
            ("^KQ11", "KOSDAQ"),
            ("069500.KS", "KODEX 200"),
            ("229200.KS", "KODEX 코스닥150"),
        ],
        "crypto": [
            ("BTC-USD", "Bitcoin"),
            ("ETH-USD", "Ethereum"),
            ("SOL-USD", "Solana"),
            ("BNB-USD", "BNB"),
        ],
        "volatility": [
            ("^VIX", "VIX"),
        ],
    }

    # 크립토 Fear & Greed 레벨
    CRYPTO_FEAR_GREED = {
        "extreme_fear": (0, 25),
        "fear": (25, 45),
        "neutral": (45, 55),
        "greed": (55, 75),
        "extreme_greed": (75, 100),
    }

    # VIX 레벨 기준
    VIX_LEVELS = {
        "low": (0, 12),
        "normal": (12, 20),
        "elevated": (20, 25),
        "high": (25, 35),
        "extreme": (35, 100),
    }

    # 파일 캐시 경로
    CACHE_DIR = "./data/cache/market"

    # 폴백 시장 데이터 (API 실패 시 사용)
    FALLBACK_MARKET_DATA = {
        "us": {
            "condition": "sideways",
            "confidence": 50,
            "summary": "시장 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.",
            "recommendation": "API 제한으로 실시간 데이터 조회가 불가합니다.",
        },
        "korea": {
            "condition": "sideways",
            "confidence": 50,
            "summary": "한국 시장 데이터를 가져올 수 없습니다.",
            "recommendation": "잠시 후 다시 시도해주세요.",
        },
        "crypto": {
            "condition": "sideways",
            "confidence": 50,
            "summary": "크립토 시장 데이터를 가져올 수 없습니다.",
            "recommendation": "잠시 후 다시 시도해주세요.",
        },
    }

    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(minutes=60)  # 캐시 1시간으로 증가
        self.failure_cache_duration = timedelta(minutes=10)  # 실패 시 10분간 재시도 안함
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """캐시 디렉토리 생성"""
        import os
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def _get_file_cache(self, cache_key: str) -> Optional[MarketConditionResult]:
        """파일 캐시에서 로드"""
        import json
        import os

        cache_file = f"{self.CACHE_DIR}/{cache_key}.json"
        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)

            cached_at = datetime.fromisoformat(data['cached_at'])
            is_failure = data.get('is_failure', False)

            # 실패 캐시는 짧은 TTL, 성공 캐시는 긴 TTL
            cache_ttl = self.failure_cache_duration if is_failure else self.cache_duration
            if datetime.now() - cached_at > cache_ttl:
                return None

            # 간단한 결과 반환 (캐시된 요약 정보)
            return MarketConditionResult(
                condition=MarketRegime(data['condition']),
                confidence=data['confidence'],
                timestamp=cached_at,
                signals=data.get('signals', []),
                warnings=data.get('warnings', []),
                bull_score=data.get('bull_score', 0),
                bear_score=data.get('bear_score', 0),
                sideways_score=data.get('sideways_score', 0),
                volatile_score=data.get('volatile_score', 0),
                vix_level=data.get('vix_level'),
                vix_status=data.get('vix_status', ''),
                summary=data.get('summary', ''),
                recommendation=data.get('recommendation', ''),
            )
        except Exception as e:
            logger.debug(f"File cache read error: {e}")
            return None

    def _save_file_cache(self, cache_key: str, result: MarketConditionResult, is_failure: bool = False):
        """파일 캐시에 저장"""
        import json

        cache_file = f"{self.CACHE_DIR}/{cache_key}.json"
        try:
            data = {
                'cached_at': datetime.now().isoformat(),
                'is_failure': is_failure,
                'condition': result.condition.value,
                'confidence': result.confidence,
                'signals': result.signals,
                'warnings': result.warnings,
                'bull_score': result.bull_score,
                'bear_score': result.bear_score,
                'sideways_score': result.sideways_score,
                'volatile_score': result.volatile_score,
                'vix_level': result.vix_level,
                'vix_status': result.vix_status,
                'summary': result.summary,
                'recommendation': result.recommendation,
            }
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.debug(f"File cache write error: {e}")

    def detect(self, market: str = "us") -> MarketConditionResult:
        """
        시장 상황 감지

        Args:
            market: "us", "korea", "crypto", "all"

        Returns:
            MarketConditionResult
        """
        # 메모리 캐시 확인
        cache_key = f"market_condition_{market}"
        if cache_key in self.cache:
            cached, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_duration:
                return cached

        # 파일 캐시 확인 (API 호출 전에)
        file_cached = self._get_file_cache(cache_key)
        if file_cached:
            self.cache[cache_key] = (file_cached, datetime.now())
            return file_cached

        # 지수 데이터 가져오기
        indices_to_analyze = []
        if market in ("us", "all"):
            indices_to_analyze.extend(self.INDICES["us"])
        if market in ("korea", "all"):
            indices_to_analyze.extend(self.INDICES["korea"])
        if market in ("crypto", "all"):
            indices_to_analyze.extend(self.INDICES["crypto"])

        # 분석 실행 (Rate limit 방지를 위한 딜레이 포함)
        import time
        index_analyses = []
        for i, (symbol, name) in enumerate(indices_to_analyze):
            if i > 0:
                time.sleep(1.0)  # 요청 간 1초 딜레이
            analysis = self._analyze_index(symbol, name)
            if analysis:
                index_analyses.append(analysis)

        # API 실패 시 폴백 데이터 사용
        if not index_analyses:
            logger.warning(f"All index analyses failed for {market}, using fallback data")
            fallback = self.FALLBACK_MARKET_DATA.get(market, self.FALLBACK_MARKET_DATA["us"])
            result = MarketConditionResult(
                condition=MarketRegime(fallback["condition"]),
                confidence=fallback["confidence"],
                timestamp=datetime.now(),
                signals=["⚠️ API 제한으로 실시간 데이터 없음"],
                warnings=["데이터 소스 연결 실패"],
                summary=fallback["summary"],
                recommendation=fallback["recommendation"],
            )
            # 실패 캐시 저장 (10분간 재시도 안함)
            self.cache[cache_key] = (result, datetime.now())
            self._save_file_cache(cache_key, result, is_failure=True)
            return result

        # VIX 분석 (미국/한국 시장용)
        vix_level = None
        vix_status = "unknown"

        if market in ("us", "korea", "all"):
            time.sleep(1.0)  # Rate limit 방지
            vix_data = self._get_vix()
            if vix_data is not None:
                vix_level = vix_data
                vix_status = self._get_vix_status(vix_data)

        # 크립토 Fear & Greed Index (크립토 시장용)
        fear_greed = None
        fear_greed_status = "unknown"

        if market in ("crypto", "all"):
            fear_greed = self._get_crypto_fear_greed()
            if fear_greed is not None:
                fear_greed_status = self._get_fear_greed_status(fear_greed)
                # 크립토는 VIX 대신 Fear & Greed 사용
                if market == "crypto":
                    vix_level = fear_greed
                    vix_status = fear_greed_status

        # 종합 판단
        result = self._determine_condition(index_analyses, vix_level, vix_status, market)
        result.index_analyses = index_analyses
        result.vix_level = vix_level
        result.vix_status = vix_status

        # 캐시 저장 (메모리 + 파일, 성공)
        self.cache[cache_key] = (result, datetime.now())
        self._save_file_cache(cache_key, result)

        return result

    def _analyze_index(self, symbol: str, name: str, max_retries: int = 3) -> Optional[IndexAnalysis]:
        """개별 지수 분석 - 기술적 지표 강화"""
        import time
        import yfinance as yf
        import logging as _logging
        import numpy as np
        import sys
        import io

        _logging.getLogger("yfinance").setLevel(_logging.CRITICAL)

        # Rate limit 시 재시도 로직
        df = None
        for attempt in range(max_retries):
            try:
                # yfinance 에러 메시지 숨기기
                old_stderr = sys.stderr
                sys.stderr = io.StringIO()
                try:
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(period="1y")
                finally:
                    captured = sys.stderr.getvalue()
                    sys.stderr = old_stderr

                    # 캡처된 에러에서 rate limit 확인
                    if "rate" in captured.lower() or "too many" in captured.lower():
                        raise Exception("Rate limited")

                if df is not None and not df.empty:
                    break

            except Exception as e:
                error_msg = str(e).lower()
                if "rate" in error_msg or "limit" in error_msg or "too many" in error_msg:
                    wait_time = (2 ** attempt) * 3  # 3, 6, 12초
                    # 첫 번째 시도만 로그 (스팸 방지)
                    if attempt == 0:
                        logger.debug(f"{symbol} rate limited, will retry with backoff")
                    time.sleep(wait_time)
                else:
                    logger.debug(f"{symbol} fetch error: {e}")
                    break

        if df is None or df.empty or len(df) < 50:
            logger.debug(f"{symbol}: insufficient data")
            return None

        try:

            close = df['Close']
            high = df['High']
            low = df['Low']
            current = close.iloc[-1]

            # === 변화율 계산 ===
            change_1d = ((current / close.iloc[-2]) - 1) * 100 if len(df) >= 2 else 0
            change_1w = ((current / close.iloc[-5]) - 1) * 100 if len(df) >= 5 else 0
            change_1m = ((current / close.iloc[-21]) - 1) * 100 if len(df) >= 21 else 0
            change_3m = ((current / close.iloc[-63]) - 1) * 100 if len(df) >= 63 else 0

            # === 이동평균 ===
            ma10 = close.rolling(10).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma50 = close.rolling(50).mean().iloc[-1]
            ma150 = close.rolling(150).mean().iloc[-1] if len(df) >= 150 else ma50
            ma200 = close.rolling(200).mean().iloc[-1] if len(df) >= 200 else ma150

            # 이동평균 기울기 (추세 강도)
            ma50_slope = (close.rolling(50).mean().iloc[-1] - close.rolling(50).mean().iloc[-20]) / 20 if len(df) >= 70 else 0
            ma200_slope = (close.rolling(200).mean().iloc[-1] - close.rolling(200).mean().iloc[-20]) / 20 if len(df) >= 220 else 0

            # === RSI ===
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]

            # === MACD ===
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_histogram = macd_line - signal_line

            macd_bullish = macd_line.iloc[-1] > signal_line.iloc[-1]
            macd_histogram_rising = macd_histogram.iloc[-1] > macd_histogram.iloc[-5] if len(df) >= 5 else False

            # === ADX (Average Directional Index) - 추세 강도 ===
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr14 = tr.rolling(14).mean()

            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

            plus_di = 100 * (plus_dm.rolling(14).mean() / atr14)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr14)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(14).mean().iloc[-1] if not dx.rolling(14).mean().isna().iloc[-1] else 20

            # === Bollinger Bands ===
            bb_mid = close.rolling(20).mean()
            bb_std = close.rolling(20).std()
            bb_upper = bb_mid + 2 * bb_std
            bb_lower = bb_mid - 2 * bb_std
            bb_position = (current - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]) * 100

            # === 52주 고저점 ===
            high_52w = high.max()
            low_52w = low.min()
            from_52w_high = ((current / high_52w) - 1) * 100
            from_52w_low = ((current / low_52w) - 1) * 100

            # === 복합 추세 판단 ===
            above_ma20 = current > ma20
            above_ma50 = current > ma50
            above_ma200 = current > ma200
            ma20_above_ma50 = ma20 > ma50
            ma50_above_ma200 = ma50 > ma200

            # 추세 점수 계산 (복합 조건)
            trend_score = 0

            # 가격 vs 이동평균 (최대 30점)
            if current > ma200: trend_score += 10
            if current > ma150: trend_score += 5
            if current > ma50: trend_score += 8
            if current > ma20: trend_score += 7

            # 이동평균 정배열/역배열 (최대 20점)
            if ma20 > ma50 > ma150 > ma200:
                trend_score += 20  # 완벽한 정배열
            elif ma20 > ma50 > ma200:
                trend_score += 15
            elif ma50 > ma200:
                trend_score += 10
            elif ma20 < ma50 < ma150 < ma200:
                trend_score -= 15  # 역배열

            # 이동평균 기울기 (최대 15점)
            if ma50_slope > 0 and ma200_slope > 0:
                trend_score += 15
            elif ma50_slope > 0:
                trend_score += 8
            elif ma50_slope < 0 and ma200_slope < 0:
                trend_score -= 10

            # MACD (최대 15점)
            if macd_bullish and macd_histogram_rising:
                trend_score += 15
            elif macd_bullish:
                trend_score += 8
            elif not macd_bullish:
                trend_score -= 5

            # RSI (최대 10점)
            if 50 < rsi < 70:
                trend_score += 10  # 건강한 상승
            elif rsi >= 70:
                trend_score += 5   # 과매수 주의
            elif 30 < rsi < 50:
                trend_score -= 5   # 약세
            elif rsi <= 30:
                trend_score -= 10  # 과매도

            # ADX - 추세 강도 (최대 10점)
            if adx > 25:  # 강한 추세
                trend_score += 10 if trend_score > 0 else -10
            elif adx > 20:
                trend_score += 5 if trend_score > 0 else -5

            # 추세 결정
            if trend_score >= 50:
                trend = "uptrend"
                strength = "strong"
            elif trend_score >= 25:
                trend = "uptrend"
                strength = "moderate"
            elif trend_score <= -50:
                trend = "downtrend"
                strength = "strong"
            elif trend_score <= -25:
                trend = "downtrend"
                strength = "moderate"
            else:
                trend = "sideways"
                strength = "weak" if -10 < trend_score < 10 else "moderate"

            return IndexAnalysis(
                symbol=symbol,
                name=name,
                current_price=current,
                change_1d=change_1d,
                change_1w=change_1w,
                change_1m=change_1m,
                change_3m=change_3m,
                above_ma20=above_ma20,
                above_ma50=above_ma50,
                above_ma200=above_ma200,
                ma20_above_ma50=ma20_above_ma50,
                ma50_above_ma200=ma50_above_ma200,
                rsi_14=rsi,
                from_52w_high=from_52w_high,
                from_52w_low=from_52w_low,
                trend=trend,
                strength=strength,
            )

        except Exception as e:
            logger.warning(f"Index analysis failed for {symbol}: {e}")
            return None

    def _get_vix(self, max_retries: int = 3) -> Optional[float]:
        """VIX 값 가져오기 (Rate limit 재시도 포함)"""
        import time
        import yfinance as yf
        import sys
        import io

        for attempt in range(max_retries):
            try:
                old_stderr = sys.stderr
                sys.stderr = io.StringIO()
                try:
                    ticker = yf.Ticker("^VIX")
                    data = ticker.history(period="5d")
                finally:
                    captured = sys.stderr.getvalue()
                    sys.stderr = old_stderr

                    if "rate" in captured.lower() or "too many" in captured.lower():
                        raise Exception("Rate limited")

                if not data.empty:
                    return data['Close'].iloc[-1]
            except Exception as e:
                error_msg = str(e).lower()
                if "rate" in error_msg or "limit" in error_msg or "too many" in error_msg:
                    wait_time = (2 ** attempt) * 3
                    if attempt == 0:
                        logger.debug(f"VIX rate limited, will retry with backoff")
                    time.sleep(wait_time)
                else:
                    logger.debug(f"VIX fetch failed: {e}")
                    break
        return None

    def _get_vix_status(self, vix: float) -> str:
        """VIX 상태 판단"""
        for status, (low, high) in self.VIX_LEVELS.items():
            if low <= vix < high:
                return status
        return "extreme"

    def _get_crypto_fear_greed(self) -> Optional[float]:
        """크립토 Fear & Greed Index 가져오기"""
        try:
            import urllib.request
            import json

            url = "https://api.alternative.me/fng/?limit=1"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data.get("data"):
                    return float(data["data"][0]["value"])
        except Exception as e:
            logger.warning(f"Crypto Fear & Greed fetch failed: {e}")

            # 대안: BTC 변동성 기반 추정
            try:
                import yfinance as yf
                btc = yf.Ticker("BTC-USD")
                hist = btc.history(period="30d")
                if not hist.empty:
                    # 30일 변동성으로 대략적인 Fear & Greed 추정
                    returns = hist['Close'].pct_change().dropna()
                    volatility = returns.std() * 100
                    avg_return = returns.mean() * 100

                    # 수익률과 변동성 기반 추정
                    if avg_return > 2 and volatility < 5:
                        return 75  # Greed
                    elif avg_return > 0:
                        return 55  # Neutral-Greed
                    elif avg_return < -2 and volatility > 5:
                        return 25  # Fear
                    else:
                        return 45  # Neutral
            except:
                pass

        return None

    def _get_fear_greed_status(self, value: float) -> str:
        """Fear & Greed 상태 판단"""
        for status, (low, high) in self.CRYPTO_FEAR_GREED.items():
            if low <= value < high:
                return status
        return "extreme_greed" if value >= 75 else "extreme_fear"

    def _determine_condition(
        self,
        analyses: List[IndexAnalysis],
        vix: Optional[float],
        vix_status: str,
        market: str = "us"
    ) -> MarketConditionResult:
        """종합 시장 상황 판단"""

        if not analyses:
            return MarketConditionResult(
                condition=MarketRegime.SIDEWAYS,
                confidence=0,
                timestamp=datetime.now(),
                summary="데이터 부족으로 판단 불가",
            )

        # 점수 계산
        bull_score = 0
        bear_score = 0
        sideways_score = 0
        volatile_score = 0
        signals = []
        warnings = []

        # 지수별 분석
        uptrend_count = sum(1 for a in analyses if a.trend == "uptrend")
        downtrend_count = sum(1 for a in analyses if a.trend == "downtrend")
        sideways_count = sum(1 for a in analyses if a.trend == "sideways")
        total = len(analyses)

        # 추세 기반 점수
        if uptrend_count / total >= 0.6:
            bull_score += 40
            signals.append(f"📈 {uptrend_count}/{total} 지수 상승 추세")
        elif downtrend_count / total >= 0.6:
            bear_score += 40
            signals.append(f"📉 {downtrend_count}/{total} 지수 하락 추세")
        else:
            sideways_score += 30
            signals.append(f"↔️ 혼조세 (상승:{uptrend_count}, 하락:{downtrend_count})")

        # 이동평균 분석
        above_200ma_count = sum(1 for a in analyses if a.above_ma200)
        if above_200ma_count / total >= 0.7:
            bull_score += 20
            signals.append("✅ 대부분 200일선 위")
        elif above_200ma_count / total <= 0.3:
            bear_score += 20
            signals.append("⚠️ 대부분 200일선 아래")

        # 골든크로스/데드크로스
        golden_cross = sum(1 for a in analyses if a.ma50_above_ma200)
        if golden_cross / total >= 0.7:
            bull_score += 15
            signals.append("🌟 골든크로스 우세")
        elif golden_cross / total <= 0.3:
            bear_score += 15
            signals.append("💀 데드크로스 우세")

        # 단기 모멘텀 (1개월 수익률)
        avg_1m_return = sum(a.change_1m for a in analyses) / total
        if avg_1m_return > 5:
            bull_score += 15
            signals.append(f"🚀 강한 1개월 수익률 (+{avg_1m_return:.1f}%)")
        elif avg_1m_return < -5:
            bear_score += 15
            signals.append(f"📉 약한 1개월 수익률 ({avg_1m_return:.1f}%)")
        elif -2 < avg_1m_return < 2:
            sideways_score += 15
            signals.append(f"➡️ 횡보 중 ({avg_1m_return:.1f}%)")

        # 52주 고점 대비
        avg_from_high = sum(a.from_52w_high for a in analyses) / total
        if avg_from_high > -5:
            bull_score += 10
            signals.append(f"📊 52주 고점 근처 ({avg_from_high:.1f}%)")
        elif avg_from_high < -20:
            bear_score += 10
            if avg_from_high < -10:
                signals.append(f"📉 52주 고점 대비 큰 하락 ({avg_from_high:.1f}%)")

        # VIX / Fear & Greed 기반 분석
        if vix is not None:
            if market == "crypto":
                # 크립토: Fear & Greed Index (0-100, 높을수록 탐욕)
                if vix_status == "extreme_greed":
                    warnings.append(f"🔥 극단적 탐욕 ({vix:.0f}) - 과열 주의")
                    sideways_score += 10
                elif vix_status == "greed":
                    bull_score += 10
                    signals.append(f"😀 탐욕 구간 ({vix:.0f})")
                elif vix_status == "neutral":
                    signals.append(f"😐 중립 구간 ({vix:.0f})")
                elif vix_status == "fear":
                    bear_score += 10
                    signals.append(f"😰 공포 구간 ({vix:.0f})")
                elif vix_status == "extreme_fear":
                    bear_score += 15
                    volatile_score += 20
                    warnings.append(f"😱 극단적 공포 ({vix:.0f}) - 매수 기회?")
            else:
                # 주식: VIX (낮을수록 안정)
                if vix_status == "low":
                    bull_score += 10
                    signals.append(f"😌 VIX 낮음 ({vix:.1f}) - 낙관적")
                elif vix_status == "normal":
                    signals.append(f"😐 VIX 보통 ({vix:.1f})")
                elif vix_status == "elevated":
                    sideways_score += 10
                    warnings.append(f"⚠️ VIX 상승 ({vix:.1f}) - 주의 필요")
                elif vix_status in ("high", "extreme"):
                    volatile_score += 30
                    bear_score += 10
                    warnings.append(f"🚨 VIX 높음 ({vix:.1f}) - 고변동성/공포")

        # 회복기/조정기 판단
        is_recovery = False
        is_correction = False

        # 조정기: 최근 상승 후 단기 하락
        avg_3m_return = sum(a.change_3m for a in analyses) / total
        if avg_3m_return > 10 and avg_1m_return < 0:
            is_correction = True
            signals.append("📉 상승 후 조정 국면")

        # 회복기: 저점에서 반등
        if avg_from_high < -15 and avg_1m_return > 3:
            is_recovery = True
            signals.append("🌱 저점에서 회복 중")

        # 최종 판단
        scores = {
            MarketRegime.BULL: bull_score,
            MarketRegime.BEAR: bear_score,
            MarketRegime.SIDEWAYS: sideways_score,
            MarketRegime.VOLATILE: volatile_score,
        }

        # 특수 상황 체크
        if is_recovery and bull_score < bear_score:
            condition = MarketRegime.RECOVERY
        elif is_correction and bear_score < bull_score:
            condition = MarketRegime.CORRECTION
        elif volatile_score >= 30:
            condition = MarketRegime.VOLATILE
        else:
            condition = max(scores, key=scores.get)

        # 신뢰도 계산
        max_score = max(scores.values())
        total_score = sum(scores.values())
        confidence = (max_score / total_score * 100) if total_score > 0 else 50

        # 요약 및 추천 생성
        summary, recommendation = self._generate_summary(
            condition, analyses, avg_1m_return, avg_3m_return, vix, vix_status, market
        )

        return MarketConditionResult(
            condition=condition,
            confidence=min(confidence, 95),  # 최대 95%
            timestamp=datetime.now(),
            signals=signals,
            warnings=warnings,
            bull_score=bull_score,
            bear_score=bear_score,
            sideways_score=sideways_score,
            volatile_score=volatile_score,
            summary=summary,
            recommendation=recommendation,
        )

    def _generate_summary(
        self,
        condition: MarketRegime,
        analyses: List[IndexAnalysis],
        avg_1m: float,
        avg_3m: float,
        vix: Optional[float],
        vix_status: str,
        market: str = "us"
    ) -> Tuple[str, str]:
        """요약 및 추천 생성"""

        market_name = {
            "us": "미국 시장",
            "korea": "한국 시장",
            "crypto": "크립토 시장",
            "all": "글로벌 시장",
        }.get(market, "시장")

        if market == "crypto":
            summaries = {
                MarketRegime.BULL: f"{market_name}은 강세장입니다. BTC, ETH 등 주요 코인이 상승 추세이며, 3개월 평균 {avg_3m:.1f}% 상승했습니다.",
                MarketRegime.BEAR: f"{market_name}은 약세장입니다. 주요 코인이 하락 추세이며, 신중한 접근이 필요합니다.",
                MarketRegime.SIDEWAYS: f"{market_name}은 횡보 구간입니다. 뚜렷한 방향 없이 박스권에서 움직이고 있습니다.",
                MarketRegime.VOLATILE: f"{market_name}은 고변동성 구간입니다. Fear & Greed {vix:.0f}로 불안정합니다." if vix else f"{market_name}은 고변동성 구간입니다.",
                MarketRegime.RECOVERY: f"{market_name}은 회복 중입니다. 저점에서 반등하며 1개월 {avg_1m:.1f}% 상승했습니다.",
                MarketRegime.CORRECTION: f"{market_name}은 조정 구간입니다. 상승 후 일시적 하락 중입니다.",
            }
            recommendations = {
                MarketRegime.BULL: "알트코인 모멘텀 전략이 효과적입니다. 강세 추세를 따라가세요.",
                MarketRegime.BEAR: "스테이블코인 비중 확대, DCA 전략을 고려하세요.",
                MarketRegime.SIDEWAYS: "레인지 트레이딩, 그리드 봇 전략이 유리합니다.",
                MarketRegime.VOLATILE: "포지션 축소, 레버리지 사용 자제하세요.",
                MarketRegime.RECOVERY: "메이저 코인 비중 확대, 선별적 알트 진입을 고려하세요.",
                MarketRegime.CORRECTION: "DCA 매수 기회입니다. 우량 코인 분할 매수하세요.",
            }
        elif market == "korea":
            summaries = {
                MarketRegime.BULL: f"{market_name}은 강세장입니다. KOSPI/KOSDAQ이 상승 추세이며, 3개월 평균 {avg_3m:.1f}% 상승했습니다.",
                MarketRegime.BEAR: f"{market_name}은 약세장입니다. 외국인 매도세와 함께 하락 추세입니다.",
                MarketRegime.SIDEWAYS: f"{market_name}은 횡보장입니다. 박스권에서 등락을 반복하고 있습니다.",
                MarketRegime.VOLATILE: f"{market_name}은 고변동성 구간입니다. VIX {vix:.1f}로 불확실성이 높습니다." if vix else f"{market_name}은 고변동성 구간입니다.",
                MarketRegime.RECOVERY: f"{market_name}은 회복 국면입니다. 저점에서 반등하며 1개월 {avg_1m:.1f}% 상승했습니다.",
                MarketRegime.CORRECTION: f"{market_name}은 조정 국면입니다. 상승 추세 후 숨 고르기 중입니다.",
            }
            recommendations = {
                MarketRegime.BULL: "2차전지, 반도체 등 주도주 모멘텀 전략이 효과적입니다.",
                MarketRegime.BEAR: "배당주, 방어주 비중 확대를 고려하세요.",
                MarketRegime.SIDEWAYS: "박스권 스윙 트레이딩이 유리합니다.",
                MarketRegime.VOLATILE: "현금 비중 확대, 리스크 관리에 집중하세요.",
                MarketRegime.RECOVERY: "경기민감주, 저평가 가치주를 주목하세요.",
                MarketRegime.CORRECTION: "우량 대형주 눌림목 매수 기회입니다.",
            }
        else:
            summaries = {
                MarketRegime.BULL: f"{market_name}은 강세장입니다. 주요 지수가 상승 추세를 보이고 있으며, 3개월 평균 수익률 {avg_3m:.1f}%를 기록 중입니다.",
                MarketRegime.BEAR: f"{market_name}은 약세장입니다. 주요 지수가 하락 추세이며, 방어적인 포지션이 필요합니다.",
                MarketRegime.SIDEWAYS: f"{market_name}은 횡보장입니다. 뚜렷한 방향성 없이 박스권에서 움직이고 있습니다.",
                MarketRegime.VOLATILE: f"{market_name}은 고변동성 구간입니다. VIX {vix:.1f}로 불확실성이 높습니다." if vix else f"{market_name}은 고변동성 구간입니다.",
                MarketRegime.RECOVERY: f"{market_name}은 회복 국면입니다. 저점에서 반등하며 1개월 {avg_1m:.1f}% 상승했습니다.",
                MarketRegime.CORRECTION: f"{market_name}은 조정 국면입니다. 상승 추세 후 일시적 하락 중입니다.",
            }
            recommendations = {
                MarketRegime.BULL: "모멘텀/성장주 전략이 효과적입니다. 상승 추세를 따라가세요.",
                MarketRegime.BEAR: "방어주/배당주 비중 확대, 현금 비중 유지를 고려하세요.",
                MarketRegime.SIDEWAYS: "스윙 트레이딩, 박스권 매매가 유리합니다.",
                MarketRegime.VOLATILE: "포지션 축소, 리스크 관리에 집중하세요.",
                MarketRegime.RECOVERY: "경기민감주, 턴어라운드 종목을 주목하세요.",
                MarketRegime.CORRECTION: "우량주 눌림목 매수 기회를 노려보세요.",
            }

        return summaries.get(condition, ""), recommendations.get(condition, "")

    def get_detailed_report(self, market: str = "us") -> str:
        """상세 리포트 생성"""
        result = self.detect(market)

        report = []
        report.append("=" * 60)
        report.append("📊 시장 상황 분석 리포트")
        report.append("=" * 60)
        report.append(f"\n🎯 현재 시장: {result.condition.value.upper()}")
        report.append(f"📈 신뢰도: {result.confidence:.0f}%")
        report.append(f"⏰ 분석 시점: {result.timestamp.strftime('%Y-%m-%d %H:%M')}")

        if result.vix_level:
            report.append(f"\n📉 VIX: {result.vix_level:.1f} ({result.vix_status})")

        report.append(f"\n💡 요약:\n{result.summary}")
        report.append(f"\n🎯 추천:\n{result.recommendation}")

        report.append("\n" + "-" * 40)
        report.append("📌 주요 시그널:")
        for signal in result.signals:
            report.append(f"  {signal}")

        if result.warnings:
            report.append("\n⚠️ 경고:")
            for warning in result.warnings:
                report.append(f"  {warning}")

        report.append("\n" + "-" * 40)
        report.append("📊 지수별 현황:")
        for idx in result.index_analyses:
            report.append(f"\n  {idx.name} ({idx.symbol})")
            report.append(f"    현재가: {idx.current_price:,.2f}")
            report.append(f"    1일: {idx.change_1d:+.1f}% | 1주: {idx.change_1w:+.1f}% | 1개월: {idx.change_1m:+.1f}%")
            report.append(f"    추세: {idx.trend} ({idx.strength})")
            report.append(f"    RSI: {idx.rsi_14:.1f} | 52주고점대비: {idx.from_52w_high:.1f}%")

        report.append("\n" + "=" * 60)

        return "\n".join(report)


# 간편 사용 함수
def detect_market_condition(market: str = "us") -> MarketConditionResult:
    """시장 상황 감지 (간편 함수)"""
    detector = MarketConditionDetector()
    return detector.detect(market)


def get_market_report(market: str = "us") -> str:
    """시장 리포트 생성 (간편 함수)"""
    detector = MarketConditionDetector()
    return detector.get_detailed_report(market)


if __name__ == "__main__":
    # 테스트
    print(get_market_report("us"))
