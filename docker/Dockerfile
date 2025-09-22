#
# AWG GOLANG BUILDING STAGE
# Base: Alpine
#

# Pull the current golang-alpine image.
FROM golang:1.25-alpine AS awg-go

# Install build-dependencies.
RUN apk add --no-cache \
    git \
    gcc \
    musl-dev

# Standard working directory for WGDashboard
RUN mkdir -p /workspace && \
    git clone https://github.com/WGDashboard/amneziawg-go /workspace/awg

# Enable CGO compilation for AmneziaWG
ENV CGO_ENABLED=1

# Change directory
WORKDIR /workspace/awg
# Compile the binaries
RUN go mod download && \
    go mod verify && \
    go build -ldflags '-linkmode external -extldflags "-fno-PIC -static"' -v -o /usr/bin
#
# AWG TOOLS BUILDING STAGE
# Base: Debian
#
FROM alpine:latest AS awg-tools

# Install needed dependencies.
RUN apk add --no-cache \
    make \
    git \
    build-base \
    linux-headers \
    ca-certificates

# Get the workspace ready
RUN mkdir -p /workspace && \
    git clone https://github.com/WGDashboard/amneziawg-tools /workspace/awg-tools

# Change directory
WORKDIR /workspace/awg-tools/src
# Compile and change permissions
RUN make && chmod +x wg*

#
# PIP DEPENDENCY BUILDING
# Base: Alpine
#

# Use the python-alpine image for building pip dependencies
FROM python:3.13-alpine AS pip-builder

# Add the build dependencies and create a Python virtual environment.
RUN apk add --no-cache \
      build-base \
      pkgconfig \
      python3-dev \
      libffi-dev \
      linux-headers \
      rust \
      cargo \
    && mkdir -p /opt/wgdashboard/src \
    && python3 -m venv /opt/wgdashboard/src/venv

# Copy the requirements file into the build layer.
COPY ./src/requirements.txt /opt/wgdashboard/src
# Install the pip packages
RUN . /opt/wgdashboard/src/venv/bin/activate && \
    pip3 install --upgrade pip && \
    pip3 install -r /opt/wgdashboard/src/requirements.txt

#
# WGDashboard RUNNING STAGE
# Base: Alpine
#

# Running with the python-alpine image.
FROM python:3.13-alpine AS final
LABEL maintainer="dselen@nerthus.nl"

# Install only the runtime dependencies
RUN apk add --no-cache \
    iproute2 iptables \
    bash curl \
    wget unzip \
    procps sudo \
    tzdata wireguard-tools \
    openresolv openrc

# Copy only the final binaries from the AWG builder stages
COPY --from=awg-go /usr/bin/amneziawg-go /usr/bin/amneziawg-go
COPY --from=awg-tools /workspace/awg-tools/src/wg /usr/bin/awg
COPY --from=awg-tools /workspace/awg-tools/src/wg-quick/linux.bash /usr/bin/awg-quick

# Environment variables
ARG wg_net="10.0.0.1"
ARG wg_port="51820"
ENV TZ="Europe/Amsterdam" \
    global_dns="9.9.9.9" \
    wgd_port="10086" \
    log_level="INFO" \
    public_ip="" \
    WGDASH=/opt/wgdashboard

# Create directories needed for operation
RUN mkdir /data /configs -p ${WGDASH}/src /etc/amnezia/amneziawg

# Copy the python virtual environment from the pip-builder stage
COPY ./src ${WGDASH}/src
COPY --from=pip-builder /opt/wgdashboard/src/venv /opt/wgdashboard/src/venv

# First WireGuard interface template
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN out_adapt=$(ip -o -4 route show to default | awk '{print $NF}') \
  && echo -e "[Interface]\n\
Address = ${wg_net}/24\n\
PrivateKey =\n\
PostUp = iptables -t nat -I POSTROUTING 1 -s ${wg_net}/24 -o ${out_adapt} -j MASQUERADE\n\
PostUp = iptables -I FORWARD -i wg0 -o wg0 -j DROP\n\
PreDown = iptables -t nat -D POSTROUTING -s ${wg_net}/24 -o ${out_adapt} -j MASQUERADE\n\
PreDown = iptables -D FORWARD -i wg0 -o wg0 -j DROP\n\
ListenPort = ${wg_port}\n\
SaveConfig = true\n\
DNS = ${global_dns}" > /configs/wg0.conf.template \
  && chmod 600 /configs/wg0.conf.template

# Set a healthcheck to determine the container its health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

# Copy in the runtime script, essential.
COPY ./docker/entrypoint.sh /entrypoint.sh

#
EXPOSE 10086
WORKDIR $WGDASH/src

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
