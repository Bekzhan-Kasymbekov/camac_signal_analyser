cmake_minimum_required(VERSION 3.16)

project(camac_signal_analyser_core)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(include)

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

execute_process(
    COMMAND ${Python3_EXECUTABLE} -m pybind11 --includes
    OUTPUT_VARIABLE PYBIND11_INCLUDES
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

separate_arguments(PYBIND11_INCLUDES)

add_executable(camac_parser
    src/main.cpp
    src/camac_parser.cpp
)

add_library(camac_core MODULE
    src/bindings.cpp
    src/camac_parser.cpp
)

target_compile_options(camac_core PRIVATE ${PYBIND11_INCLUDES})

target_link_libraries(camac_core PRIVATE Python3::Python)

set_target_properties(camac_core PROPERTIES
    PREFIX ""
    SUFFIX ".so"
)
