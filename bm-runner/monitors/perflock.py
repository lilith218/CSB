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
        VALUE_COL = "avg_wait"
        KEY_COL = "caller"
        INFO_COL = "type"
        output = ""
        self.__run_lock_contention()
        df = read_data_frame_from_csv(self.perf_contention_csv, names=self.header)
        self.__plot(df)
        print(df)
        if df is None:
            bm_log(f"{self.name} did not produce a valid data-frame", LogType.ERROR)
            return ""
        for _, row in df.iterrows():
            value = row[VALUE_COL]
            key = row[KEY_COL]
            info = row[INFO_COL]
            if pd.notna(value) and pd.api.types.is_number(value):
                output += f"{key}_{info}={value};"
            else:
                bm_log(f"{self.name} could not read a valid value for {key}", LogType.ERROR)
        return output

    def __run_lock_contention(self):
        cmd = [
            "sudo",
            "perf",
            "lock",
            "contention",
            "-i",
            self.perf_lock_data,
            "-x",
            ";",
            "--output",
            self.perf_contention_csv,
        ]
        shell_out(command=cmd, current_dir=self.dir)

    def __plot(self, df):
        cfg = PlotConfig(y="avg_wait", x="caller", hue="type")
        plot_chart(cfg, df, os.path.join(self.dir, "lock-contention"))

    def stop(self):
        if self.perf_lock is not None:
            self.perf_lock.stop()
