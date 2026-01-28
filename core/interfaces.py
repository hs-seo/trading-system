"""
Core Interfaces - 모든 플러그인의 기반이 되는 추상 베이스 클래스

확장 시 이 인터페이스들을 구현하면 시스템과 자동 통합됩니다.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import pandas as pd


# ============================================================================
# Common Data Types
# ============================================================================

class Market(Enum):
    """지원 시장"""
    KOSPI = "kospi"
    KOSDAQ = "kosdaq"
    NASDAQ = "nasdaq"
    NYSE = "nyse"
    CRYPTO = "crypto"
    FUTURES = "futures"
    ETF = "etf"


class Timeframe(Enum):
    """타임프레임"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MN1 = "1M"


class SignalType(Enum):
    """신호 타입"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"  # 관심 종목


class Confidence(Enum):
    """신뢰도 수준"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


@dataclass
class Symbol:
    """종목 정보"""
    ticker: str
    name: str
    market: Market
    sector: Optional[str] = None
    industry: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OHLCV:
    """가격 데이터"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass
class Signal:
    """분석 신호"""
    symbol: Symbol
    signal_type: SignalType
    confidence: Confidence
    source: str  # 신호 출처 (indicator/strategy 이름)
    timestamp: datetime
    price: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 추가 컨텍스트 (LLM/Expert 분석용)
    chart_context: Optional[str] = None
    fundamental_context: Optional[str] = None


@dataclass
class AnalysisResult:
    """분석 결과 컨테이너"""
    symbol: Symbol
    timestamp: datetime
    indicators: Dict[str, Any] = field(default_factory=dict)
    signals: List[Signal] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)  # 각 기준별 점수
    final_score: Optional[float] = None
    rank: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Data Source Interface
# ============================================================================

class DataSource(ABC):
    """
    데이터 소스 추상 베이스 클래스

    새 데이터 소스 추가 시 이 클래스를 상속하세요.
    예: yfinance, KRX, Binance, TradingView 등
    """

    name: str = "base"
    supported_markets: List[Market] = []

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        OHLCV 데이터 조회

        Returns:
            DataFrame with columns: [timestamp, open, high, low, close, volume]
        """
        pass

    @abstractmethod
    def fetch_symbols(self, market: Market) -> List[Symbol]:
        """시장의 전체 종목 목록 조회"""
        pass

    def fetch_realtime(self, symbol: str) -> Optional[OHLCV]:
        """실시간 가격 (지원하는 소스만)"""
        return None

    def fetch_orderbook(self, symbol: str) -> Optional[Dict]:
        """호가창 데이터 (지원하는 소스만)"""
        return None

    def health_check(self) -> bool:
        """연결 상태 확인"""
        return True


class FinancialDataSource(DataSource):
    """
    재무 데이터 소스 확장 인터페이스

    가격 외 재무제표, 밸류에이션 등 제공
    """

    @abstractmethod
    def fetch_financials(
        self,
        symbol: str,
        period: str = "annual",  # annual, quarterly
    ) -> pd.DataFrame:
        """재무제표 조회"""
        pass

    @abstractmethod
    def fetch_ratios(self, symbol: str) -> Dict[str, float]:
        """
        주요 비율 조회

        Returns:
            {
                "PER": 15.5,
                "PBR": 2.1,
                "EV_EBITDA": 8.3,
                "ROIC": 18.5,
                "FCF_Yield": 5.2,
                ...
            }
        """
        pass

    def fetch_estimates(self, symbol: str) -> Optional[Dict]:
        """애널리스트 추정치 (지원하는 소스만)"""
        return None


# ============================================================================
# Storage Interface
# ============================================================================

