"""Thin HTTP client for the MemDB API.

All methods raise on non-2xx responses unless the caller handles 404 specially.
"""

from __future__ import annotations

from typing import Any

import requests


class MemDBError(Exception):
    """Raised when MemDB returns a non-2xx response."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"MemDB {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class MemDBNotFoundError(MemDBError):
    """Raised specifically for 404 responses."""


class MemDBClient:
    """Thin wrapper over the MemDB HTTP API.

    Args:
        base_url: MemDB base URL, e.g. ``http://localhost:8080``.
        service_secret: Value for ``X-Service-Secret`` header. Pass empty
            string when ``AUTH_ENABLED=false`` (default MemDB config).
        timeout: Per-request HTTP timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        service_secret: str = "",
        timeout: int = 10,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        if service_secret:
            self._session.headers.update({"X-Service-Secret": service_secret})

    # ------------------------------------------------------------------
    # Phase 1 key-addressed operations
    # ------------------------------------------------------------------

    def add_with_key(
        self,
        user_id: str,
        cube_id: str,
        key: str,
        text: str,
    ) -> dict[str, Any]:
        """POST /product/add with mode=raw, async_mode=sync, key=<path>."""
        payload: dict[str, Any] = {
            "user_id": user_id,
            "writable_cube_ids": [cube_id],
            "messages": [{"role": "user", "content": text}],
            "mode": "raw",
            "async_mode": "sync",
            "key": key,
        }
        return self._post("/product/add", payload)

    def get_memory_by_key(
        self,
        cube_id: str,
        user_id: str,
        key: str,
    ) -> dict[str, Any] | None:
        """POST /product/get_memory_by_key — returns data dict or None on 404."""
        payload = {"cube_id": cube_id, "user_id": user_id, "key": key}
        try:
            resp = self._post("/product/get_memory_by_key", payload)
        except MemDBNotFoundError:
            return None
        return resp

    def list_memories_by_prefix(
        self,
        cube_id: str,
        user_id: str,
        prefix: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """POST /product/list_memories_by_prefix — returns list of MemoryKeyListItem."""
        payload = {
            "cube_id": cube_id,
            "user_id": user_id,
            "prefix": prefix,
            "limit": limit,
            "offset": offset,
        }
        result = self._post("/product/list_memories_by_prefix", payload)
        # data is the list directly
        data = result if isinstance(result, list) else []
        return data

    def update_memory(self, memory_id: str, memory: str) -> dict[str, Any]:
        """POST /product/update_memory."""
        payload = {"memory_id": memory_id, "memory": memory}
        return self._post("/product/update_memory", payload)

    def delete_memories(self, memory_ids: list[str], cube_id: str | None = None) -> dict[str, Any]:
        """POST /product/delete_memory."""
        payload: dict[str, Any] = {"memory_ids": memory_ids}
        if cube_id:
            payload["writable_cube_ids"] = [cube_id]
        return self._post("/product/delete_memory", payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        resp = self._session.post(url, json=payload, timeout=self._timeout)
        return self._handle(resp)

    def _handle(self, resp: requests.Response) -> Any:
        if resp.status_code == 404:
            body = self._safe_json(resp)
            msg = body.get("message", "not found") if isinstance(body, dict) else "not found"
            raise MemDBNotFoundError(404, msg)
        if not resp.ok:
            body = self._safe_json(resp)
            msg = body.get("message", resp.text) if isinstance(body, dict) else resp.text
            raise MemDBError(resp.status_code, msg)
        body = resp.json()
        # MemDB wraps responses: {"code": 200, "message": "ok", "data": ...}
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    @staticmethod
    def _safe_json(resp: requests.Response) -> Any:
        try:
            return resp.json()
        except Exception:
            return {}
