#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
cmake -S../ -B../build -DCSB_BM_GENERATOR=ON
cmake --build ../build --target csb-generate
cmake --build ../build --target csb-gen-agg
