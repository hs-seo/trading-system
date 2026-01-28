"""
Event System - 이벤트 기반 아키텍처

컴포넌트 간 느슨한 결합을 위한 Pub/Sub 시스템입니다.
새로운 기능 추가 시 기존 코드 수정 없이 이벤트 구독만으로 통합 가능합니다.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(Enum):
    """시스템 이벤트 타입"""

    # 데이터 이벤트
    DATA_FETCHED = "data.fetched"
    DATA_UPDATED = "data.updated"
    DATA_ERROR = "data.error"

    # 분석 이벤트
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    INDICATOR_CALCULATED = "indicator.calculated"

    # 신호 이벤트
    SIGNAL_GENERATED = "signal.generated"
    SIGNAL_CONFIRMED = "signal.confirmed"
    SIGNAL_EXPIRED = "signal.expired"

    # 스크리닝 이벤트
    SCREENING_STARTED = "screening.started"
    SCREENING_COMPLETED = "screening.completed"
    CANDIDATE_FOUND = "candidate.found"

    # 결정 이벤트
    DECISION_MADE = "decision.made"
    EXPERT_OPINION = "expert.opinion"

    # 시스템 이벤트
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    ERROR = "system.error"
    CONFIG_CHANGED = "config.changed"

    # 알람 이벤트
    ALERT_SENT = "alert.sent"
    ALERT_FAILED = "alert.failed"


@dataclass
class Event:
    """이벤트 객체"""
    type: EventType
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        return f"Event({self.type.value}, source={self.source}, ts={self.timestamp})"


# 이벤트 핸들러 타입
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]  # coroutine


class EventBus:
    """
    이벤트 버스 - 중앙 이벤트 관리

    동기/비동기 핸들러 모두 지원합니다.

    사용법:
        bus = EventBus()

        # 구독
        @bus.subscribe(EventType.SIGNAL_GENERATED)
        def on_signal(event):
            print(f"New signal: {event.data}")

        # 발행
        bus.publish(Event(
            type=EventType.SIGNAL_GENERATED,
            data=signal,
            source="rsi_indicator"
        ))
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
            cls._instance._async_handlers: Dict[EventType, List[AsyncEventHandler]] = defaultdict(list)
            cls._instance._history: List[Event] = []
            cls._instance._max_history = 1000
        return cls._instance

    def subscribe(
        self,
        event_type: EventType,
        handler: Optional[EventHandler] = None,
    ) -> Callable:
        """
        이벤트 구독 (데코레이터 또는 직접 호출)

        Example:
            # 데코레이터로 사용
            @bus.subscribe(EventType.SIGNAL_GENERATED)
            def handler(event):
                pass

            # 직접 호출
            bus.subscribe(EventType.SIGNAL_GENERATED, handler)
        """
        def decorator(fn: EventHandler) -> EventHandler:
            if asyncio.iscoroutinefunction(fn):
                self._async_handlers[event_type].append(fn)
            else:
                self._handlers[event_type].append(fn)
            logger.debug(f"Subscribed {fn.__name__} to {event_type.value}")
            return fn

        if handler:
            return decorator(handler)
        return decorator

    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """구독 해제"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
        if handler in self._async_handlers[event_type]:
            self._async_handlers[event_type].remove(handler)

    def publish(self, event: Event):
        """
        이벤트 발행 (동기)

        동기 핸들러만 실행합니다.
        비동기 핸들러는 publish_async를 사용하세요.
        """
        self._add_to_history(event)
        logger.debug(f"Publishing event: {event}")

        for handler in self._handlers[event.type]:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler {handler.__name__} failed: {e}")
                self.publish(Event(
                    type=EventType.ERROR,
                    data={"error": str(e), "handler": handler.__name__},
                    source="event_bus"
                ))

    async def publish_async(self, event: Event):
        """
        이벤트 발행 (비동기)

        동기/비동기 핸들러 모두 실행합니다.
        """
        self._add_to_history(event)
        logger.debug(f"Publishing async event: {event}")

        # 동기 핸들러 실행
        for handler in self._handlers[event.type]:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Sync handler {handler.__name__} failed: {e}")

        # 비동기 핸들러 병렬 실행
        tasks = []
        for handler in self._async_handlers[event.type]:
            tasks.append(self._run_async_handler(handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_async_handler(self, handler: AsyncEventHandler, event: Event):
        """비동기 핸들러 실행"""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Async handler {handler.__name__} failed: {e}")

    def _add_to_history(self, event: Event):
        """이벤트 히스토리 저장"""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[Event]:
        """이벤트 히스토리 조회"""
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def clear_history(self):
        """히스토리 초기화"""
        self._history = []


# 전역 이벤트 버스 인스턴스
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """전역 이벤트 버스 가져오기"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# 편의 함수들
def publish(event: Event):
    """이벤트 발행 (편의 함수)"""
    get_event_bus().publish(event)


def subscribe(event_type: EventType):
    """이벤트 구독 데코레이터 (편의 함수)"""
    return get_event_bus().subscribe(event_type)


# ============================================================================
# Event-Driven Mixins
# ============================================================================

class EventEmitter:
    """
    이벤트 발생 믹스인

    플러그인 클래스에서 상속받아 이벤트 발행 기능 추가
    """

    def emit(self, event_type: EventType, data: Any, **kwargs):
        """이벤트 발행"""
        event = Event(
            type=event_type,
            data=data,
            source=getattr(self, 'name', self.__class__.__name__),
            **kwargs
        )
        get_event_bus().publish(event)

    async def emit_async(self, event_type: EventType, data: Any, **kwargs):
        """비동기 이벤트 발행"""
        event = Event(
            type=event_type,
            data=data,
            source=getattr(self, 'name', self.__class__.__name__),
            **kwargs
        )
        await get_event_bus().publish_async(event)


class EventListener:
    """
    이벤트 리스너 믹스인

    플러그인 클래스에서 상속받아 이벤트 구독 기능 추가
    """

    _subscriptions: List[EventType] = []

    def start_listening(self):
        """구독 시작"""
        bus = get_event_bus()
        for event_type in self._subscriptions:
            handler_name = f"on_{event_type.name.lower()}"
            handler = getattr(self, handler_name, None)
            if handler:
                bus.subscribe(event_type, handler)

    def stop_listening(self):
        """구독 중지"""
        bus = get_event_bus()
        for event_type in self._subscriptions:
            handler_name = f"on_{event_type.name.lower()}"
            handler = getattr(self, handler_name, None)
            if handler:
                bus.unsubscribe(event_type, handler)


# ============================================================================
# Pre-built Event Handlers
# ============================================================================

class LoggingHandler:
    """모든 이벤트 로깅"""

    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level

    def handle(self, event: Event):
        logger.log(
            self.log_level,
            f"[{event.type.value}] {event.source}: {event.data}"
        )


class MetricsCollector:
    """이벤트 메트릭 수집"""

    def __init__(self):
        self.counts: Dict[EventType, int] = defaultdict(int)
        self.last_events: Dict[EventType, Event] = {}

    def handle(self, event: Event):
        self.counts[event.type] += 1
        self.last_events[event.type] = event

    def get_stats(self) -> Dict:
        return {
            "counts": {k.value: v for k, v in self.counts.items()},
            "last_events": {k.value: str(v) for k, v in self.last_events.items()},
        }
