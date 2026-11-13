cmake_minimum_required(VERSION 3.16)
project(thesis_scorer LANGUAGES CXX)
add_library(thesis_scorer SHARED page_scorer.cpp)
target_compile_features(thesis_scorer PRIVATE cxx_std_17)
set_target_properties(thesis_scorer PROPERTIES PREFIX "")
set(OUTPUT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../backend/native")
set_target_properties(thesis_scorer PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${OUTPUT_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${OUTPUT_DIR}")
foreach(CONFIG DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
    set_target_properties(thesis_scorer PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY_${CONFIG} "${OUTPUT_DIR}"
        RUNTIME_OUTPUT_DIRECTORY_${CONFIG} "${OUTPUT_DIR}")
endforeach()
if(MINGW)
    target_link_options(thesis_scorer PRIVATE -static-libgcc -static-libstdc++)
endif()
