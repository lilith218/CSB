#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
mkdir -p "${tmp}/syz/bin" "${tmp}/reduced/0"

for name in keep drop; do
  printf '# csb.trace.os=linux\n# csb.trace.arch=amd64\ngetpid()\n' > \
    "${tmp}/reduced/0/${name}.prog"
done

printf '%s\n' '#!/bin/sh' \
  'while [ "$#" -gt 0 ]; do' \
  '  shift' \
  'done' \
  'IFS= read -r selected' \
  'printf '\''%s\n'\'' "${selected}"' > "${tmp}/syz/bin/syz-multidiff"
chmod +x "${tmp}/syz/bin/syz-multidiff"

input_rel="$(realpath --relative-to "$(pwd)" "${tmp}/reduced")"
DIR_SYZ_SRC="${tmp}/syz" DIR_PROG="${input_rel}" DIR_OUT="${tmp}/selected" \
  ./05_multidiff.sh

cmp "${tmp}/reduced/0/drop.prog" "${tmp}/selected/0/drop.prog"
test ! -e "${tmp}/selected/0/keep.prog"

if DIR_SYZ_SRC="${tmp}/syz" DIR_PROG="${tmp}/reduced" DIR_OUT="${tmp}/selected" \
    ./05_multidiff.sh; then
  echo "05_multidiff.sh accepted a non-empty output directory" >&2
  exit 1
fi
