# The instrument's core: the sound engine and, in time, the brain - plain
# C++17 with no framework, built natively for the plugin (plugin/) and to
# WebAssembly for the website. See plugin/PLAN.md.
cmake_minimum_required(VERSION 3.22)
project(scope_core LANGUAGES CXX)

add_library(scope_core INTERFACE)
target_include_directories(scope_core INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(scope_core INTERFACE cxx_std_17)
