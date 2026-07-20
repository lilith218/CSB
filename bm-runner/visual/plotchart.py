# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from config.plot import PlotConfig
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame
from utils.logger import LogType, bm_log
import seaborn as sns
from pathlib import Path
from typing import Optional


class PlotChart:
    def __init__(self, plot: PlotConfig):
        self.fig = plt.figure(dpi=150)
        self.chart = self.fig.add_subplot()
        self.chart.set_title(plot.title)
        self.plots_count: int = 0

    def add(
        self,
        plot: PlotConfig,
        df: DataFrame,
        add_points: bool = False,
        **kwargs,
    ) -> bool:

        if (
            not PlotChart.__col_exists(df, plot.y, plot.title)
            or not PlotChart.__col_exists(df, plot.x, plot.title)
            or not PlotChart.__col_exists(df, plot.hue, plot.title)
        ):
            return False

        required_cols = [plot.x, plot.y, plot.hue]
        # this will drop all rows with missing values
        plot_df = df.dropna(subset=required_cols)

        if plot_df.empty:
            bm_log(
                f"Cannot plot {plot.title}: no complete rows for "
                f"'{plot.x}', '{plot.y}', and '{plot.hue}'",
                LogType.ERROR,
            )
            return False

        args = dict(kwargs)
        # prep hue, we want to generate enough colors
        cnt = plot_df[plot.hue].nunique()
        sorted_gp = sorted(plot_df[plot.hue].unique())
        if isinstance(plot.palette, str):
            palette = sns.color_palette(palette=plot.palette, n_colors=cnt)
        else:
            palette = plot.palette
        sns_plot_fun = getattr(sns, plot.shape)

        chart = sns_plot_fun(
            ax=self.chart,
            data=plot_df,
            palette=palette,
            x=plot.x,
            hue=plot.hue,
            hue_order=sorted_gp,
            y=plot.y,
            **args,
        )

        if add_points:
            sns.scatterplot(
                x=plot.x,
                y=plot.y,
                hue=plot.hue,
                markers=plot.hue,
                data=plot_df,
                hue_order=sorted_gp,
                palette=palette,
                ax=chart,
                legend=False,
            )

        # calculate maximum length of x values
        max_len = max(len(str(x)) for x in plot_df[plot.x])
        # rotate the xticks to avoid overlap of string
        if max_len > 10:
            plt.xticks(rotation=90)

        chart.set(xlabel=plot.x_lbl, ylabel=plot.y_lbl)
        chart.grid(True)
        new_ylim = 1.2 * pd.to_numeric(plot_df[plot.y], errors="coerce").dropna().max()
        if np.isfinite(new_ylim):
            chart.set_ylim(0, 1 if new_ylim == 0 else new_ylim)
        else:
            bm_log(
                f"Tried to setup an invalid Y={new_ylim} on `{plot.y_lbl}` axis limit at `{plot.title}` plot!",
                LogType.WARNING,
            )

        plt.legend(
            loc="upper left",
            title=f"{plot.hue_lbl}",
            bbox_to_anchor=(1, 1),
            borderaxespad=0.3,
            fontsize=4.5,
        )
        self.plots_count += 1
        return True

    def save(self, out_fig_name, gen_pdf: bool = False) -> Optional[str]:
        if self.plots_count == 0:
            bm_log(f"Will not save plot {out_fig_name}. It is empty", LogType.ERROR)
            plt.close()
            return None
        self.fig.set_size_inches(w=10, h=8)
        self.fig.tight_layout()

        fig_name = f"{out_fig_name}.png"
        if Path(fig_name).exists():
            bm_log(f"{fig_name} already exists and is going to be overwritten!!!", LogType.WARNING)
        self.fig.savefig(fig_name, transparent=False)
        if gen_pdf:
            self.fig.savefig(f"{out_fig_name}.pdf", transparent=False)
        plt.close()
        return fig_name

    @staticmethod
    def __col_exists(df: DataFrame, col: str, title: str) -> bool:
        if col not in df.columns:
            bm_log(
                f"cannot find column {col} in the produced data. This plot `{title}` will not be generated!",
                LogType.ERROR,
            )
            return False
        return True

    @staticmethod
    def plot(
        plot: PlotConfig,
        df: DataFrame,
        out_fig_name,
        add_points: bool = False,
        gen_pdf: bool = False,
        **kwargs,
    ) -> Optional[str]:
        pc = PlotChart(plot)
        if pc.add(plot, df, add_points=add_points, **kwargs):
            return pc.save(out_fig_name, gen_pdf)
        else:
            plt.close()
            return None
