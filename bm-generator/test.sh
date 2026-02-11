#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
set -e

STRACE_LOG="ls_strace.log"
APP="ls"
FILE_LOG=${STRACE_LOG} helper/collect_strace.sh ${APP}
./00_init.sh
./01_build.sh
./02_parse.sh ${STRACE_LOG}
./03_extract.sh
./04_prepare.sh
./05_generate.sh
