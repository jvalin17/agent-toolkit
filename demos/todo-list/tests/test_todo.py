"""In-memory todo list."""

import pytest

from todo import TodoList


def test_add_and_list():
    todos = TodoList()
    item_id = todos.add("Buy milk")
    assert item_id == 1
    assert todos.list_items() == [{"id": 1, "title": "Buy milk", "done": False}]


def test_complete():
    todos = TodoList()
    item_id = todos.add("Write tests")
    assert todos.complete(item_id) is True
    assert todos.list_items()[0]["done"] is True


def test_complete_missing_returns_false():
    todos = TodoList()
    assert todos.complete(99) is False


def test_remove():
    todos = TodoList()
    item_id = todos.add("Temp")
    assert todos.remove(item_id) is True
    assert todos.list_items() == []


def test_add_rejects_blank():
    todos = TodoList()
    with pytest.raises(ValueError):
        todos.add("   ")
