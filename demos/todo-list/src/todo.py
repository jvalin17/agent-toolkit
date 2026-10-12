"""In-memory todo list."""

from __future__ import annotations

from typing import Dict, List


class TodoList:
    def __init__(self) -> None:
        self._items: Dict[int, Dict] = {}
        self._next_id = 1

    def add(self, title: str) -> int:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("title must not be blank")
        item_id = self._next_id
        self._next_id += 1
        self._items[item_id] = {"id": item_id, "title": cleaned, "done": False}
        return item_id

    def list_items(self) -> List[Dict]:
        return [dict(item) for item_id, item in sorted(self._items.items())]

    def complete(self, item_id: int) -> bool:
        item = self._items.get(item_id)
        if item is None:
            return False
        item["done"] = True
        return True

    def remove(self, item_id: int) -> bool:
        if item_id not in self._items:
            return False
        del self._items[item_id]
        return True
