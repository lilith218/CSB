cmake_minimum_required(VERSION 3.22)
project(
    CSB
    LANGUAGES C
    DESCRIPTION "Builtin Benchmarks of CSB")

add_subdirectory(bench)
add_subdirectory(bm-generator)
