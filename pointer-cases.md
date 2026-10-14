# 双向链表指针案例

## 约定

- `head` 与 `tail` 是永久哨兵，不承载缓存键值。
- `head.next` 是 MRU（最近使用）节点，`tail.prev` 是 LRU（最久未使用）节点。
- 空表始终为 `head <-> tail`。
- 真实节点只会处于两种状态之一：完整地连接在链表中，或 `prev is None and next is None`。

## 1. 空缓存插入首节点

插入前：

```text
head <-> tail
```

`_add_after_head(A)` 保存原 `head.next`（即 `tail`），再建立四条链接：

```text
head.next = A
A.prev = head
A.next = tail
tail.prev = A
```

插入后：

```text
head <-> A <-> tail
```

此时 `A` 同时是 MRU 与 LRU。

## 2. 在非空缓存插入 MRU

插入前：

```text
head <-> B <-> A <-> tail
          MRU       LRU
```

插入 `C` 后：

```text
head <-> C <-> B <-> A <-> tail
          MRU             LRU
```

只有 `head`、原 MRU `B` 与新节点 `C` 的相邻链接被修改，节点数多少不影响操作步数。

## 3. 将中间节点刷新为 MRU

刷新前：

```text
head <-> C <-> B <-> A <-> tail
```

对 `B` 先执行 `_remove(B)`：

```text
head <-> C <-> A <-> tail    B(prev=None, next=None)
```

再执行 `_add_after_head(B)`：

```text
head <-> B <-> C <-> A <-> tail
          MRU             LRU
```

字典仍指向同一个 `B` 对象；没有创建重复节点。

## 4. MRU 再次被访问

若节点的 `prev is head`，它已经是 MRU。`_move_to_front` 直接返回，不拆除也不重建：

```text
head <-> A <-> B <-> tail
          ^ 再次 get(A)，结构不变
```

## 5. 更新旧键

`put(A, new_value)` 修改原节点的 `value`，再把同一节点移到头部。字典长度与真实节点数均不增加：

```text
更新前: head <-> C <-> B <-> A(old) <-> tail
更新后: head <-> A(new) <-> C <-> B <-> tail
```

## 6. 淘汰 LRU

容量已满时插入新键，先把新节点放到 MRU 端，再取 `tail.prev`：

```text
超容时: head <-> D <-> C <-> B <-> A <-> tail
                                     ^ LRU
淘汰后: head <-> D <-> C <-> B <-> tail
```

`_evict_lru` 同时做两件事：把 `A` 从链表拆除，再用 `A.key` 从字典删除。被拆除节点的两个指针被清空，能暴露误复用，也避免它看起来仍属于链表。

## 7. 容量为 1

```text
put(1): head <-> 1 <-> tail
put(2): head <-> 2 <-> 1 <-> tail  (暂时超容)
evict : head <-> 2 <-> tail
```

哨兵让首节点、尾节点和唯一节点都走同一套链接逻辑，不需要为空表或单节点表编写特殊分支。

## 8. 不变量如何捕获指针错误

`_assert_invariants()` 同时正向与反向遍历，并检查：

1. 每一步 `node.prev.next is node` 且 `node.next.prev is node`；
2. 正向节点序列等于反向节点序列的逆序；
3. 不出现重复节点或重复 key；
4. 链表真实节点集合与字典值集合完全一致；
5. 字典 key 与其节点的 `node.key` 一致；
6. 哨兵不进入字典，且 `head.prev`、`tail.next` 始终为空。

因此，漏改任一方向链接、只删字典未删链表、重复挂载同一节点、错误淘汰哨兵等问题都会被检测到。
