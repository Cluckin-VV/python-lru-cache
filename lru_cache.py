"""A fixed-capacity least-recently-used cache.

The hash table finds a node by key in average O(1) time.  The hand-written
doubly linked list stores recency order without sorting or scanning:
``head.next`` is the MRU node and ``tail.prev`` is the LRU node.
"""

from __future__ import annotations


class _Node:
    """One linked-list node; key=None is reserved for the two sentinels."""

    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: int | None, value: int | None) -> None:
        self.key = key
        self.value = value
        self.prev: _Node | None = None
        self.next: _Node | None = None


class LRUCache:
    """Map integer keys to integer values with least-recently-used eviction."""

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be greater than zero")

        self.capacity = capacity
        self._nodes: dict[int, _Node] = {}
        self._head = _Node(None, None)
        self._tail = _Node(None, None)
        self._head.next = self._tail
        self._tail.prev = self._head
        self._assert_invariants()

    def get(self, key: int) -> int:
        """Return a value and mark its node MRU, or return -1 when absent."""
        node = self._nodes.get(key)
        if node is None:
            return -1

        self._move_to_front(node)
        self._assert_invariants()
        # Real nodes always contain integer values.
        assert node.value is not None
        return node.value

    def put(self, key: int, value: int) -> None:
        """Insert or update ``key``, then evict the LRU node if necessary."""
        node = self._nodes.get(key)
        if node is not None:
            node.value = value
            self._move_to_front(node)
            self._assert_invariants()
            return

        node = _Node(key, value)
        self._nodes[key] = node
        self._add_after_head(node)

        if len(self._nodes) > self.capacity:
            self._evict_lru()

        self._assert_invariants()

    def keys_mru_to_lru(self) -> list[int]:
        """Return keys ordered from most to least recently used."""
        keys: list[int] = []
        node = self._head.next
        while node is not self._tail:
            assert node is not None
            assert node.key is not None
            keys.append(node.key)
            node = node.next
        return keys

    def _remove(self, node: _Node) -> None:
        """Unlink one real node in O(1) time and leave it detached."""
        if node is self._head or node is self._tail:
            raise ValueError("cannot remove a sentinel node")
        if node.prev is None or node.next is None:
            raise ValueError("cannot remove a detached node")

        previous = node.prev
        following = node.next
        previous.next = following
        following.prev = previous
        node.prev = None
        node.next = None

    def _add_after_head(self, node: _Node) -> None:
        """Insert a detached real node at the MRU end in O(1) time."""
        if node is self._head or node is self._tail:
            raise ValueError("cannot add a sentinel as a real node")
        if node.prev is not None or node.next is not None:
            raise ValueError("node must be detached before insertion")

        old_mru = self._head.next
        assert old_mru is not None
        node.prev = self._head
        node.next = old_mru
        self._head.next = node
        old_mru.prev = node

    def _move_to_front(self, node: _Node) -> None:
        """Move an existing real node to the MRU end in O(1) time."""
        if node.prev is self._head:
            return
        self._remove(node)
        self._add_after_head(node)

    def _evict_lru(self) -> None:
        """Remove the LRU node from both the list and dictionary in O(1)."""
        lru = self._tail.prev
        if lru is None or lru is self._head:
            raise RuntimeError("cannot evict from an empty cache")

        key = lru.key
        assert key is not None
        self._remove(lru)
        removed = self._nodes.pop(key)
        assert removed is lru

    def _assert_invariants(self) -> None:
        """Assert that the dictionary and both list directions agree exactly."""
        assert len(self._nodes) <= self.capacity
        assert self._head is not self._tail
        assert self._head.prev is None
        assert self._tail.next is None
        assert self._head.next is not None
        assert self._tail.prev is not None
        assert self._head not in self._nodes.values()
        assert self._tail not in self._nodes.values()

        forward_nodes: list[_Node] = []
        forward_ids: set[int] = set()
        keys: set[int] = set()
        previous = self._head
        node = self._head.next

        while node is not self._tail:
            assert node is not None, "forward chain ended before tail"
            node_id = id(node)
            assert node_id not in forward_ids, "cycle or duplicate node detected"
            forward_ids.add(node_id)
            assert node is not self._head
            assert node.prev is previous
            assert previous.next is node
            assert node.key is not None
            assert node.key not in keys, "duplicate key in linked list"
            keys.add(node.key)
            forward_nodes.append(node)
            previous = node
            node = node.next

        assert previous.next is self._tail
        assert self._tail.prev is previous

        reverse_nodes: list[_Node] = []
        reverse_ids: set[int] = set()
        following = self._tail
        node = self._tail.prev

        while node is not self._head:
            assert node is not None, "reverse chain ended before head"
            node_id = id(node)
            assert node_id not in reverse_ids, "reverse cycle detected"
            reverse_ids.add(node_id)
            assert node is not self._tail
            assert node.next is following
            assert following.prev is node
            reverse_nodes.append(node)
            following = node
            node = node.prev

        assert following.prev is self._head
        assert self._head.next is following
        assert forward_nodes == list(reversed(reverse_nodes))
        assert len(forward_nodes) == len(self._nodes)
        assert keys == set(self._nodes)

        linked_nodes = set(forward_nodes)
        for key, mapped_node in self._nodes.items():
            assert mapped_node in linked_nodes
            assert mapped_node.key == key
