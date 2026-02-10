# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.22)

project(
    CSB-Generator
    LANGUAGES C
    DESCRIPTION "Benchmark Generator of CSB")

include(FetchContent)

message(STATUS "Fetching syzkaller ...")

FetchContent_Declare(
  syzkaller
  GIT_REPOSITORY https://github.com/open-s4c/syzkaller.git
  GIT_TAG s4c/csb-gen
  GIT_PROGRESS TRUE
)
FetchContent_MakeAvailable(syzkaller)
