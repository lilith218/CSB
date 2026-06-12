# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import sys
import subprocess
import glob
import re
from io import StringIO
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
from pandas import DataFrame

from monitors.monitor import Monitor
from bm_utils import resolve_path
from utils.logger import bm_log, LogType
from utils.process import BackgroundProcess
from config.env_config import EnvUniversalConfig, UniversalConfig
from benchkit.shell.shell import shell_out

class PerfLock(Monitor):
    LOCK_CONTENTION_CSV = "lock-contention.csv"
    LOCK_CONTENTION_PLOT = "lock-contention.png"
    LOCK_CONTENTION_SEPARATOR = ";"
    LOCK_CONTENTION_TOP_N = 20

    def __init__(self, output_dir: str, args: Optional[list[str]] = []):
        super().__init__(dir=output_dir, args=args)
        self.name = "perf-lock"
        self.outfile_name = f"{self.name}.data"
        self.report_file = f"{self.name}-report.csv"
        cmds = ["sudo", "perf", "lock", "record",  "-e", "lock:contention_begin",
            "-e", "lock:contention_end", "--output", self.outfile_name]
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


    def lock_contention_cmd(self) -> list[str]:
        return [
            "sudo",
            "perf",
            "lock",
            "contention",
            "-i",
            self.outfile_name,
            "-x",
            ";",
            "-F",
            "contended,wait_total,wait_max,avg_wait",
            "--output",
            self.report_file,
        ]

    @classmethod
    def perf_events(cls) -> list[str]:
        events = ["cycles"]
        if cls.arm_spe_enabled_and_supported():
            events.append(cls.arm_spe_event())
        return events

    def start(self):
        self.perf_lock.start()

    def collect_results(self):
        return ""

        """
        Generates flamegraph on perf.data in output dir
        """
        # run perf script on the perf.data in results folder
        perf = subprocess.Popen(
            ["sudo", "perf", "script", "-i", "perf.data"],
            cwd=self.dir,
            stdout=subprocess.PIPE,
            stderr=errfile,
        )
        # run stack collapse on the output of perf record
        stacks_file = os.path.join(self.dir, "flamegraph.stacks")
        with open(stacks_file, "w") as stacks:
            try:
                subprocess.run(
                    [f"{self.fg_path}/stackcollapse-perf.pl"],
                    stdin=perf.stdout,
                    stdout=stacks,
                    stderr=errfile,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                bm_log(f"Failed to generate flamegraph: {e}", LogType.ERROR)
            finally:
                if perf.stdout:
                    perf.stdout.close()
        svg = os.path.join(self.dir, "flamegraph.svg")
        # run flamegraph on the output of stackcollapse
        # and save the output in svg
        with open(svg, "w") as svg, open(stacks_file, "r") as stacks:
            try:
                subprocess.run(
                    [f"{self.fg_path}/flamegraph.pl"],
                    stdin=stacks,
                    stdout=svg,
                    stderr=errfile,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                bm_log(f"Failed to generate flamegraph: {e}", LogType.ERROR)
    def __generate_lock_contention(self):
        shell_out(
            command=self.lock_contention_cmd(),
            current_dir=self.dir
        )
        self.dump_lock_contention_plot_from_file(Path(self.dir) / self.report_file)

    @classmethod
    def dump_lock_contention_plots_for_tree(cls, output_dir: Path):
        for csv_file in sorted(output_dir.glob(f"**/{cls.LOCK_CONTENTION_CSV}")):
            cls.dump_lock_contention_plot_from_file(csv_file)

    @classmethod
    def dump_lock_contention_plot_from_file(cls, csv_file: Path):
        df = cls.lock_contention_dataframe(csv_file)
        cls.dump_lock_contention_plot(df, csv_file.parent / cls.LOCK_CONTENTION_PLOT)

    @classmethod
    def lock_contention_dataframe(cls, csv_file: Path) -> DataFrame:
        if not csv_file.exists() or csv_file.stat().st_size == 0:
            bm_log(f"CSV not exists or size=0 {csv_file}", LogType.ERROR)
            return pd.DataFrame()

        try:
            with open(csv_file, "r") as file:
                content = file.read()
        except OSError as e:
            bm_log(f"Could not read lock-contention output from {csv_file}: {e}", LogType.ERROR)
            return pd.DataFrame()


        lines = content.splitlines()
        # Find the line with the header
        header_line = next(
            (line for line in lines if line.lstrip().startswith("# output:")),
            None
        )

        if header_line is None:
            return pd.DataFrame()  # or handle error

        # Remove the '# output:' prefix and split into column names
        header = [col.strip() for col in header_line.replace("# output:", "").split(cls.LOCK_CONTENTION_SEPARATOR)]

        table_lines = [
            line.strip()
            for line in content.splitlines()
            if cls.LOCK_CONTENTION_SEPARATOR in line and not line.lstrip().startswith("#")
        ]
        if not table_lines:
            bm_log(f"Could not extract tables from {csv_file}: {e}", LogType.ERROR)
            return pd.DataFrame()

        try:
            raw_df = pd.read_csv(
                StringIO("\n".join(table_lines)),
                sep=cls.LOCK_CONTENTION_SEPARATOR,
                engine="python",
                header=None,
                names=header
            )
        except pd.errors.ParserError as e:
            bm_log(f"Could not parse lock-contention output from {csv_file}: {e}", LogType.ERROR)
            return pd.DataFrame()

        return cls.normalize_lock_contention_dataframe(raw_df)

    @classmethod
    def normalize_lock_contention_dataframe(cls, raw_df: DataFrame) -> DataFrame:
        if raw_df.empty:
            bm_log(f"Normalize got empty df: {raw_df}", LogType.ERROR)
            return pd.DataFrame()

        raw_df = raw_df.rename(columns=lambda col: str(col).strip())
        metric_columns = {
            "contended": cls.find_column(raw_df, ["contended", "output: contended"]),
            "wait_total": cls.find_column(raw_df, ["wait_total", "total_wait"]),
            "wait_max": cls.find_column(raw_df, ["wait_max", "max_wait"]),
            "avg_wait": cls.find_column(raw_df, ["avg_wait", "average_wait"]),
        }
        metric_columns = {metric: col for metric, col in metric_columns.items() if col}
        if not metric_columns:
            bm_log(f"Normalize got no metric columns: {raw_df.columns}", LogType.ERROR)
            return pd.DataFrame()

        label_column = cls.find_label_column(raw_df, set(metric_columns.values()))
        if label_column is None:
            bm_log(f"Label not found: {raw_df}", LogType.ERROR)
            return pd.DataFrame()

        df = pd.DataFrame()
        df["lock"] = raw_df[label_column].astype(str)
        for metric, col in metric_columns.items():
            df[metric] = cls.to_numeric_series(raw_df[col])

        df = df.dropna(subset=list(metric_columns.keys()), how="all")
        df = df[(df["lock"].str.len() > 0) & (df["lock"] != "nan")]
        if "wait_total" in df:
            df["wait_total_ms"] = df["wait_total"] / 1_000_000
            df = df.sort_values("wait_total", ascending=False)
        else:
            df = df.sort_values("contended", ascending=False)
        return df

    @classmethod
    def dump_lock_contention_plot(cls, df: DataFrame, plot_file: Path):
        if df.empty:
            return

        top_df = df.head(cls.LOCK_CONTENTION_TOP_N).copy()
        if "wait_total_ms" in top_df:
            x_col = "wait_total_ms"
            x_label = "Total wait (ms)"
            title = "Lock contention by total wait"
        else:
            x_col = "contended"
            x_label = "Contended acquisitions"
            title = "Lock contention"

        top_df = top_df.sort_values(x_col, ascending=True)
        height = max(4, min(12, 0.35 * len(top_df) + 1.5))
        plt.figure(figsize=(10, height), dpi=150)
        plt.barh(top_df["lock"], top_df[x_col])
        plt.title(title)
        plt.xlabel(x_label)
        plt.grid(axis="x")
        plt.tight_layout()
        plt.savefig(plot_file)
        plt.close()

    @classmethod
    def find_label_column(cls, df: DataFrame, metric_columns: set[str]) -> Optional[str]:
        preferred = ["caller", "lock", "name", "symbol", "type"]
        candidates = [col for col in df.columns if col not in metric_columns]
        for name in preferred:
            for col in candidates:
                if name in cls.normalize_column_name(col):
                    return col
        return candidates[-1] if candidates else None

    @classmethod
    def find_column(cls, df: DataFrame, names: list[str]) -> Optional[str]:
        normalized_names = [cls.normalize_column_name(name) for name in names]
        for col in df.columns:
            normalized_col = cls.normalize_column_name(col)
            if any(name in normalized_col for name in normalized_names):
                return col
        return None

    @staticmethod
    def normalize_column_name(name: str) -> str:
        return re.sub(r"[^0-9a-z# ]+", "_", str(name).strip().lower()).strip("_")

    @staticmethod
    def to_numeric_series(series) -> pd.Series:
        values = series.astype(str).str.replace(",", "", regex=False)
        values = values.str.extract(r"([-+]?\d+(?:\.\d+)?)", expand=False)
        return pd.to_numeric(values, errors="coerce")

    def stop(self):
        if self.perf_lock is not None:
            self.perf_lock.stop()
            self.__generate_lock_contention()
