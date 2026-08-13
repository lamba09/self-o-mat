cmake_minimum_required(VERSION 3.7)
project(self_o_mat)

set(CMAKE_CXX_STANDARD 14)

# Asio only exposes the posix_time based timer interfaces when Boost.Date_Time is enabled.
add_compile_definitions(BOOST_ASIO_HAS_BOOST_DATE_TIME)

if(VERBOSE)
    message("Verbose is set, adding definition")
    add_definitions(-DVERBOSE)
endif()
add_definitions(-DVERBOSE)

# Generate protobuf files on file change
add_custom_command(OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/src/protobuf/api.pb.cc ${CMAKE_CURRENT_SOURCE_DIR}/src/protobuf/api.pb.h
        DEPENDS api.proto
        COMMAND /bin/sh ${CMAKE_CURRENT_SOURCE_DIR}/compile_protobuf.sh
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})



find_package(OpenCV REQUIRED)
find_package(Boost REQUIRED)
if(Boost_FOUND)
    if(${Boost_VERSION} VERSION_GREATER_EQUAL 1.70)
        # Boost.System is header-only from 1.69 on and ships no importable component.
        find_package(Boost REQUIRED COMPONENTS thread filesystem chrono)
    else()
        find_package(Boost REQUIRED COMPONENTS system thread filesystem)
    endif()
endif()
find_package(Cups REQUIRED)
find_package(Protobuf REQUIRED)

include_directories(src)
include_directories(dependencies)
include_directories(/usr/include/gphoto2)
include_directories(/opt/libjpeg-turbo/include)
include_directories(${Boost_INCLUDE_DIR})
include_directories(${CUPS_INCLUDE_DIR})
include_directories(${Protobuf_INCLUDE_DIRS})
include_directories(${Protobuf_INCLUDE_DIR})
include_directories(dependencies/served/src)

execute_process(COMMAND /bin/sh ${CMAKE_CURRENT_SOURCE_DIR}/patches/apply-dependency-patches.sh
        RESULT_VARIABLE DEPENDENCY_PATCH_RESULT
        OUTPUT_VARIABLE DEPENDENCY_PATCH_OUTPUT
        ERROR_VARIABLE DEPENDENCY_PATCH_OUTPUT)
message("${DEPENDENCY_PATCH_OUTPUT}")
if(NOT DEPENDENCY_PATCH_RESULT EQUAL 0)
    message(FATAL_ERROR "Could not patch the vendored dependencies")
endif()

OPTION (SERVED_BUILD_TESTS "Build served unit test suite" OFF)
OPTION (SERVED_BUILD_EXAMPLES "Build served  examples" OFF)
add_subdirectory(dependencies/served)

add_subdirectory(dependencies/spdlog)

if(USE_SPI)
    message("We have wiring pi!")

    add_definitions(-DUSE_SPI)
else()
    message("We don't have wiring pi!")
endif()

add_executable(self_o_mat.app
        src/main.cpp
        src/logic/BoothLogic.cpp
        src/ui/BoothGui.cpp
        src/camera/OpenCVCamera.cpp
        src/camera/GphotoCamera.cpp
        src/logic/ImageProcessor.cpp
        src/tools/buffers.cpp
        src/logic/PrinterManager.cpp
        src/api/BoothApi.cpp src/protobuf/api.pb.cc
        src/ui/NopGui.cpp
        src/tools/JpegDecoder.cpp
        src/camera/controllers/TriggerController.cpp
        src/camera/controllers/BaseController.cpp src/camera/controllers/FocusController.cpp
        src/camera/controllers/InfoController.cpp
        src/camera/controllers/ChoiceRangeController.cpp
        src/tools/readfile.cpp
        src/tools/cobs.cpp src/logic/SelfomatController.cpp
        src/logic/filters/BasicImageFilter.cpp
        src/logic/filters/IImageFilter.cpp
        src/tools/verbose.cpp)



target_link_libraries(self_o_mat.app ${Boost_LIBRARIES}
        gphoto2
        gphoto2_port
        turbojpeg
        sfml-system
        sfml-graphics
        sfml-window
        ${OpenCV_LIBS}
        ${CUPS_LIBRARIES}
        served
        protobuf
        spdlog::spdlog
)

add_executable(filter_test src/main_filter.cpp src/logic/filters/IImageFilter.h src/logic/filters/BasicImageFilter.cpp src/logic/filters/BasicImageFilter.h src/logic/filters/IImageFilter.cpp)
target_link_libraries(filter_test ${Boost_LIBRARIES})
target_link_libraries(filter_test ${OpenCV_LIBS})

add_executable(opencv_info src/main_opencv_info.cpp)
target_link_libraries(opencv_info ${OpenCV_LIBS})

if(USE_SPI)
    target_link_libraries(self_o_mat.app wiringPi)
endif()

add_custom_target(WITH_APP /bin/sh ${CMAKE_CURRENT_SOURCE_DIR}/deploy_app.sh ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR})

add_custom_target(PACK /bin/sh ${CMAKE_CURRENT_SOURCE_DIR}/pack.sh ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR})

add_dependencies(PACK self_o_mat.app)
add_dependencies(self_o_mat.app WITH_APP)