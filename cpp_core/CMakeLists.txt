cmake_minimum_required(VERSION 3.18)

project(camac_signal_analyser LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python3 COMPONENTS Interpreter Development.Module REQUIRED)

execute_process(
    COMMAND "${Python3_EXECUTABLE}" -m pybind11 --cmakedir
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

find_package(pybind11 CONFIG REQUIRED)

set(CAMAC_INCLUDE_DIR
    ${CMAKE_CURRENT_SOURCE_DIR}/cpp_core/include
)

set(CAMAC_CORE_SOURCES
    cpp_core/src/camac_parser.cpp
)

set(CAMAC_CORE_HEADERS
    cpp_core/include/camac_parser.hpp
    cpp_core/include/camac_event.hpp
    cpp_core/include/camac_archive.hpp
)

pybind11_add_module(camac_core
    cpp_core/src/bindings.cpp
    ${CAMAC_CORE_SOURCES}
    ${CAMAC_CORE_HEADERS}
)

target_include_directories(camac_core PRIVATE
    ${CAMAC_INCLUDE_DIR}
)

add_executable(camac_parser_cli
    cpp_core/src/main.cpp
    ${CAMAC_CORE_SOURCES}
    ${CAMAC_CORE_HEADERS}
)

target_include_directories(camac_parser_cli PRIVATE
    ${CAMAC_INCLUDE_DIR}
)
