"""
Config Loader - YAML/JSON 설정 로더

설정 파일로 시스템 동작을 제어합니다.
환경변수 치환, 기본값, 검증 지원.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """데이터 소스 설정"""
    name: str
    type: str  # yfinance, krx, binance, fmp
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageConfig:
    """저장소 설정"""
    type: str  # sqlite, parquet, hybrid
    path: str = "./data"
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndicatorConfig:
    """인디케이터 설정"""
    name: str
    type: str  # rsi, macd, smc, etc.
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyConfig:
    """전략 설정"""
    name: str
    type: str
    enabled: bool = True
    indicators: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertConfig:
    """알람 설정"""
    type: str  # telegram, discord, email
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """전체 설정"""
    # 기본 설정
    app_name: str = "TradingSystem"
    log_level: str = "INFO"
    debug: bool = False

    # 데이터 소스
    sources: List[SourceConfig] = field(default_factory=list)

    # 저장소
    storage: StorageConfig = field(default_factory=lambda: StorageConfig(type="sqlite"))

    # 인디케이터
    indicators: List[IndicatorConfig] = field(default_factory=list)

    # 전략
    strategies: List[StrategyConfig] = field(default_factory=list)

    # 알람
    alerts: List[AlertConfig] = field(default_factory=list)

    # 스케줄링
    schedule: Dict[str, Any] = field(default_factory=dict)

    # 사용자 정의 설정
    custom: Dict[str, Any] = field(default_factory=dict)


class ConfigLoader:
    """
    설정 로더

    기능:
    - YAML/JSON 파일 로드
    - 환경변수 치환 (${VAR_NAME} 또는 ${VAR_NAME:default})
    - 다중 파일 병합
    - 스키마 검증

    사용법:
        loader = ConfigLoader()
        config = loader.load("config/default.yaml")
    """

    ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')

    def __init__(self):
        self._config: Optional[Config] = None

    def load(self, config_path: Union[str, Path]) -> Config:
        """설정 파일 로드"""
        config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return Config()

        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML not installed. Run: pip install pyyaml")

        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        if raw_config is None:
            raw_config = {}

        # 환경변수 치환
        raw_config = self._substitute_env_vars(raw_config)

        # Config 객체로 변환
        self._config = self._parse_config(raw_config)

        logger.info(f"Loaded config from {config_path}")
        return self._config

    def load_multiple(self, *config_paths: Union[str, Path]) -> Config:
        """여러 설정 파일 병합 로드"""
        merged = {}

        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML not installed")

        for path in config_paths:
            path = Path(path)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                merged = self._deep_merge(merged, config)

        merged = self._substitute_env_vars(merged)
        self._config = self._parse_config(merged)
        return self._config

    def _substitute_env_vars(self, obj: Any) -> Any:
        """환경변수 치환"""
        if isinstance(obj, str):
            def replacer(match):
                var_name = match.group(1)
                default = match.group(2)
                value = os.environ.get(var_name, default)
                if value is None:
                    logger.warning(f"Environment variable {var_name} not set")
                    return match.group(0)
                return value

            return self.ENV_VAR_PATTERN.sub(replacer, obj)

        elif isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]

        return obj

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """딕셔너리 깊은 병합"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _parse_config(self, raw: Dict) -> Config:
        """딕셔너리를 Config 객체로 변환"""
        config = Config()

        # 기본 설정
        config.app_name = raw.get("app_name", config.app_name)
        config.log_level = raw.get("log_level", config.log_level)
        config.debug = raw.get("debug", config.debug)

        # 데이터 소스
        for source_dict in raw.get("sources", []):
            config.sources.append(SourceConfig(
                name=source_dict.get("name", ""),
                type=source_dict.get("type", ""),
                enabled=source_dict.get("enabled", True),
                params=source_dict.get("params", {}),
            ))

        # 저장소
        storage_dict = raw.get("storage", {})
        config.storage = StorageConfig(
            type=storage_dict.get("type", "sqlite"),
            path=storage_dict.get("path", "./data"),
            params=storage_dict.get("params", {}),
        )

        # 인디케이터
        for ind_dict in raw.get("indicators", []):
            config.indicators.append(IndicatorConfig(
                name=ind_dict.get("name", ""),
                type=ind_dict.get("type", ""),
                enabled=ind_dict.get("enabled", True),
                params=ind_dict.get("params", {}),
            ))

        # 전략
        for strat_dict in raw.get("strategies", []):
            config.strategies.append(StrategyConfig(
                name=strat_dict.get("name", ""),
                type=strat_dict.get("type", ""),
                enabled=strat_dict.get("enabled", True),
                indicators=strat_dict.get("indicators", []),
                params=strat_dict.get("params", {}),
            ))

        # 알람
        for alert_dict in raw.get("alerts", []):
            config.alerts.append(AlertConfig(
                type=alert_dict.get("type", ""),
                enabled=alert_dict.get("enabled", True),
                params=alert_dict.get("params", {}),
            ))

        # 스케줄
        config.schedule = raw.get("schedule", {})

        # 사용자 정의
        config.custom = raw.get("custom", {})

        return config

    def get_config(self) -> Config:
        """현재 로드된 설정 반환"""
        if self._config is None:
            raise ValueError("Config not loaded. Call load() first.")
        return self._config


# 전역 설정 로더
_loader = ConfigLoader()


def load_config(config_path: Union[str, Path]) -> Config:
    """설정 로드 (편의 함수)"""
    return _loader.load(config_path)


def get_config() -> Config:
    """현재 설정 반환 (편의 함수)"""
    return _loader.get_config()


def load_config_from_env() -> Config:
    """환경변수에서 설정 경로 로드"""
    config_path = os.environ.get("TRADING_CONFIG", "config/default.yaml")
    return load_config(config_path)
