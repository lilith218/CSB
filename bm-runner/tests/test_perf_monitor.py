# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.perf import FlameGraph
from config.env_config import UniversalConfig


def lock_contention_csv():
    return """type;caller;contended;wait_total;wait_max;avg_wait
mutex;mutex_lock;4;2000000;1000000;500000
spinlock;queued_spin_lock_slowpath;10;12000000;3000000;1200000
rwsem;down_read;1;500000;500000;500000
"""


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


def test_perf_lock_commands_use_separate_output_files():
    assert FlameGraph.lock_record_cmd(["-C", "0,1"]) == [
        "sudo",
        "perf",
        "lock",
        "record",
        "--output",
        "perf-lock.data",
        "-C",
        "0,1",
    ]
    assert FlameGraph.lock_contention_cmd() == [
        "sudo",
        "perf",
        "lock",
        "contention",
        "-i",
        "perf-lock.data",
        "-x",
        ";",
        "-F",
        "contended,wait_total,wait_max,avg_wait",
        "--output",
        "lock-contention.csv",
    ]


def test_lock_contention_dataframe_parses_and_sorts_csv(tmp_path):
    csv_file = tmp_path / FlameGraph.LOCK_CONTENTION_CSV
    csv_file.write_text(lock_contention_csv())

    df = FlameGraph.lock_contention_dataframe(csv_file)

    assert list(df["lock"]) == [
        "queued_spin_lock_slowpath",
        "mutex_lock",
        "down_read",
    ]
    assert list(df["wait_total_ms"]) == [12.0, 2.0, 0.5]
    assert list(df["contended"]) == [10, 4, 1]


def test_lock_contention_plot_regenerated_for_all_runs(tmp_path):
    first_run = tmp_path / "container_cnt-1" / "run-1"
    second_run = tmp_path / "container_cnt-2" / "run-1"
    first_run.mkdir(parents=True)
    second_run.mkdir(parents=True)
    (first_run / FlameGraph.LOCK_CONTENTION_CSV).write_text(lock_contention_csv())
    (second_run / FlameGraph.LOCK_CONTENTION_CSV).write_text(lock_contention_csv())

    FlameGraph.dump_lock_contention_plots_for_tree(tmp_path)

    assert (first_run / FlameGraph.LOCK_CONTENTION_PLOT).stat().st_size > 0
    assert (second_run / FlameGraph.LOCK_CONTENTION_PLOT).stat().st_size > 0
