#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

for script in 04_reduce.sh 05_prepare.sh 06_generate.sh 07_select.sh; do
  test -x "${script}"
done

for script in 03b_reduce.sh 04_prepare.sh 05_generate.sh 06_select.sh; do
  test ! -e "${script}"
done

grep -Fq ': ${DIR_PROG:="./reduced"}' 05_prepare.sh
grep -Fq 'set -e' 06_generate.sh
