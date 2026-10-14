# 手写固定容量 LRU Cache

这是一个 Python 3.11+ 标准库实现。它不使用 `OrderedDict`、`functools.lru_cache`、时间戳排序、`list.index`、`min` 扫描或定期全表整理，核心结构严格采用：

```text
dict[key] -> node

head <-> MRU node <-> ... <-> LRU node <-> tail
```

## LRU 语义

LRU（Least Recently Used）缓存保留最近访问过的条目。当新键令条目数超过固定容量时，它精确淘汰最久未使用的键。

- `get(key)`：缺失返回 `-1`；命中返回值并把该节点刷新为 MRU。
- `put(key, value)`：新键创建节点；旧键原地更新并刷新为 MRU。
- `head.next`：MRU。
- `tail.prev`：LRU。

## 为什么只用 dict 或 list 都不够

只用 `dict` 可以平均 O(1) 定位 key，却不能直接表达并不断更新精确的最近使用顺序。只用普通 `list` 可以保存顺序，但按 key 查找或删除任意节点需要 O(n) 扫描；在头部插入还会移动元素。

`dict + 双向链表` 同时解决两件事：字典直接定位节点，链表用固定数量的指针改写完成刷新和淘汰。

## 为什么必须是双向链表

命中节点可能位于链表中间。已知该节点时，双向链表可通过 `prev` 和 `next` 在 O(1) 时间拆除它；单向链表仍需从头寻找前驱，最坏 O(n)。

## 哨兵节点解决了什么

永久存在的 `head`、`tail` 不承载业务键值。空表、单节点表、删除首尾节点都使用相同指针公式，减少空指针和边界分支。哨兵绝不会进入字典，也不会被当成真实节点淘汰。

## 复杂度

- 核心 `get`：平均 O(1)。
- 核心 `put`：平均 O(1)。
- `keys_mru_to_lru`：输出 n 个键，O(n)。
- 缓存常驻空间：O(capacity)。

这里的“平均”来自 Python `dict` 的平均 O(1) 哈希操作，不是最坏情况保证。为满足本任务的证明要求，当前实现每次修改后还执行 O(n) 的完整结构审计，因此调试验收路径的端到端修改操作是 O(n)；核心数据结构为何仍是平均 O(1)，以及两者为何不能混为一谈，见 [complexity-proof.md](complexity-proof.md)。指针边界案例见 [pointer-cases.md](pointer-cases.md)。

## 运行测试

```powershell
python -m unittest -v
```

测试共 18 项 LRU 专项用例，覆盖非法容量、空缓存、经典容量 2 序列、命中刷新、旧键更新、容量 1、重复访问、淘汰与重新插入、MRU→LRU 顺序、1000 次连续操作、不变量检查、双向遍历和哨兵安全。

## 为什么测试通过不等于生产级可靠

这些确定性单元测试能证明列出的语义与结构不变量在覆盖场景中成立，但不能自动证明所有输入与运行环境都可靠。生产缓存还需根据用途处理线程安全、异步并发、容量按条目还是按字节计算、命中率与淘汰指标、故障恢复、序列化、值对象可变性、进程间共享、压力下延迟和恶意哈希碰撞等问题。本实现也没有 TTL、持久化或分布式一致性能力。

## 与 Redis 近似 LRU 的差别

本实现维护全部条目的精确全序，每次命中都移动实际节点，淘汰的一定是全缓存精确 LRU。Redis 面向服务端内存与吞吐权衡，其 LRU 淘汰会随机采样少量 key，并从候选中选择更久未访问者；候选池让结果更接近精确 LRU，但仍可能不淘汰全局最旧 key。Redis 还由内存上限与可配置淘汰策略驱动，可选择仅考虑带过期时间的 key 或其他策略。参见 [Redis 官方 Key eviction 文档](https://redis.io/docs/latest/develop/reference/eviction/)。

## 文件

- `lru_cache.py`：实现与结构不变量。
- `test_lru_cache.py`：18 项 `unittest` 测试。
- `pointer-cases.md`：空表、刷新、更新和淘汰的指针推演。
- `complexity-proof.md`：不用跑分的复杂度证明。

