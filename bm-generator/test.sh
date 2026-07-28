#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
set -e
export CSB_RESULTS_GROUP="ls"
source helper/bm-generator-lib.sh
echo "STEP#A: Testing architecture metadata helpers ..."
./test_arch_metadata.sh
./test_01_build.sh
./test_pipeline_guards.sh
./test_pipeline_layout.sh
./test_multidiff_stage.sh
STRACE_LOG="ls_strace.log"
APP="ls -la /dev"
../scripts/plugins/collect_strace.sh ${STRACE_LOG} ${APP}
echo "STEP#0: Initializing ..."
./00_init.sh
echo "STEP#1: Building ..."
./01_build.sh
echo "STEP#1A: Testing syzkaller architecture metadata and sanitizer matrix ..."
(cd ../deps/syzkaller && go test ./tools/syz-trace2syz ./tools/syz-prog2c -count=1)
echo "STEP#2: Parsing ${STRACE_LOG} ..."
./02_parse.sh ${STRACE_LOG}
echo "STEP#3: Extracting ..."
./03_extract.sh
echo "STEP#4: Reducing ..."
./04_reduce.sh
echo "STEP#5: Filtering with multidiff ..."
./05_multidiff.sh
echo "STEP#6: Preparing ..."
./06_prepare.sh
echo "STEP#7: Generating ..."
./07_generate.sh
echo "STEP#8: Selecting benchmarks using flamegraph-diff ..."
./08_select.sh
