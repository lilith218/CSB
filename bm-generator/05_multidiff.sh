#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

source helper/bm-generator-lib.sh

: ${DIR_PROG:="./reduced"}
: ${DIR_OUT:="./multidiff"}
: ${MULTIDIFF_FOLD:=2}

if [ ! -d "${DIR_PROG}" ]; then
  echo "Directory \"${DIR_PROG}\" with reduced syz-lang programs does not exist." >&2
  echo "Run scripts with lower numbers first, or specify DIR_PROG." >&2
  exit 1
fi

DIR_PROG_ABS="`readlink -e ${DIR_PROG}`"
mapfile -d '' files < <(find "${DIR_PROG_ABS}" -type f -name '*.prog' -print0 | sort -z)
if [ "${#files[@]}" -eq 0 ]; then
  echo "No syzkaller programs found in ${DIR_PROG}." >&2
  exit 1
fi

SCRIPT_SYZ_SRC="helper/find_syzkaller_src.sh"
: ${DIR_SYZ_SRC:=$(${SCRIPT_SYZ_SRC})}
if [ ! -x "${DIR_SYZ_SRC}/bin/syz-multidiff" ]; then
  echo "syz-multidiff not found. Try to run:" >&2
  echo "  ./`ls -1 01_*.sh`" >&2
  exit 1
fi

mkdir -p "${DIR_OUT}"
DIR_OUT_ABS="`readlink -e ${DIR_OUT}`"
if [ ! -n "$(find "${DIR_OUT_ABS}" -maxdepth 0 -type d -empty 2>/dev/null)" ]; then
  echo "Directory for multidiff output is not empty: ${DIR_OUT_ABS}" >&2
  exit 1
fi

target_os="$(prog_target_os "${files[0]}")"
target_arch="$(prog_target_arch "${files[0]}")"
if ! prog_targets_match "${target_os}" "${target_arch}" "${files[@]}"; then
  echo "syz-multidiff inputs must use one target OS and architecture." >&2
  exit 1
fi

selection="$(mktemp)"
trap 'rm -f "${selection}"' EXIT
printf '%s\n' "${files[@]}" | "${DIR_SYZ_SRC}/bin/syz-multidiff" \
  -os "${target_os}" -arch "${target_arch}" -stdin -listfiles \
  -fold "${MULTIDIFF_FOLD}" > "${selection}"

while IFS= read -r file; do
  rel="${file#${DIR_PROG_ABS}/}"
  out="${DIR_OUT_ABS}/${rel}"
  mkdir -p "$(dirname "${out}")"
  cp "${file}" "${out}"
done < "${selection}"

if ! find "${DIR_OUT_ABS}" -type f -name '*.prog' -print -quit | grep -q .; then
  echo "syz-multidiff selected no programs." >&2
  exit 1
fi