class Storage(ABC):
    """
    저장소 추상 베이스 클래스

    새 저장소 추가 시 이 클래스를 상속하세요.
    예: SQLite, PostgreSQL, Parquet, TimescaleDB 등
    """

    name: str = "base"

    @abstractmethod
    def save_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        data: pd.DataFrame,
    ) -> bool:
        """OHLCV 데이터 저장"""
        pass

    @abstractmethod
    def load_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """OHLCV 데이터 로드"""
        pass

    @abstractmethod
    def save_analysis(self, result: AnalysisResult) -> bool:
        """분석 결과 저장"""
        pass

    @abstractmethod
    def load_analysis(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[AnalysisResult]:
        """분석 결과 로드"""
        pass

    def get_last_update(self, symbol: str, timeframe: Timeframe) -> Optional[datetime]:
        """마지막 업데이트 시간"""
        return None

    def list_symbols(self, market: Optional[Market] = None) -> List[str]:
        """저장된 종목 목록"""
        return []


# ============================================================================
# Indicator Interface
# ============================================================================

class Indicator(ABC):
    """
    기술적 지표 추상 베이스 클래스

    새 인디케이터 추가 시 이 클래스를 상속하세요.
    트레이딩뷰 인디케이터도 이 형식으로 래핑 가능
    """

    name: str = "base"
    description: str = ""

    # 설정 가능한 파라미터 정의
    default_params: Dict[str, Any] = {}

    def __init__(self, **params):
        self.params = {**self.default_params, **params}

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        지표 계산

        Args:
            df: OHLCV DataFrame

        Returns:
            원본 df에 계산된 컬럼이 추가된 DataFrame
        """
        pass

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """
        신호 생성 (선택적 구현)

        기본적으로 calculate만 구현해도 됨.
        특정 조건에서 신호를 생성하려면 이 메서드 오버라이드
        """
        return []

    def to_config(self) -> Dict:
        """설정 직렬화"""
        return {
            "name": self.name,
            "params": self.params,
        }

    @classmethod
    def from_config(cls, config: Dict) -> "Indicator":
        """설정에서 인스턴스 생성"""
        return cls(**config.get("params", {}))


# ============================================================================
# Strategy Interface
# ============================================================================

class Strategy(ABC):
    """
    스크리닝/트레이딩 전략 추상 베이스 클래스

    여러 인디케이터와 조건을 조합하여 종목 선정
    """

    name: str = "base"
    description: str = ""

    # 이 전략에 필요한 인디케이터들
    required_indicators: List[str] = []

    # 설정 가능한 파라미터
    default_params: Dict[str, Any] = {}

    def __init__(self, **params):
        self.params = {**self.default_params, **params}
        self.indicators: List[Indicator] = []

    def add_indicator(self, indicator: Indicator):
        """인디케이터 추가"""
        self.indicators.append(indicator)

    @abstractmethod
    def screen(
        self,
        universe: List[Symbol],
        data: Dict[str, pd.DataFrame],  # symbol -> OHLCV DataFrame
    ) -> List[AnalysisResult]:
        """
        종목 스크리닝

        Args:
            universe: 검색 대상 종목 리스트
            data: 각 종목의 가격 데이터

        Returns:
            분석 결과 리스트 (점수순 정렬)
        """
        pass

    def backtest(
        self,
        symbol: Symbol,
        data: pd.DataFrame,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """
        백테스팅 (선택적 구현)

        Returns:
            {
                "total_return": 0.25,
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.15,
                "win_rate": 0.6,
                "trades": [...],
            }
        """
        return {}


# ============================================================================
# Decision Engine Interface
# ============================================================================

class DecisionEngine(ABC):
    """
    의사결정 엔진 추상 베이스 클래스

    여러 신호/분석을 종합하여 최종 결정
    예: Rule-based, Ensemble, Genetic Algorithm, LLM 등
    """

    name: str = "base"

    @abstractmethod
    def decide(
        self,
        analysis_results: List[AnalysisResult],
        context: Optional[Dict] = None,
    ) -> List[Signal]:
        """
        최종 결정

        Args:
            analysis_results: 여러 전략/인디케이터의 분석 결과
            context: 추가 컨텍스트 (매크로, 뉴스 등)

        Returns:
            최종 신호 리스트
        """
        pass

    def explain(self, signal: Signal) -> str:
        """결정 이유 설명 (LLM 연동용)"""
        return signal.reason


class GeneticEngine(DecisionEngine):
    """
    유전자 알고리즘 기반 결정 엔진

    파라미터 최적화 및 전략 조합 최적화에 사용
    """

    name: str = "genetic"

    @abstractmethod
    def evolve(
        self,
        population: List[Dict],  # 파라미터 세트들
        fitness_func: callable,
        generations: int = 100,
    ) -> Dict:
        """
        진화 실행

        Returns:
            최적 파라미터 세트
        """
        pass

    @abstractmethod
    def crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """교차"""
        pass

    @abstractmethod
    def mutate(self, individual: Dict, rate: float = 0.1) -> Dict:
        """돌연변이"""
        pass


# ============================================================================
# Expert Interface (LLM Integration)
# ============================================================================

class Expert(ABC):
    """
    전문가 시스템 추상 베이스 클래스

    LLM을 활용한 분석 및 의사결정
    """

    name: str = "base"
    expertise: str = ""  # "chart", "fundamental", "macro" 등

    @abstractmethod
    def analyze(
        self,
        symbol: Symbol,
        data: pd.DataFrame,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        전문가 분석

        Returns:
            {
                "opinion": "bullish/bearish/neutral",
                "confidence": 0.8,
                "reasoning": "...",
                "key_points": [...],
                "risks": [...],
            }
        """
        pass

    @abstractmethod
    def get_prompt(self, analysis_request: Dict) -> str:
        """LLM 프롬프트 생성"""
        pass

    def parse_response(self, response: str) -> Dict:
        """LLM 응답 파싱"""
        return {"raw": response}


class ChartExpert(Expert):
    """차트 분석 전문가"""
    expertise = "chart"

    @abstractmethod
    def describe_pattern(self, df: pd.DataFrame) -> str:
        """차트 패턴 설명"""
        pass

    @abstractmethod
    def identify_levels(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """
        주요 레벨 식별

        Returns:
            {
                "support": [100.0, 95.0],
                "resistance": [110.0, 120.0],
                "supply_zones": [(115, 118), ...],
                "demand_zones": [(95, 98), ...],
            }
        """
        pass


class FundamentalExpert(Expert):
    """펀더멘털 분석 전문가"""
    expertise = "fundamental"

    @abstractmethod
    def analyze_valuation(self, ratios: Dict[str, float]) -> Dict:
        """밸류에이션 분석"""
        pass

    @abstractmethod
    def analyze_quality(self, financials: pd.DataFrame) -> Dict:
        """기업 품질 분석"""
        pass


# ============================================================================
# Alert Interface
# ============================================================================

class AlertChannel(ABC):
    """
    알람 채널 추상 베이스 클래스

    예: Telegram, Discord, Email, Webhook 등
    """

    name: str = "base"

    @abstractmethod
    def send(self, signal: Signal) -> bool:
        """신호 전송"""
        pass

    @abstractmethod
    def send_batch(self, signals: List[Signal]) -> bool:
        """여러 신호 일괄 전송"""
        pass

    def format_message(self, signal: Signal) -> str:
        """메시지 포맷팅"""
        return f"""
[{signal.signal_type.value.upper()}] {signal.symbol.ticker}
Price: {signal.price}
Confidence: {signal.confidence.name}
Source: {signal.source}
Reason: {signal.reason}
Time: {signal.timestamp}
        """.strip()
