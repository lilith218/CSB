# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os

import pandas as pd

from monitors.monitor import Monitor
from utils.logger import bm_log, LogType
from utils.process import BackgroundProcess
from benchkit.shell.shell import shell_out
from bm_utils import read_data_frame_from_csv
from bm_visualize import plot_chart, PlotConfig


class PerfLock(Monitor):
    LOCK_CONTENTION_CSV = "lock-contention.csv"
    LOCK_CONTENTION_PLOT = "lock-contention.png"
    LOCK_CONTENTION_SEPARATOR = ";"
    LOCK_CONTENTION_TOP_N = 20
    TARGET_METRIC = "avg_wait"

    # output: contended; total wait; max wait; avg wait; type; caller
    header = ["contended", "total_wait", "max_wait", "avg_wait", "type", "caller"]

    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        self.name = "perf-lock"
        self.perf_lock_data = f"{self.name}.data"
        self.perf_contention_csv = os.path.join(self.dir, f"{self.name}-report.csv")
        cmds = [
            "sudo",
            "perf",
            "lock",
            "record",
            "-g",
            "-e",
            "lock:contention_begin",
            "-e",
            "lock:contention_end",
            "--output",
            self.perf_lock_data,
        ]
        cmds.extend(args)
        # TODO: check if kernel flags are set
        # TODO: check if lock contention is supported
        self.perf_lock = BackgroundProcess(
            name=self.name,
            out_dir=output_dir,
            cmds=cmds,
            requires=["perf"],
            pin=self.get_cpus(),
        )

    def start(self):
        self.perf_lock.start()

    def collect_results(self):
        output = ""
        if self.__run_lock_contention():
            df = read_data_frame_from_csv(self.perf_contention_csv, names=self.header)
            self.__plot(df.head(self.LOCK_CONTENTION_TOP_N))
            if df is None:
                bm_log(f"{self.name} did not produce a valid data-frame", LogType.ERROR)
                return ""
            avg_wait = df["avg_wait"].mean()
            max_wait      = df["max_wait"].max()
            total_wait    = df["total_wait"].sum()

            output += f"perf_lock_avg_wait={avg_wait};"
            output += f"perf_lock_max_wait={max_wait};"
            output += f"perf_lock_total_wait={total_wait};"
        return output

    def __run_lock_contention(self) -> bool:
        cmd = [
            "sudo",
            "perf",
            "lock",
            "contention",
            "-k",
            self.TARGET_METRIC,
            "-i",
            self.perf_lock_data,
            "-x",
            ";",
            "--output",
            self.perf_contention_csv,
        ]
        try:
            shell_out(command=cmd, current_dir=self.dir)
            return True
        except Exception as e:
            bm_log("perf lock raised an error, check if it is supported.", LogType.ERROR)
            return False

    def __plot(self, df:pd.DataFrame):
        subject = "avg_wait"
        cfg = PlotConfig(y=subject, x="caller", hue="type", shape="barplot")
        plot_chart(cfg, df, os.path.join(self.dir, "lock-contention"))

    def stop(self):
        if self.perf_lock is not None:
            self.perf_lock.stop()
