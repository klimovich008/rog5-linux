#!/usr/bin/env python3
"""Exhaustive lock-order model for CCF orphan reparenting and runtime PM."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Operation:
    action: str
    lock: str = ""


@dataclass(frozen=True)
class State:
    pcs: tuple[int, ...]
    owners: tuple[int, ...]


LOCKS = ("prepare_lock", "pm_transition", "rpm_list_lock")
LOCK_INDEX = {name: index for index, name in enumerate(LOCKS)}


def acquire(lock: str) -> Operation:
    return Operation("acquire", lock)


def release(lock: str) -> Operation:
    return Operation("release", lock)


WORK = Operation("work")


def explore(threads: tuple[tuple[Operation, ...], ...]) -> tuple[int, int, int]:
    initial = State((0,) * len(threads), (-1,) * len(LOCKS))
    queue = deque([initial])
    visited = {initial}
    complete = deadlocks = leaks = 0

    while queue:
        state = queue.popleft()
        done = all(pc == len(threads[index]) for index, pc in enumerate(state.pcs))
        if done:
            if all(owner == -1 for owner in state.owners):
                complete += 1
            else:
                leaks += 1
            continue

        successors: list[State] = []
        for thread_index, operations in enumerate(threads):
            pc = state.pcs[thread_index]
            if pc == len(operations):
                continue

            operation = operations[pc]
            owners = list(state.owners)
            if operation.action == "acquire":
                lock_index = LOCK_INDEX[operation.lock]
                if owners[lock_index] != -1:
                    continue
                owners[lock_index] = thread_index
            elif operation.action == "release":
                lock_index = LOCK_INDEX[operation.lock]
                if owners[lock_index] != thread_index:
                    raise AssertionError("model releases a lock it does not own")
                owners[lock_index] = -1

            pcs = list(state.pcs)
            pcs[thread_index] += 1
            successors.append(State(tuple(pcs), tuple(owners)))

        if not successors:
            deadlocks += 1
            continue

        for successor in successors:
            if successor not in visited:
                visited.add(successor)
                queue.append(successor)

    return complete, deadlocks, leaks


RUNTIME_CALLBACK = (
    acquire("pm_transition"),
    acquire("prepare_lock"),
    WORK,
    release("prepare_lock"),
    release("pm_transition"),
)

OLD_ORPHAN_SCAN = (
    acquire("prepare_lock"),
    acquire("pm_transition"),
    WORK,
    release("pm_transition"),
    release("prepare_lock"),
)

CANDIDATE_ORPHAN_SCAN = (
    acquire("rpm_list_lock"),
    acquire("pm_transition"),
    release("pm_transition"),
    acquire("prepare_lock"),
    WORK,
    release("prepare_lock"),
    acquire("pm_transition"),
    release("pm_transition"),
    release("rpm_list_lock"),
)

PUT_BEFORE_UNLOCK = (
    acquire("rpm_list_lock"),
    acquire("pm_transition"),
    release("pm_transition"),
    acquire("prepare_lock"),
    WORK,
    acquire("pm_transition"),
    release("pm_transition"),
    release("prepare_lock"),
    release("rpm_list_lock"),
)

MISSING_PUT_ALL = CANDIDATE_ORPHAN_SCAN[:-3]


def assert_deadlock(name: str, registration: tuple[Operation, ...]) -> None:
    complete, deadlocks, _ = explore((registration, RUNTIME_CALLBACK))
    assert complete > 0, f"{name}: no completing schedule exists"
    assert deadlocks > 0, f"{name}: expected ABBA deadlock is unreachable"


def assert_safe(name: str, registration: tuple[Operation, ...]) -> None:
    complete, deadlocks, leaks = explore((registration, RUNTIME_CALLBACK))
    assert complete > 0, f"{name}: no completing schedule exists"
    assert deadlocks == 0, f"{name}: ABBA deadlock remains reachable"
    assert leaks == 0, f"{name}: terminal lock/reference leak remains"


assert_deadlock("current __clk_core_init", OLD_ORPHAN_SCAN)
assert_deadlock("get-all below prepare_lock mutation", OLD_ORPHAN_SCAN)
assert_deadlock("put-all before prepare_unlock mutation", PUT_BEFORE_UNLOCK)
assert_safe("candidate __clk_core_init", CANDIDATE_ORPHAN_SCAN)
assert_safe("candidate of_clk_add_provider", CANDIDATE_ORPHAN_SCAN)
assert_safe("candidate of_clk_add_hw_provider", CANDIDATE_ORPHAN_SCAN)

_, _, missing_put_leaks = explore((MISSING_PUT_ALL, RUNTIME_CALLBACK))
assert missing_put_leaks > 0, "missing put-all mutation did not leak its list lock"

print(
    "PASS exhaustive CCF model finds the old/mutated ABBA cycles and "
    "no candidate deadlock or terminal lock leak"
)
