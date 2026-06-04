cmake_minimum_required(VERSION 3.16)

project(camac_signal_analyser_core)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(include)

add_executable(camac_parser
    src/main.cpp
    src/camac_parser.cpp
)
