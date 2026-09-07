cmake_minimum_required(VERSION 3.16)
project(tazagojo_mediaserver CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# ---------------------------------------------------------------------------
# libdatachannel: WebRTC + a bundled WebSocket client. We read the source from
# the network on first configure. For airtight/SBC (Raspberry Pi) builds,
# vendors this directory under third_party/libdatachannel and point
# DATACHANNEL_SOURCE_DIR at it instead.
# ---------------------------------------------------------------------------
if(NOT DEFINED DATACHANNEL_SOURCE_DIR)
  set(DATACHANNEL_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/libdatachannel")
endif()

if(EXISTS "${DATACHANNEL_SOURCE_DIR}/CMakeLists.txt")
  add_subdirectory("${DATACHANNEL_SOURCE_DIR}" libdatachannel)
  set(PRIVATE_USE_GETTEXT OFF)
else()
  include(FetchContent)
  FetchContent_Declare(libdatachannel
    GIT_REPOSITORY https://github.com/paullouisageneau/libdatachannel.git
    GIT_TAG v0.21.2
    GIT_SHALLOW TRUE)
  set(USE_GNUTLS OFF CACHE BOOL "" FORCE)
  set(USE_MBEDTLS OFF CACHE BOOL "" FORCE)
  set(USE_NICE OFF CACHE BOOL "" FORCE)
  set(NO_WEBSOCKET OFF CACHE BOOL "" FORCE) # we need the bundled WebSocket client for signaling
  set(NO_EXAMPLES ON CACHE BOOL "" FORCE)
  set(NO_TESTS ON CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(libdatachannel)
endif()

find_package(Threads REQUIRED)

# nlohmann::json is vendored inside libdatachannel's dependency tree; it is not
# re-exported through the datachannel target, so surface it to our sources.
find_path(TAZAGOJO_JSON_INCLUDE_DIR nlohmann/json.hpp
  HINTS
    "${libdatachannel_SOURCE_DIR}/deps/json/include"
    "${DATACHANNEL_SOURCE_DIR}/deps/json/include")

add_executable(tazagojo_mediaserver
  src/main.cpp
  src/bitrate.hpp
  src/signaling.hpp
  src/peer.hpp
  src/relay.hpp)

target_include_directories(tazagojo_mediaserver PRIVATE src "${TAZAGOJO_JSON_INCLUDE_DIR}")
target_link_libraries(tazagojo_mediaserver PRIVATE datachannel Threads::Threads)

install(TARGETS tazagojo_mediaserver RUNTIME DESTINATION bin)