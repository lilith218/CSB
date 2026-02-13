#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

BUILD_DIR="../build"
DIR_FILE="${BUILD_DIR}/syzkaller-path.txt"

if [ -f "${DIR_FILE}" ]; then
     SYZKALLER_DIR=$(cat "${DIR_FILE}")
     echo $SYZKALLER_DIR
fi
