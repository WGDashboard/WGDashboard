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
# WGDashboard RUNNING STAGE
# Base: Alpine
#

# Running with the python-alpine image.
FROM alpine:3.22 AS final
LABEL maintainer="dselen@nerthus.nl"

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
RUN mkdir -p /data /configs "${WGDASH}" "${WGDASH}/db" \
  "${WGDASH}/log" "${WGDASH}/download" /etc/amnezia/amneziawg

WORKDIR $WGDASH

# Copy source files
COPY ./src .

# Copy only the final binaries from the AWG builder stages
COPY --from=awg-go /usr/bin/amneziawg-go /usr/bin/amneziawg-go
COPY --from=awg-tools /workspace/awg-tools/src/wg /usr/bin/awg
COPY --from=awg-tools /workspace/awg-tools/src/wg-quick/linux.bash /usr/bin/awg-quick

# Copy in the runtime script, essential.
COPY ./docker/entrypoint.sh /entrypoint.sh

# Install dependencies
RUN apk add --no-cache \
    iproute2 iptables \
    bash curl procps \
    tzdata wireguard-tools \
    python3 py3-pip py3-psutil py3-bcrypt && \
    python3 -m pip install --upgrade pip --break-system-packages && \
    python3 -m pip install --no-cache-dir --break-system-packages -r requirements.txt

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

# Replacement of paths with relative ones for namespace handling when using a reverse proxy
RUN set -ex && \
  find ${WGDASH}/static/dist -type f \( -name "*.html" -o -name "*.js" \) \
    -exec sed -i 's|/static/dist|./static/dist|g' {} \; && \
  find ${WGDASH}/static/dist -type f -name "*.css" \
    -exec sed -i \
    -e 's|/static/dist/WGDashboardAdmin/assets/|./|g' \
    -e 's|/static/dist/WGDashboardAdmin/img/|../img/|g' \
    -e 's|/static/dist/WGDashboardClient/assets/|./|g' \
    -e 's|/static/dist/WGDashboardClient/img/|../img/|g' {} \;

# Set a healthcheck to determine the container its health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

EXPOSE 10086

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
