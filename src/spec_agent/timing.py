"""轻量分阶段耗时观测。

设置 ``SPEC_AGENT_TIMING=1`` 后，会通过 ``spec_agent.timing`` logger 输出各阶段耗时。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from .config import get_settings

TIMING_LOGGER = logging.getLogger("spec_agent.timing")


def timing_enabled() -> bool:
    return get_settings().timing_enabled


@contextmanager
def phase(name: str) -> Iterator[None]:
    """记录一个同步阶段的耗时。"""
    if not timing_enabled():
        yield
        return

    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - started
        TIMING_LOGGER.info("%s took %.3fs", name, elapsed)


def log_phase(name: str, started: float) -> None:
    """记录已经结束的阶段耗时。"""
    if not timing_enabled():
        return
    TIMING_LOGGER.info("%s took %.3fs", name, time.perf_counter() - started)
