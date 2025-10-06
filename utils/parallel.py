"""提供批次處理與並行執行的工具函式。"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Iterable, List, Sequence, Tuple, TypeVar

import streamlit as st

T = TypeVar("T")


async def gather_with_concurrency(limit: int, *tasks: Awaitable[T]) -> List[T]:
    """限制並行數量的 gather。"""
    semaphore = asyncio.Semaphore(limit)

    async def _sem_task(task: Awaitable[T]) -> T:
        async with semaphore:
            return await task

    return await asyncio.gather(*[_sem_task(task) for task in tasks])


def run_async(coro: Awaitable[T]) -> T:
    """在同步環境執行協程（兼容 Streamlit）。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def run_agent_batch(
    coroutines: Sequence[Awaitable[T]],
    concurrency: int = 3,
    show_progress: bool = True,
    progress_label: str = "執行中"
) -> List[T]:
    """並行執行多個 Agent 任務並顯示進度。"""
    results: List[T] = []
    total = len(coroutines)
    progress = st.progress(0.0, text=progress_label) if show_progress else None

    for start in range(0, total, concurrency):
        chunk = coroutines[start : start + concurrency]
        chunk_results = await asyncio.gather(*chunk, return_exceptions=False)
        results.extend(chunk_results)
        if progress:
            progress.progress(min((len(results) / total), 1.0), text=progress_label)

    if progress:
        progress.empty()
    return results


__all__ = ["gather_with_concurrency", "run_async", "run_agent_batch"]
