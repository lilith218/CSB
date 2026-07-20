# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import sys
import subprocess
import glob
from monitors.monitor import Monitor
from bm_utils import resolve_path
from utils.logger import bm_log, LogType
from utils.process import BackgroundProcess
from config.env_config import EnvUniversalConfig, UniversalConfig
from benchkit.shell.shell import shell_out


class FlameGraph(Monitor):
    FG_PATH_DIR = "deps/FlameGraph"
    ARM_SPE_PERIOD_ENV_VAR_NAME = "CSB_ARM_SPE_PERIOD"
    ARM_SPE_DEVICE_GLOB = "/sys/bus/event_source/devices/arm_spe*"
    ARM_SPE_MIN_INTERVAL_GLOB = "/sys/bus/event_source/devices/arm_spe*/caps/min_interval"
    ARM_SPE_FALLBACK_MIN_INTERVAL = 1024
    ARM_SPE_PERIOD_MULTIPLIER = 10
    DATA_FILE = "perf.data"

    def __init__(self, output_dir: str, args: list[str] = ["-a"]):
        super().__init__(dir=output_dir, args=args)
        if self.arm_spe_enabled() and not self.arm_spe_supported():
            bm_log(
                "arm_spe PMU is not available; skipping arm_spe perf event.",
                LogType.WARNING,
            )
        cmds = self.perf_record_cmd(args)
        self.perf = BackgroundProcess(
            name="perf",
            out_dir=output_dir,
            cmds=cmds,
            requires=["perf"],
            pin=self.get_cpus(),
        )
        self.fg_path = resolve_path(self.FG_PATH_DIR)

    @classmethod
    def perf_record_cmd(cls, args: list[str]) -> list[str]:
        cmds = [
            "sudo",
            "perf",
            "record",
            "-g",
        ]
        for event in cls.perf_events():
            cmds.extend(["-e", event])
        cmds.extend(args)
        return cmds

    @classmethod
    def perf_events(cls) -> list[str]:
        # Restrict frequency sampling to the cycles event.
        # Avoid using a global '-F 99', as tracepoint events (e.g. lock contention)
        # should be recorded on every occurrence rather than being frequency sampled.
        events = ["cycles/freq=99/"]
        if cls.arm_spe_enabled_and_supported():
            events.append(cls.arm_spe_event())
        return events

    @classmethod
    def arm_spe_enabled_and_supported(cls) -> bool:
        return cls.arm_spe_enabled() and cls.arm_spe_supported()

    @classmethod
    def arm_spe_enabled(cls) -> bool:
        return EnvUniversalConfig.is_on(UniversalConfig.CSB_ARM_SPE)

    @classmethod
    def arm_spe_supported(cls) -> bool:
        for device in glob.glob(cls.ARM_SPE_DEVICE_GLOB):
            if not os.path.isdir(device):
                continue
            try:
                with open(os.path.join(device, "type"), "r") as type_file:
                    int(type_file.read().strip(), 0)
            except (OSError, ValueError):
                continue
            else:
                return True
        return False

    @classmethod
    def arm_spe_event(cls) -> str:
        return f"arm_spe/jitter=1,period={cls.arm_spe_period()}/"

    @classmethod
    def arm_spe_period(cls) -> int:
        env_period = os.getenv(cls.ARM_SPE_PERIOD_ENV_VAR_NAME)
        if env_period is not None:
            period = 0
            try:
                period = int(env_period)
            except ValueError:
                bm_log(
                    f"{cls.ARM_SPE_PERIOD_ENV_VAR_NAME} must be a positive integer.",
                    LogType.FATAL,
                )
                sys.exit(1)
            if period > 0:
                return period
            bm_log(
                f"{cls.ARM_SPE_PERIOD_ENV_VAR_NAME} must be a positive integer.",
                LogType.FATAL,
            )
            sys.exit(1)

        return cls.arm_spe_min_interval() * cls.ARM_SPE_PERIOD_MULTIPLIER

    @classmethod
    def arm_spe_min_interval(cls) -> int:
        intervals = []
        for path in glob.glob(cls.ARM_SPE_MIN_INTERVAL_GLOB):
            try:
                with open(path, "r") as min_interval_file:
                    interval = int(min_interval_file.read().strip(), 0)
            except (OSError, ValueError):
                continue
            if interval > 0:
                intervals.append(interval)
        if intervals:
            return max(intervals)
        return cls.ARM_SPE_FALLBACK_MIN_INTERVAL

    def start(self):
        # Launch perf in the background
        self.perf.start()

    def collect_results(self):
        return ""

    def __generate_flamegraph(self, errfile):
        """
        Generates flamegraph on perf data in output dir
        """
        # run perf script on the perf data in results folder
        cmd = ["sudo", "perf", "script", "-i", self.DATA_FILE]
        # If the recording contains tracepoint events, suppress them in the
        # perf script output so they are not included in the FlameGraph.
        # This leaves hardware sampling events (e.g. cycles) available for
        # stackcollapse-perf.pl while preserving the tracepoints in perf.data
        # for other analyses such as `perf lock contention`.
        if self.__perf_data_has_tracepoints():
            cmd.extend(["-F", "trace:"])
        perf = subprocess.Popen(
            cmd,
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

    def stop(self):
        if self.perf is not None:
            self.perf.stop(timeout=30)
            with open(os.path.join(self.dir, "flamegraph.errors"), "w") as errfile:
                self.__generate_flamegraph(errfile)

    def __perf_data_has_tracepoints(self) -> bool:
        cmd = [
            "sudo",
            "perf",
            "evlist",
            "-i",
            self.DATA_FILE,
        ]
        try:
            result = shell_out(cmd, current_dir=self.dir)

            return any(
                event.startswith("lock:") or event.startswith("tracepoint:")
                for event in result.split()
            )
        except Exception:
            return False
