#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT


 : ${JOBS:=$(nproc)}

GO_VER_REQ_MAJ="1"
GO_VER_REQ_MIN="25"

go_install() {
    read -p "Install go? " -n 1 -r
    echo    # (optional) move to a new line
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        ./helper/install_go.sh
    else
        exit 1
    fi
}

go_update() {
    echo "Your go version is too old, remove it and install a more recent version."
    echo "Depending on your system and installation choose one of the following:"
    echo "  dnf remove golang"
    echo "  apt remove golang-go"
    echo "  rm -rf /usr/local/go/"
    echo "Then run $0 again to install a matching version of golang"
    exit 1
}

# returns current major version in first line, minor version in second line and so on
go_version() {
    go version | sed 's/^.*go\([0-9]\)\.\([0-9]\+\)\.\([0-9]\+\).*$/\1\n\2\n\3/'
}

if [ "x`command -v go`" == "x" ]; then
    echo "Unable to find \"go\" executable in \$PATH"
    echo "Either update \$PATH or install go"
    go_install
fi

if [ "x`command -v go`" == "x" ]; then
    echo "Unable to find \"go\" executable in \$PATH"
    echo "Either update \$PATH or install go"
    exit 1
fi

CUR_MAJ=$(go_version | head -n 1)
CUR_MIN=$(go_version | head -n 2 | tail -n 1)

if [ ${CUR_MAJ} -lt ${GO_VER_REQ_MAJ} ]; then
    go_update
    exit 1
fi

if [ ${CUR_MAJ} -eq ${GO_VER_REQ_MAJ} ]; then
    if [ ${CUR_MIN} -lt ${GO_VER_REQ_MIN} ]; then
        go_update
        exit 1
    fi
fi

cmake -S. -Bbuild
cmake --build build
