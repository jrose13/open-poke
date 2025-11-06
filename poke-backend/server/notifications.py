from __future__ import annotations

from typing import Dict, List

from fastapi import WebSocket


class EventNotifier:
    """Tracks websocket subscribers per user and pushes JSON events."""

    def __init__(self) -> None:
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if not connections:
            return
        try:
            connections.remove(websocket)
        except ValueError:
            pass
        if not connections:
            self._connections.pop(user_id, None)

    async def broadcast(self, user_id: str, payload: dict) -> None:
        connections = list(self._connections.get(user_id, []))
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(user_id, websocket)



