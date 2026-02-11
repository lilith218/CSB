#!/bin/bash

GOBIN="`go env GOBIN`"

if [ "x${GOBIN}" == "x" ]; then
  echo "Set GOBIN go environment variable and add it to PATH"
  echo "Example:"
  echo "  go env -w GOBIN=${HOME}/.local/bin"
  echo "Double check that GOBIN is in $PATH"
  echo "  echo $PATH | grep `go env GOBIN`"
  exit 1
fi

SCRIPT_SYZ_SRC="helper/find_syzkaller_src.sh"
 : ${DIR_SYZ_SRC:=$(${SCRIPT_SYZ_SRC})}

if [ ! -d "${DIR_SYZ_SRC}" ]; then
  echo "syzkaller source dir not found. Running:"
  echo "  cmake -S. -Bbuild"
  cmake -S. -Bbuild
  cmake --build build
 DIR_SYZ_SRC=$(${SCRIPT_SYZ_SRC})
  if [ ! -d "${DIR_SYZ_SRC}" ]; then
    echo "Failed setting up syzkaller sources."
    echo "If the syzkaller source dir is not beneath $(pwd), then run this script as:"
    echo "  DIR_SYZ_SRC=</path/to/syzkaller/source> $0"
    exit 1
  fi
fi

cd "${DIR_SYZ_SRC}"

TOOLS="trace2syz prog2c extraction"

make
#make generate_trace2syz

for tool in ${TOOLS}; do
    (cd tools/syz-${tool} && go build)
done
