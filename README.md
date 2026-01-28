# Trading System - 확장 가능한 종목 선정 시스템

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Trading System                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │ Data Sources │───▶│   Storage    │───▶│   Analysis   │               │
│  │  (Plugins)   │    │  (TimeSeries)│    │  (Plugins)   │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│         │                   │                    │                       │
│         ▼                   ▼                    ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │ - yfinance   │    │ - SQLite     │    │ - Indicators │               │
│  │ - KRX        │    │ - PostgreSQL │    │ - SMC        │               │
│  │ - Binance    │    │ - TimescaleDB│    │ - ML Models  │               │
│  │ - TradingView│    │ - Parquet    │    │ - LLM Expert │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                 │                        │
│                                                 ▼                        │
│                      ┌──────────────────────────────────────┐           │
│                      │         Decision Engine              │           │
│                      │  ┌────────┐ ┌────────┐ ┌──────────┐  │           │
│                      │  │ Rules  │ │Genetic │ │   LLM    │  │           │
│                      │  │ Based  │ │  Algo  │ │ Ensemble │  │           │
│                      │  └────────┘ └────────┘ └──────────┘  │           │
│                      └──────────────────────────────────────┘           │
│                                      │                                   │
│                                      ▼                                   │
│                      ┌──────────────────────────────────────┐           │
│                      │         Signal & Alert               │           │
│                      │    Telegram / Discord / Dashboard    │           │
│                      └──────────────────────────────────────┘           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 디렉토리 구조

```
trading-system/
├── core/                    # 핵심 추상화 및 인터페이스
│   ├── __init__.py
│   ├── interfaces.py        # 추상 베이스 클래스
│   ├── registry.py          # 플러그인 레지스트리
│   ├── events.py            # 이벤트 시스템
│   └── pipeline.py          # 데이터 파이프라인
│
├── data/                    # 데이터 레이어
│   ├── sources/             # 데이터 소스 플러그인
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── yfinance_source.py
│   │   ├── krx_source.py
│   │   ├── binance_source.py
│   │   └── financial_source.py
│   │
│   └── storage/             # 저장소 플러그인
│       ├── __init__.py
│       ├── base.py
│       ├── sqlite_storage.py
│       ├── parquet_storage.py
│       └── timescale_storage.py
│
├── analysis/                # 분석 레이어
│   ├── indicators/          # 기술적 지표 플러그인
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── classic.py       # MA, RSI, MACD 등
│   │   ├── smc.py           # Smart Money Concepts
│   │   ├── supply_demand.py # Supply/Demand Zones
│   │   └── custom/          # 트레이딩뷰 커스텀 지표
│   │
│   ├── strategies/          # 전략 플러그인
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── quant_screener.py
│   │   └── swing_screener.py
│   │
│   └── ml/                  # ML 모델 플러그인
│       ├── __init__.py
│       ├── base.py
│       ├── pattern_recognition.py
│       └── genetic_optimizer.py
│
├── decision/                # 의사결정 레이어
│   ├── engines/             # 결정 엔진
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── rule_engine.py
│   │   ├── ensemble.py
│   │   └── genetic_engine.py
│   │
│   └── experts/             # LLM 전문가 시스템
│       ├── __init__.py
│       ├── base.py
│       ├── chart_analyst.py
│       └── fundamental_analyst.py
│
├── alerts/                  # 알람 시스템
│   ├── __init__.py
│   ├── base.py
│   ├── telegram_alert.py
│   └── discord_alert.py
│
├── config/                  # 설정 파일
│   ├── default.yaml
│   ├── data_sources.yaml
│   ├── indicators.yaml
│   └── strategies.yaml
│
├── tests/                   # 테스트
├── scripts/                 # 유틸리티 스크립트
├── main.py                  # 진입점
└── requirements.txt
```

## 확장 방법

### 새 데이터 소스 추가
```python
from data.sources.base import DataSource

@register_source("my_source")
class MyDataSource(DataSource):
    def fetch_ohlcv(self, symbol, start, end):
        # 구현
        pass
```

### 새 인디케이터 추가
```python
from analysis.indicators.base import Indicator

@register_indicator("my_indicator")
class MyIndicator(Indicator):
    def calculate(self, df):
        # 구현
        return signals
```

### 새 전략 추가
```python
from analysis.strategies.base import Strategy

@register_strategy("my_strategy")
class MyStrategy(Strategy):
    def screen(self, universe):
        # 구현
        return candidates
```

## 빠른 시작

### 1. 설치
```bash
cd trading-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 설정
```bash
# 환경변수 설정 (선택적)
export FMP_API_KEY="your_key"  # Financial Modeling Prep
export TELEGRAM_BOT_TOKEN="your_token"  # 알람용
```

### 3. 실행
```bash
# 시스템 테스트
python main.py test

# 나스닥 스크리닝
python main.py screen --market nasdaq

# 특정 종목 스크리닝
python main.py screen --symbols AAPL MSFT NVDA

# 한국 주식 스크리닝
python main.py screen --market kospi

# 등록된 플러그인 확인
python main.py plugins
```

### 4. Python에서 직접 사용
```python
from data.sources import YFinanceSource
from analysis.indicators import RSIIndicator, SMCIndicator
from analysis.strategies import QuantScreener
from core.interfaces import Symbol, Market, Timeframe
from datetime import datetime, timedelta

# 데이터 가져오기
source = YFinanceSource()
df = source.fetch_ohlcv(
    "AAPL",
    Timeframe.D1,
    datetime.now() - timedelta(days=365),
    datetime.now()
)

# 지표 계산
rsi = RSIIndicator(period=14)
df = rsi.calculate(df)

smc = SMCIndicator(swing_length=10)
df = smc.calculate(df)

# 주요 레벨 확인
levels = smc.get_key_levels()
print(f"Swing Highs: {levels['swing_highs']}")
print(f"Order Blocks: {levels['order_block_highs']}")
```

## 확장 로드맵

### Phase 1 (현재): 기본 인프라 ✅
- [x] 플러그인 아키텍처
- [x] 데이터 소스 (yfinance, KRX, Binance)
- [x] 저장소 (SQLite, Parquet)
- [x] 기본 지표 (MA, RSI, MACD, Bollinger, ATR)
- [x] SMC 지표 (BOS, CHoCH, Order Block, FVG)
- [x] Supply/Demand Zone
- [x] 퀀트 스크리너
- [x] 스윙 스크리너

### Phase 2: 고도화 (예정)
- [ ] 백테스팅 프레임워크
- [ ] 유전자 알고리즘 최적화
- [ ] LLM 전문가 시스템 (차트 분석, 펀더멘털 분석)
- [ ] 알람 시스템 (Telegram, Discord)
- [ ] 웹 대시보드 (Streamlit)

### Phase 3: ML/AI (예정)
- [ ] 차트 패턴 인식 (CNN)
- [ ] 시계열 예측 (LSTM/Transformer)
- [ ] 강화학습 기반 전략

## 트레이딩뷰 인디케이터 통합

트레이딩뷰 Pine Script 인디케이터를 Python으로 포팅하여 사용:

```python
from analysis.indicators.base import Indicator
from core.registry import register

@register("indicator", "my_tv_indicator")
class MyTradingViewIndicator(Indicator):
    """트레이딩뷰에서 포팅한 커스텀 인디케이터"""

    name = "my_tv_indicator"

    default_params = {
        "length": 14,
        "mult": 2.0,
    }

    def calculate(self, df):
        # Pine Script 로직을 Python으로 변환
        # ...
        return df
```

## 라이선스

MIT License
