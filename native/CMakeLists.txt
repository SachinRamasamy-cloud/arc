cmake_minimum_required(VERSION 3.20)
project(arc_engine VERSION 1.0.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_path(BOOST_INCLUDE_DIR boost/json.hpp REQUIRED)
add_library(arc-native-core STATIC
    src/boost_json.cpp
    engines/validation/json.cpp
    engines/validation/csv.cpp
    engines/transformation/normalize.cpp
    engines/transformation/process.cpp
)
target_include_directories(arc-native-core PUBLIC include ${BOOST_INCLUDE_DIR})
foreach(target arc-native-core)
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror -fstack-protector-strong)
endforeach()
option(ARC_SANITIZE "Enable address and undefined behavior sanitizers" OFF)
if(ARC_SANITIZE)
    target_compile_options(arc-native-core PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(arc-native-core PUBLIC -fsanitize=address,undefined)
endif()
add_executable(arc-engine worker/main.cpp)
target_link_libraries(arc-engine PRIVATE arc-native-core)
target_compile_options(arc-engine PRIVATE -Wall -Wextra -Wpedantic -Werror -fstack-protector-strong)
enable_testing()
add_test(NAME engine-version COMMAND arc-engine --version)
add_executable(arc-core-test tests/core_test.cpp)
target_link_libraries(arc-core-test PRIVATE arc-native-core)
target_compile_options(arc-core-test PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME core-operations COMMAND arc-core-test)
