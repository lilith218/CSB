#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
mkdir -p "${tmp}/syz/bin" "${tmp}/empty" "${tmp}/parsed"
printf '1 getpid() = 1\n' > "${tmp}/trace.log"

printf '#!/bin/sh\nexit 7\n' > "${tmp}/syz/bin/syz-trace2syz"
printf '#!/bin/sh\nexit 0\n' > "${tmp}/syz/bin/syz-prog-reduce"
printf '#!/bin/sh\nexit 0\n' > "${tmp}/syz/bin/syz-multidiff"
chmod +x "${tmp}/syz/bin/"*

if DIR_SYZ_SRC="${tmp}/syz" DIR_PROG="${tmp}/parsed" TRACE_ARCH=arm64 \
    ./02_parse.sh "${tmp}/trace.log"; then
  echo "02_parse.sh masked a trace2syz failure" >&2
  exit 1
fi

if DIR_SYZ_SRC="${tmp}/syz" DIR_PROG="${tmp}/empty" DIR_OUT="${tmp}/extract" \
    ./03_extract.sh; then
  echo "03_extract.sh accepted an empty input directory" >&2
  exit 1
fi

if DIR_SYZ_SRC="${tmp}/syz" DIR_PROG="${tmp}/empty" DIR_OUT="${tmp}/reduce" \
    ./04_reduce.sh; then
  echo "04_reduce.sh accepted an empty input directory" >&2
  exit 1
fi

if DIR_SYZ_SRC="${tmp}/syz" DIR_PROG="${tmp}/empty" DIR_OUT="${tmp}/multidiff" \
    ./05_multidiff.sh; then
  echo "05_multidiff.sh accepted an empty input directory" >&2
  exit 1
fi

if DIR_PROG="${tmp}/empty" ./06_prepare.sh; then
  echo "06_prepare.sh accepted an empty input directory" >&2
  exit 1
fi
