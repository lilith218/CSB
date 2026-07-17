# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from config.benchmark import BenchmarkConfig
from config.benchmark import MonitorType
from monitors.perflock import PerfLock
from unittest.mock import patch


def test_monitor_list_order():
    with patch.object(PerfLock, "is_supported", return_value=True):
        monitors = {
            MonitorType.MPSTAT: [],
            MonitorType.PERF_LOCK: [],
            MonitorType.PERF: [],
        }
        # Note that the expectation is too strong, it will pass
        # because it matches the current implementation,
        # but it suffices to check if perf is listed before perf_lock
        expected = {
            MonitorType.PERF: [],
            MonitorType.PERF_LOCK: [],
            MonitorType.MPSTAT: [],
        }
        cfg = BenchmarkConfig(monitors=monitors)
        assert list(cfg.monitors.keys()) == list(expected.keys())


def test_monitor_missing_perf_order():
    with patch.object(PerfLock, "is_supported", return_value=True):
        monitors = {
            MonitorType.MPSTAT: [],
            MonitorType.PERF_LOCK: [],
        }
        expected = {
            MonitorType.PERF: [],
            MonitorType.PERF_LOCK: [],
            MonitorType.MPSTAT: [],
        }
        cfg = BenchmarkConfig(monitors=monitors)
        assert list(cfg.monitors.keys()) == list(expected.keys())
