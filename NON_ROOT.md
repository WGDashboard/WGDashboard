# Running WGDashboard as a non-root service user (advanced)

WGDashboard can run as a non-root service user if you:
- grant controlled `sudo` access for `wg` and `wg-quick`, and
- allow read/write access to the WireGuard configuration files.

This is an advanced setup. Make a backup before changing a live system.

## 1) Create a service user and group

```
sudo groupadd --system wgdashboard
sudo groupadd --system wireguard
sudo useradd --system --home-dir /opt/wgdashboard --shell /sbin/nologin \
  --gid wgdashboard --groups wireguard wgdashboard
```

## 2) Set permissions

```
# WGDashboard app directory
sudo chown -R wgdashboard:wgdashboard /opt/wgdashboard/src
sudo chmod 0750 /opt/wgdashboard/src
sudo chmod 0750 /opt/wgdashboard/src/log /opt/wgdashboard/src/db
sudo chmod 0600 /opt/wgdashboard/src/wg-dashboard.ini

# WireGuard config directory
sudo chgrp wireguard /etc/wireguard
sudo chmod 0750 /etc/wireguard
sudo chgrp wireguard /etc/wireguard/*.conf
sudo chmod 0660 /etc/wireguard/*.conf

# Keep private keys locked to root
sudo chown root:root /etc/wireguard/*.key
sudo chmod 0600 /etc/wireguard/*.key
```

## 3) Sudoers allowlist (required)

Determine the actual binary paths on your system:

```
command -v wg
command -v wg-quick
```

Create `/etc/sudoers.d/wgdashboard` using those exact paths:

```
Defaults:wgdashboard !requiretty
wgdashboard ALL=(root) NOPASSWD: /path/to/wg, /path/to/wg-quick
```

Validate:

```
sudo visudo -cf /etc/sudoers.d/wgdashboard
```

## 4) Systemd override

Create `/etc/systemd/system/wg-dashboard.service.d/override.conf`:

```
[Service]
Type=simple
PIDFile=
User=wgdashboard
Group=wgdashboard
SupplementaryGroups=wireguard
ExecStart=
ExecStart=/opt/wgdashboard/src/venv/bin/gunicorn --config /opt/wgdashboard/src/gunicorn.conf.py
ExecStop=
ExecStop=/bin/kill -TERM $MAINPID
ExecReload=
ExecReload=/bin/kill -HUP $MAINPID
```

Then reload and restart:

```
sudo systemctl daemon-reload
sudo systemctl restart wg-dashboard
```

## 5) Verify

```
systemctl status wg-dashboard
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:10819/
```

## Notes
- WGDashboard executes `wg` and `wg-quick`. This requires sudo when running as non-root.
- If you use AmneziaWG, ensure the corresponding binaries are available.
- If you use SELinux/AppArmor, add policy exceptions as needed.
