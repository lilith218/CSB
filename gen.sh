#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
set -e
export CSB_RESULTS_GROUP="rocksdb"
rm -rf build
cmake -S. -Bbuild -DCSB_BM_GENERATOR=ON
cmake --build build --target zoom_out_single.json.in


