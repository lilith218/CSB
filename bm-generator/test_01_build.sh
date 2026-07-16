#!/bin/bash
# SPDX-License-Identifier: MIT

set -eu

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
mkdir -p "${tmp}/bin" "${tmp}/syzkaller"

cat > "${tmp}/bin/go" <<'EOF'
#!/bin/sh
echo /tmp/gobin
EOF
cat > "${tmp}/bin/cmake" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >> "${tmp}/cmake.log"
EOF
chmod +x "${tmp}/bin/go" "${tmp}/bin/cmake"

PATH="${tmp}/bin:${PATH}" DIR_BUILD="${tmp}/build" \
  DIR_SYZ_SRC="${tmp}/syzkaller" ./01_build.sh

grep -Fx -- "-S../ -B${tmp}/build -DCSB_BM_GENERATOR=ON" "${tmp}/cmake.log"
grep -Fx -- "--build ${tmp}/build --target syzkaller" "${tmp}/cmake.log"
