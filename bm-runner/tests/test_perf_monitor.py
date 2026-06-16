# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.perf import FlameGraph
from monitors.perfstat import PerfStat
from config.env_config import UniversalConfig
from types import SimpleNamespace


def test_arm_spe_event_uses_env_period(monkeypatch):
    monkeypatch.setenv(FlameGraph.ARM_SPE_PERIOD_ENV_VAR_NAME, "20480")

    assert FlameGraph.arm_spe_event() == "arm_spe/jitter=1,period=20480/"


def test_arm_spe_event_uses_ten_times_sysfs_min_interval(monkeypatch, tmp_path):
    min_interval = tmp_path / "arm_spe_0" / "caps" / "min_interval"
    min_interval.parent.mkdir(parents=True)
    min_interval.write_text("1024")
    monkeypatch.delenv(FlameGraph.ARM_SPE_PERIOD_ENV_VAR_NAME, raising=False)
    monkeypatch.setattr(
        FlameGraph,
        "ARM_SPE_MIN_INTERVAL_GLOB",
        str(tmp_path / "arm_spe*" / "caps" / "min_interval"),
    )

    assert FlameGraph.arm_spe_event() == "arm_spe/jitter=1,period=10240/"


def test_perf_events_skip_arm_spe_when_sysfs_device_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(FlameGraph, "ARM_SPE_DEVICE_GLOB", str(tmp_path / "arm_spe*"))
    monkeypatch.setenv(FlameGraph.ARM_SPE_PERIOD_ENV_VAR_NAME, "not-an-int")

    assert FlameGraph.perf_events() == ["cycles"]
    assert FlameGraph.perf_record_cmd(["-a"]) == [
        "sudo",
        "perf",
        "record",
        "-g",
        "-F",
        "99",
        "-e",
        "cycles",
        "-a",
    ]


def test_perf_events_include_arm_spe_when_sysfs_device_has_type(monkeypatch, tmp_path):
    min_interval = tmp_path / "arm_spe_0" / "caps" / "min_interval"
    min_interval.parent.mkdir(parents=True)
    min_interval.write_text("1024")
    (tmp_path / "arm_spe_0" / "type").write_text("999")
    monkeypatch.delenv(FlameGraph.ARM_SPE_PERIOD_ENV_VAR_NAME, raising=False)
    monkeypatch.setenv(UniversalConfig.CSB_ARM_SPE, "true")
    monkeypatch.setattr(FlameGraph, "ARM_SPE_DEVICE_GLOB", str(tmp_path / "arm_spe*"))
    monkeypatch.setattr(
        FlameGraph,
        "ARM_SPE_MIN_INTERVAL_GLOB",
        str(tmp_path / "arm_spe*" / "caps" / "min_interval"),
    )

    assert FlameGraph.perf_events() == ["cycles", "arm_spe/jitter=1,period=10240/"]
    assert FlameGraph.perf_record_cmd(["-a"]) == [
        "sudo",
        "perf",
        "record",
        "-g",
        "-e",
        "cycles",
        "-e",
        "arm_spe/jitter=1,period=10240/",
        "-a",
    ]


def test_perf_stat_collects_counter_values_when_metric_values_are_empty(tmp_path):
    output = tmp_path / "perf-stat"
    output.write_text(
        "# started on Tue Jun 16 15:09:16 2026\n"
        "\n"
        "2038.59;msec;cpu-clock;2038592268;100.00;;\n"
        "676;;context-switches;2038592028;100.00;;\n"
        "23980289;;cache-misses;1686541168;82.00;;\n"
        "219;;cgroup-switches;2038577650;100.00;;\n"
    )

    monitor = PerfStat.__new__(PerfStat)
    monitor.name = "perf-stat"
    monitor.stat = SimpleNamespace(output_file_name=str(output))

    assert monitor.collect_results() == (
        "cpu-clock=2038.59;"
        "context-switches=676.0;"
        "cache-misses=23980289.0;"
        "cgroup-switches=219.0;"
    )


def test_perf_stat_falls_back_to_metric_value(tmp_path):
    output = tmp_path / "perf-stat"
    output.write_text(";;instructions;100;100.00;1.25;insn per cycle\n")

    monitor = PerfStat.__new__(PerfStat)
    monitor.name = "perf-stat"
    monitor.stat = SimpleNamespace(output_file_name=str(output))

    assert monitor.collect_results() == "instructions=1.25;"
