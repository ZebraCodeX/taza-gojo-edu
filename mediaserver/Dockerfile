# tazagojo-mediaserver build+runtime image.
# Heavy: compiles libdatachannel + deps at build time (needs ~2GB RAM on ARM).
# The resulting binary is a static-ish SFU that maps WebRTC UDP to the host.

FROM debian:bookworm-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates pkg-config libssl-dev libopus-dev libsrtp2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY . .
# CMake >=4 removed old compat paths used by some upstream deps, so allow the
# legacy policy for vendored FetchContent projects.
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    && cmake --build build -j$(nproc)

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends libopus0 libsrtp2-1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /build/build/tazagojo_mediaserver /usr/local/bin/tazagojo_mediaserver
EXPOSE 9000
CMD ["tazagojo_mediaserver", "--url", "ws://backend:8000/ws/tutor/%SESSION%/?device=mediaserver&token=%TOKEN%"]