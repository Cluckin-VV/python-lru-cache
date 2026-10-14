import unittest
from unittest.mock import patch

from lru_cache import LRUCache


class LRUCacheTests(unittest.TestCase):
    def assert_consistent(self, cache: LRUCache) -> None:
        cache._assert_invariants()
        self.assertLessEqual(len(cache._nodes), cache.capacity)

    def test_capacity_zero_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            LRUCache(0)

    def test_negative_capacity_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            LRUCache(-1)

    def test_empty_cache_get_returns_minus_one(self) -> None:
        cache = LRUCache(2)
        self.assertEqual(cache.get(10), -1)
        self.assert_consistent(cache)

    def test_put_then_get_returns_value(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 100)
        self.assertEqual(cache.get(1), 100)
        self.assert_consistent(cache)

    def test_classic_capacity_two_sequence(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 1)
        cache.put(2, 2)
        self.assertEqual(cache.get(1), 1)
        cache.put(3, 3)
        self.assertEqual(cache.get(2), -1)
        cache.put(4, 4)
        self.assertEqual(cache.get(1), -1)
        self.assertEqual(cache.get(3), 3)
        self.assertEqual(cache.get(4), 4)
        self.assert_consistent(cache)

    def test_get_refreshes_recency(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 1)
        cache.put(2, 2)
        cache.get(1)
        cache.put(3, 3)
        self.assertEqual(cache.get(2), -1)
        self.assertEqual(cache.keys_mru_to_lru(), [3, 1])

    def test_updating_existing_key_changes_value(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(1, 99)
        self.assertEqual(cache.get(1), 99)
        self.assert_consistent(cache)

    def test_updating_existing_key_does_not_grow_cache(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        original_node = cache._nodes[1]
        cache.put(1, 20)
        self.assertEqual(len(cache._nodes), 1)
        self.assertIs(cache._nodes[1], original_node)
        self.assert_consistent(cache)

    def test_updating_existing_key_refreshes_recency(self) -> None:
        cache = LRUCache(3)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)
        cache.put(1, 11)
        self.assertEqual(cache.keys_mru_to_lru(), [1, 3, 2])
        self.assert_consistent(cache)

    def test_capacity_one_evicts_previous_key(self) -> None:
        cache = LRUCache(1)
        cache.put(1, 10)
        cache.put(2, 20)
        self.assertEqual(cache.get(1), -1)
        self.assertEqual(cache.get(2), 20)
        self.assertEqual(cache.keys_mru_to_lru(), [2])

    def test_repeated_get_does_not_duplicate_node(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        node = cache._nodes[1]
        for _ in range(25):
            self.assertEqual(cache.get(1), 10)
        self.assertEqual(cache.keys_mru_to_lru(), [1])
        self.assertEqual(len(cache._nodes), 1)
        self.assertIs(cache._nodes[1], node)
        self.assert_consistent(cache)

    def test_evicted_key_disappears_from_dict_and_list(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        evicted_node = cache._nodes[1]
        cache.put(2, 20)
        cache.put(3, 30)
        self.assertNotIn(1, cache._nodes)
        self.assertNotIn(1, cache.keys_mru_to_lru())
        self.assertIsNone(evicted_node.prev)
        self.assertIsNone(evicted_node.next)
        self.assert_consistent(cache)

    def test_evicted_key_can_be_reinserted(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)
        cache.put(1, 100)
        self.assertEqual(cache.get(1), 100)
        self.assertEqual(cache.get(2), -1)
        self.assertEqual(cache.keys_mru_to_lru(), [1, 3])
        self.assert_consistent(cache)

    def test_keys_mru_to_lru_reports_exact_order(self) -> None:
        cache = LRUCache(4)
        for key in (1, 2, 3, 4):
            cache.put(key, key * 10)
        cache.get(2)
        cache.get(1)
        self.assertEqual(cache.keys_mru_to_lru(), [1, 2, 4, 3])
        self.assert_consistent(cache)

    def test_one_thousand_operations_never_exceed_capacity(self) -> None:
        cache = LRUCache(7)
        for step in range(1_000):
            key = (step * 17) % 23
            if step % 3 == 0:
                cache.get(key)
            else:
                cache.put(key, step)
            self.assertLessEqual(len(cache._nodes), cache.capacity)
            self.assert_consistent(cache)

    def test_every_public_state_change_runs_invariant_check(self) -> None:
        cache = LRUCache(2)
        with patch.object(
            cache, "_assert_invariants", wraps=cache._assert_invariants
        ) as invariant_check:
            cache.put(1, 10)  # new-node insertion
            cache.put(1, 11)  # old-key update and refresh
            cache.put(2, 20)  # insertion without eviction
            cache.get(1)      # hit refresh
            cache.put(3, 30)  # insertion with eviction
            self.assertEqual(invariant_check.call_count, 5)

    def test_forward_and_reverse_traversals_are_inverses(self) -> None:
        cache = LRUCache(5)
        for key in (10, 20, 30, 40, 50):
            cache.put(key, key)
        cache.get(20)
        cache.put(60, 60)

        forward: list[int] = []
        node = cache._head.next
        while node is not cache._tail:
            self.assertIsNotNone(node)
            forward.append(node.key)
            node = node.next

        reverse: list[int] = []
        node = cache._tail.prev
        while node is not cache._head:
            self.assertIsNotNone(node)
            reverse.append(node.key)
            node = node.prev

        self.assertEqual(forward, list(reversed(reverse)))
        self.assertEqual(forward, cache.keys_mru_to_lru())
        self.assert_consistent(cache)

    def test_sentinels_are_never_real_cache_nodes(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        self.assertNotIn(cache._head, cache._nodes.values())
        self.assertNotIn(cache._tail, cache._nodes.values())
        self.assertIsNone(cache._head.prev)
        self.assertIsNone(cache._tail.next)
        self.assert_consistent(cache)


if __name__ == "__main__":
    unittest.main()
