"""Sistema de eventos publish/subscribe do LexProof."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Generic, TypeVar

logger = logging.getLogger(__name__)

EventDataType = TypeVar("EventDataType")


class _Subscription(Generic[EventDataType]):
    """Armazena um callback inscrito em um tipo de evento."""

    __slots__ = ("callback", "once")

    def __init__(self, callback: Callable[[EventDataType], Any], once: bool = False) -> None:
        self.callback = callback
        self.once = once


class EventBus:
    """Sistema de publicação e inscrição de eventos.

    Thread-safe: todas as operações são protegidas por um lock.
    Permite inscrição genérica por tipo de evento com callbacks tipados.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._subscribers: dict[type, list[_Subscription[Any]]] = {}
        self._history: list[tuple[type, Any]] = []

    def subscribe(
        self,
        event_type: type[EventDataType],
        callback: Callable[[EventDataType], Any],
        *,
        once: bool = False,
    ) -> None:
        """Inscreve um callback para um tipo de evento.

        Args:
            event_type: Tipo do evento a ser escutado.
            callback: Função chamada quando o evento for emitido.
            once: Se True, a inscrição é removida após a primeira chamada.
        """
        sub = _Subscription(callback, once=once)
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(sub)
        logger.debug(
            "Inscrito em %s: %s (once=%s)",
            event_type.__name__,
            callback.__qualname__,
            once,
        )

    def unsubscribe(
        self,
        event_type: type[EventDataType],
        callback: Callable[[EventDataType], Any],
    ) -> bool:
        """Remove uma inscrição específica.

        Args:
            event_type: Tipo do evento.
            callback: Callback a ser removido.

        Returns:
            True se o callback foi encontrado e removido, False caso contrário.
        """
        with self._lock:
            subs = self._subscribers.get(event_type)
            if subs is None:
                return False
            for i, sub in enumerate(subs):
                if sub.callback is callback:
                    subs.pop(i)
                    logger.debug(
                        "Removido de %s: %s",
                        event_type.__name__,
                        callback.__qualname__,
                    )
                    return True
        return False

    def emit(self, event_type: type[EventDataType], data: EventDataType) -> None:
        """Emite um evento para todos os inscritos.

        Args:
            event_type: Tipo do evento emitido.
            data: Dados do evento.
        """
        with self._lock:
            self._history.append((event_type, data))
            subs = list(self._subscribers.get(event_type, []))

        to_remove: list[tuple[type, _Subscription[Any]]] = []
        for sub in subs:
            try:
                sub.callback(data)
            except Exception:
                logger.exception(
                    "Erro ao executar callback %s para evento %s",
                    sub.callback.__qualname__,
                    event_type.__name__,
                )
            if sub.once:
                to_remove.append((event_type, sub))

        if to_remove:
            with self._lock:
                for evt_type, sub in to_remove:
                    subs_list = self._subscribers.get(evt_type, [])
                    try:
                        subs_list.remove(sub)
                    except ValueError:
                        pass

    def clear(self) -> None:
        """Remove todas as inscrições e o histórico."""
        with self._lock:
            self._subscribers.clear()
            self._history.clear()
        logger.debug("EventBus limpo: todas as inscrições removidas")

    def get_history(self) -> list[tuple[type, Any]]:
        """Retorna cópia do histórico de eventos emitidos.

        Returns:
            Lista de tuplas (tipo_do_evento, dados).
        """
        with self._lock:
            return list(self._history)

    def subscriber_count(self, event_type: type | None = None) -> int:
        """Conta inscritos para um tipo de evento ou todos.

        Args:
            event_type: Se fornecido, conta apenas inscritos deste tipo.

        Returns:
            Número de inscritos.
        """
        with self._lock:
            if event_type is not None:
                return len(self._subscribers.get(event_type, []))
            return sum(len(subs) for subs in self._subscribers.values())
