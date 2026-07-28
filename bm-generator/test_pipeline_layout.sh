#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

for script in 04_reduce.sh 05_multidiff.sh 06_prepare.sh 07_generate.sh 08_select.sh; do
  test -x "${script}"
done

for script in 03b_reduce.sh 04_prepare.sh 05_prepare.sh 05_generate.sh 06_generate.sh 06_select.sh 07_select.sh; do
  test ! -e "${script}"
done

grep -Fq ': ${DIR_PROG:="./reduced"}' 05_multidiff.sh
grep -Fq ': ${DIR_OUT:="./multidiff"}' 05_multidiff.sh
grep -Fq ': ${DIR_PROG:="./multidiff"}' 06_prepare.sh
grep -Fq 'set -e' 07_generate.sh
