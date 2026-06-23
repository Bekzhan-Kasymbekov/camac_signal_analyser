cmake_minimum_required(VERSION 3.16)

project(camac_signal_analyser_core)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

execute_process(
    COMMAND ${Python3_EXECUTABLE} -m pybind11 --cmakedir
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

find_package(pybind11 CONFIG REQUIRED)

add_executable(camac_parser
    src/main.cpp
    src/camac_parser.cpp
)

target_include_directories(camac_parser PRIVATE include)

pybind11_add_module(camac_core
    src/bindings.cpp
    src/camac_parser.cpp
)

target_include_directories(camac_core PRIVATE include)
