"""
Plugin Registry - 플러그인 등록 및 관리 시스템

데코레이터 기반으로 새 플러그인을 쉽게 등록할 수 있습니다.
"""
from typing import Any, Callable, Dict, List, Optional, Type
from functools import wraps
import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)


class Registry:
    """
    싱글톤 플러그인 레지스트리

    사용법:
        # 등록
        @Registry.register("source", "yfinance")
        class YFinanceSource(DataSource):
            pass

        # 조회
        source_cls = Registry.get("source", "yfinance")
        source = source_cls()
    """

    _instance = None
    _registries: Dict[str, Dict[str, Type]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._registries = {
                "source": {},      # 데이터 소스
                "storage": {},     # 저장소
                "indicator": {},   # 인디케이터
                "strategy": {},    # 전략
                "engine": {},      # 결정 엔진
                "expert": {},      # LLM 전문가
                "alert": {},       # 알람 채널
            }
        return cls._instance

    @classmethod
    def register(cls, category: str, name: str) -> Callable:
        """
        플러그인 등록 데코레이터

        Args:
            category: 플러그인 카테고리 (source, indicator 등)
            name: 플러그인 고유 이름

        Example:
            @Registry.register("indicator", "rsi")
            class RSIIndicator(Indicator):
                pass
        """
        def decorator(plugin_cls: Type) -> Type:
            registry = cls()
            if category not in registry._registries:
                registry._registries[category] = {}

            if name in registry._registries[category]:
                logger.warning(
                    f"Plugin '{name}' in '{category}' is being overwritten"
                )

            registry._registries[category][name] = plugin_cls
            plugin_cls._registry_name = name
            plugin_cls._registry_category = category

            logger.debug(f"Registered {category}/{name}: {plugin_cls.__name__}")
            return plugin_cls

        return decorator

    @classmethod
    def get(cls, category: str, name: str) -> Optional[Type]:
        """플러그인 클래스 조회"""
        registry = cls()
        return registry._registries.get(category, {}).get(name)

    @classmethod
    def get_instance(
        cls,
        category: str,
        name: str,
        **kwargs,
    ) -> Optional[Any]:
        """플러그인 인스턴스 생성 및 반환"""
        plugin_cls = cls.get(category, name)
        if plugin_cls:
            return plugin_cls(**kwargs)
        return None

    @classmethod
    def list_plugins(cls, category: Optional[str] = None) -> Dict[str, List[str]]:
        """등록된 플러그인 목록 조회"""
        registry = cls()
        if category:
            return {category: list(registry._registries.get(category, {}).keys())}
        return {cat: list(plugins.keys()) for cat, plugins in registry._registries.items()}

    @classmethod
    def list_category(cls, category: str) -> List[str]:
        """특정 카테고리의 플러그인 이름 목록"""
        registry = cls()
        return list(registry._registries.get(category, {}).keys())

    @classmethod
    def discover_plugins(cls, package_name: str):
        """
        패키지 내 플러그인 자동 발견 및 로드

        Args:
            package_name: 검색할 패키지 (예: "data.sources")
        """
        try:
            package = importlib.import_module(package_name)
            for _, module_name, _ in pkgutil.iter_modules(package.__path__):
                full_name = f"{package_name}.{module_name}"
                try:
                    importlib.import_module(full_name)
                    logger.debug(f"Loaded module: {full_name}")
                except Exception as e:
                    logger.error(f"Failed to load {full_name}: {e}")
        except Exception as e:
            logger.error(f"Failed to discover plugins in {package_name}: {e}")


# 편의를 위한 함수형 인터페이스
def register(category: str, name: str) -> Callable:
    """Registry.register의 편의 함수"""
    return Registry.register(category, name)


def get_plugin(category: str, name: str, **kwargs) -> Optional[Any]:
    """플러그인 인스턴스 가져오기"""
    return Registry.get_instance(category, name, **kwargs)


def list_plugins(category: Optional[str] = None) -> Dict[str, List[str]]:
    """등록된 플러그인 목록"""
    return Registry.list_plugins(category)


# ============================================================================
# Configuration-based Plugin Factory
# ============================================================================

class PluginFactory:
    """
    설정 기반 플러그인 팩토리

    YAML/JSON 설정에서 플러그인 인스턴스를 생성합니다.
    """

    @staticmethod
    def create_from_config(config: Dict) -> Any:
        """
        설정에서 플러그인 생성

        Config format:
            {
                "type": "indicator",
                "name": "rsi",
                "params": {
                    "period": 14
                }
            }
        """
        category = config.get("type")
        name = config.get("name")
        params = config.get("params", {})

        if not category or not name:
            raise ValueError("Config must have 'type' and 'name'")

        plugin = Registry.get_instance(category, name, **params)
        if not plugin:
            raise ValueError(f"Plugin not found: {category}/{name}")

        return plugin

    @staticmethod
    def create_many_from_config(configs: List[Dict]) -> List[Any]:
        """여러 플러그인 일괄 생성"""
        return [PluginFactory.create_from_config(c) for c in configs]


# ============================================================================
# Plugin Metadata
# ============================================================================

class PluginInfo:
    """플러그인 메타데이터"""

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
        dependencies: List[str] = None,
    ):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.dependencies = dependencies or []

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
        }


def plugin_info(**kwargs) -> Callable:
    """
    플러그인 메타데이터 데코레이터

    Example:
        @plugin_info(
            name="RSI Indicator",
            version="1.0.0",
            description="Relative Strength Index"
        )
        @register("indicator", "rsi")
        class RSIIndicator(Indicator):
            pass
    """
    def decorator(cls: Type) -> Type:
        cls._plugin_info = PluginInfo(**kwargs)
        return cls
    return decorator
