# syntax=docker/dockerfile:1.7

# First reproducible container target.  cliairplay v0.5.3 has only been pinned
# and practically tested here on Linux x86_64, so this file deliberately fails
# rather than pretending that another architecture is supported.
FROM --platform=linux/amd64 rust:1.98-bookworm AS vibecast-builder
ARG VIBECAST_REPOSITORY=https://github.com/Allcrafter1/vibecast.git
ARG VIBECAST_COMMIT=f28befe02fe930db300294d6bf49cdf5fec5a747
RUN apt-get update \
    && apt-get install -y --no-install-recommends clang cmake git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --filter=blob:none "${VIBECAST_REPOSITORY}" . \
    && git checkout --detach "${VIBECAST_COMMIT}"
RUN cargo build --locked --release -p vibecast-cli

FROM --platform=linux/amd64 python:3.12-slim-bookworm AS python-builder
WORKDIR /src
COPY config/container-build-cp312.lock.txt /tmp/build-requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
      --require-hashes -r /tmp/build-requirements.txt
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
RUN python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/wheels .

FROM --platform=linux/amd64 debian:bookworm-slim AS airplay-fetch
ARG CLIAIRPLAY_VERSION=v0.5.3
ARG CLIAIRPLAY_SHA256=fd6fa451cdfd0c83c502e8cdfc7e73b24a9553e7058508b5e8c69cdd1dd621dd
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl --fail --location --proto '=https' --tlsv1.2 \
      "https://github.com/music-assistant/airplay-cli/releases/download/${CLIAIRPLAY_VERSION}/cliairplay-linux-x86_64" \
      --output /tmp/cliairplay \
    && echo "${CLIAIRPLAY_SHA256}  /tmp/cliairplay" | sha256sum --check --strict \
    && chmod 0755 /tmp/cliairplay

FROM --platform=linux/amd64 python:3.12-slim-bookworm
ARG BUILD_VERSION=0.6.0-dev12
ARG BUILD_ARCH=amd64
LABEL org.opencontainers.image.title="Cast Audio Receiver Lab"
LABEL org.opencontainers.image.description="Experimental Cast audio receiver with modular local and AirPlay outputs"
LABEL org.opencontainers.image.licenses="GPL-3.0-or-later"
LABEL io.hass.version="${BUILD_VERSION}"
LABEL io.hass.type="app"
LABEL io.hass.arch="${BUILD_ARCH}"
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates ffmpeg libstdc++6 libssl3 mpv tini \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/cast-audio-receiver
COPY config/container-linux-x86_64-cp312.lock.txt /tmp/runtime-requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
      --require-hashes -r /tmp/runtime-requirements.txt
COPY --from=python-builder /tmp/wheels/cast_audio_receiver_lab-*.whl /tmp/
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
      --no-deps /tmp/cast_audio_receiver_lab-*.whl \
    && python -m pip check
COPY --from=vibecast-builder /src/target/release/vibecast /usr/local/bin/vibecast
COPY --from=airplay-fetch /tmp/cliairplay /usr/local/bin/cliairplay
RUN mkdir -p /data/private && chown -R 1000:1000 /data
VOLUME ["/data"]
EXPOSE 8008 8009 8788
ENTRYPOINT ["/usr/bin/tini", "--", "cast-audio-bootstrap"]
