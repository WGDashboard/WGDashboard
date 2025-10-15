# WGDashboard Docker Explanation:
Author: @DaanSelen<br>

This document delves into how the WGDashboard Docker container has been built.<br>
Of course there are two stages (simply said), one before run-time and one at/after run-time.<br>
The `Dockerfile` describes how the container image is made, and the `entrypoint.sh` is executed after the container is started. <br>
In this example, [WireGuard](https://www.wireguard.com/) is integrated into the container itself, so it should be a run-and-go(/out-of-the-box) experience.<br>
For more details on the source-code specific to this Docker image, refer to the source files, they have lots of comments.

<br>
<img 
  src="https://wgdashboard-resources.tor1.cdn.digitaloceanspaces.com/Logos/Logo-2-Rounded-512x512.png" 
  alt="WG-Dashboard Logo" 
  title="WG-Dashboard Logo"
  style="display: block; margin: 0 auto;"
  width="150"
  height="150"
/>
<br>

To get the container running you either pull the pre-made image from a remote repository, there are 2 official options.<br>

- ghcr.io/wgdashboard/wgdashboard:<tag>
- docker.io/donaldzou/wgdashboard:<tag>

> tags should be either: latest, main, <version> or <commit-sha>.

From there either use the environment variables described below as parameters or use the Docker Compose file: `compose.yaml`.<br>
Be careful, the default generated WireGuard configuration file uses port 51820/udp. So make sure to use this port if you want to use it out of the box.<br>
Otherwise edit the configuration file in WGDashboard under `Configuration Settings` -> `Edit Raw Configuration File`.

> Otherwise you need to enter the container and edit: `/etc/wireguard/wg0.conf`.

# WGDashboard: 🐳 Docker Deployment Guide

To run the container, you can either pull the image from the Github Container Registry (ghcr.io), Docker Hub (docker.io) or build it yourself. The image is available at:

> `docker.io` is in most cases automatically resolved by the Docker application. Therefor you can ofter specify: `donaldzou/wgdashboard:latest`

### 🔧 Quick Docker Run Command

Here's an example to get it up and running quickly:

```bash
docker run -d \
  --name wgdashboard \
  --restart unless-stopped \
  -p 10086:10086/tcp \
  -p 51820:51820/udp \
  --cap-add NET_ADMIN \
  ghcr.io/wgdashboard/wgdashboard:latest
```

> ⚠️ The default WireGuard port is `51820/udp`. If you change this, update the `/etc/wireguard/wg0.conf` accordingly.

---

### 📦 Docker Compose Alternative

You can also use Docker Compose for easier configuration:

```yaml
services:
  wgdashboard:
    image: ghcr.io/wgdashboard/wgdashboard:latest
    restart: unless-stopped
    container_name: wgdashboard

    ports:
      - 10086:10086/tcp
      - 51820:51820/udp

    volumes:
      - aconf:/etc/amnezia/amneziawg
      - conf:/etc/wireguard
      - data:/data

    cap_add:
      - NET_ADMIN

volumes:
  aconf:
  conf:
  data:
```

> 📁 You can customize the **volume paths** on the host to fit your needs. The example above uses Docker volumes.

---

## 🔄 Updating the Container

Updating the WGDashboard container should be through 'The Docker Way' - by pulling the newest/newer image and replacing this old one.

---

## ⚙️ Environment Variables

| Variable           | Accepted Values                          | Default                 | Example               | Description                                                             |
| ------------------ | ---------------------------------------- | ----------------------- | --------------------- | ----------------------------------------------------------------------- |
| `tz`               | Timezone                                 | `Europe/Amsterdam`      | `America/New_York`    | Sets the container's timezone. Useful for accurate logs and scheduling. |
| `global_dns`       | IPv4 and IPv6 addresses                  | `9.9.9.9`               | `8.8.8.8`, `1.1.1.1`  | Default DNS for WireGuard clients.                                      |
| `public_ip`        | Public IP address                        | Retrieved automatically | `253.162.134.73`      | Used to generate accurate client configs. Needed if container is NAT’d. |
| `wgd_port`         | Any port that is allowed for the process | `10086`                 | `443`                 | This port is used to set the WGDashboard web port.                      |
| `log_level`        | `DEBUG`, `INFO`, `WARNING`, `ERROR` and `CRITICAL` | `INFO`        | `WARNING`             | Sets the severity of the logs being displayed.                          |        
| `username`         | Any non‐empty string                     | `-`                     | `admin`               | Username for the WGDashboard web interface account.                     |
| `password`         | Any non‐empty string                     | `-`                     | `s3cr3tP@ss`          | Password for the WGDashboard web interface account (stored hashed).     |
| `enable_totp`      | `true`, `false`                          | `true`                  | `false`               | Enable TOTP‐based two‐factor authentication for the account.            |
| `wg_autostart`     | Wireguard interface name                 | `false`                 | `true`                | Auto‐start the WireGuard client when the container launches.            |
| `email_server`     | SMTP server address                      | `-`                     | `smtp.gmail.com`      | SMTP server for sending email notifications.                            |
| `email_port`       | SMTP port number                         | `-`                     | `587`                 | Port for connecting to the SMTP server.                                 |
| `email_encryption` | `TLS`, `SSL`, etc.                       | `-`                     | `TLS`                 | Encryption method for email communication.                              |
| `email_username`   | Any non-empty string                     | `-`                     | `user@example.com`    | Username for SMTP authentication.                                       |
| `email_password`   | Any non-empty string                     | `-`                     | `app_password`        | Password for SMTP authentication.                                       |
| `email_from`       | Valid email address                      | `-`                     | `noreply@example.com` | Email address used as the sender for notifications.                     |
| `email_template`   | Path to template file                    | `-`                     | `your-template`       | Custom template for email notifications.                                |

---

## 🔐 Port Forwarding Note

When using multiple WireGuard interfaces, remember to **open their respective ports** on the host.

Examples:
```yaml
# Individual mapping
- 51821:51821/udp

# Or port range
- 51820-51830:51820-51830/udp
```

> 🚨 **Security Tip:** Only expose ports you actually use.

---

## 🛠️ Building the Image Yourself

To build from source:

```bash
git clone https://github.com/WGDashboard/WGDashboard.git
cd WGDashboard
docker build . -f docker/Dockerfile -t yourname/wgdashboard:latest
```

Example output:
```shell
docker images

REPOSITORY           TAG       IMAGE ID       CREATED             SIZE
yourname/wgdashboard latest    c96fd96ee3b3   42 minutes ago      314MB
```

---

## 🧱 Dockerfile Overview

Here's a brief overview of the Dockerfile stages used in the image build:

### 1. **Build Tools & Go Compilation**

```Dockerfile
FROM golang:1.24 AS compiler
WORKDIR /go

RUN apt-get update && apt-get install -y ...
RUN git clone ... && make
...
```

### 2. **Binary Copy to Scratch**

```Dockerfile
FROM scratch AS bins
COPY --from=compiler /go/amneziawg-go/amneziawg-go /amneziawg-go
...
```

### 3. **Final Alpine Container Setup**

```Dockerfile
FROM alpine:latest
COPY --from=bins ...
RUN apk update && apk add --no-cache ...
COPY ./src ${WGDASH}/src
COPY ./docker/entrypoint.sh /entrypoint.sh
...
EXPOSE 10086
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
```

---

## 🚀 Entrypoint Overview

### Major Functions:

- **`ensure_installation`**: Sets up the app, database, and Python environment.
- **`set_envvars`**: Writes `wg-dashboard.ini` and applies environment variables.
- **`start_core`**: Starts the main WGDashboard service.
- **`ensure_blocking`**: Tails the error log to keep the container process alive.

---

## ✅ Final Notes

- Use `docker logs wgdashboard` for troubleshooting.
- Access the web interface via `http://your-ip:10086` (or whichever port you specified in the compose).
- The first time run will auto-generate WireGuard keys and configs (configs are generated from the template).

## Closing remarks:

For feedback please submit an issue to the repository. Or message dselen@nerthus.nl.
