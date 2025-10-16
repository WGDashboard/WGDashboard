#!/bin/bash

config_file="/data/wg-dashboard.ini"
WGD_PID_FILE="${WGDASH}/gunicorn.pid"
GUNICORN_PID=""
TAIL_PID=""

# Hash password with bcrypt
hash_password() {
  python3 -c "import bcrypt; print(bcrypt.hashpw('$1'.encode(), bcrypt.gensalt(12)).decode())"
}

# Function to set or update section/key/value in the INI file
set_ini() {
  local section="$1" key="$2" value="$3"
  local current_value

  # Add section if it doesn't exist
  grep -q "^\[${section}\]" "$config_file" \
    || printf "\n[%s]\n" "${section}" >> "$config_file"

  # Check current value if key exists
  if grep -q "^[[:space:]]*${key}[[:space:]]*=" "$config_file"; then
    current_value=$(grep "^[[:space:]]*${key}[[:space:]]*=" "$config_file" | cut -d= -f2- | xargs)

    # Don't display actual value if it's a password field
    if [[ "$key" == *"password"* ]]; then
      if [ "$current_value" = "$value" ]; then
        echo "- $key is already set correctly (value hidden)"
        return 0
      fi
      sed -i "/^\[${section}\]/,/^\[/{s|^[[:space:]]*${key}[[:space:]]*=.*|${key} = ${value}|}" "$config_file"
      echo "- Updated $key (value hidden)"
    else
      if [ "$current_value" = "$value" ]; then
        echo "- $key is already set correctly ($value)"
        return 0
      fi
      sed -i "/^\[${section}\]/,/^\[/{s|^[[:space:]]*${key}[[:space:]]*=.*|${key} = ${value}|}" "$config_file"
      echo "- Updated $key to: $value"
    fi
  else
    sed -i "/^\[${section}\]/a ${key} = ${value}" "$config_file"

    # Don't display actual value if it's a password field
    if [[ "$key" == *"password"* ]]; then
      echo "- Added new setting $key (value hidden)"
    else
      echo "- Added new setting $key: $value"
    fi
  fi
}

echo "------------------------- START ----------------------------"
echo "Starting the WGDashboard Docker container."

ensure_installation() {
  echo "Quick-installing..."

  cd "${WGDASH}" || exit

  # Github issue: https://github.com/donaldzou/WGDashboard/issues/723
  echo "Checking for stale pids..."
  if [[ -f "$WGD_PID_FILE" ]]; then
    echo "Found stale pid, removing..."
    rm "$WGD_PID_FILE"
  fi

  # Create required directories and links
  if [ ! -d "/data/db" ]; then
    echo "Creating database dir"
    mkdir -p /data/db
  fi

  if [ ! -d "${WGDASH}/db" ]; then
    ln -s /data/db "${WGDASH}/db"
  fi

  if [ ! -f "${config_file}" ]; then
    echo "Creating wg-dashboard.ini file"
    touch "${config_file}"
  fi

  if [ ! -f "${WGDASH}/wg-dashboard.ini" ]; then
    ln -s "${config_file}" "${WGDASH}/wg-dashboard.ini"
  fi

  echo "Looks like the installation succeeded. Moving on."

  # Setup WireGuard if needed
  if [ -z "$(ls -A /etc/wireguard)" ]; then
    cp -a "/configs/wg0.conf.template" "/etc/wireguard/wg0.conf"

    echo "Setting a secure private key."
    local privateKey
    privateKey=$(wg genkey)
    sed -i "s|^PrivateKey *=.*$|PrivateKey = ${privateKey}|g" /etc/wireguard/wg0.conf

    echo "Done setting template."
  else
    echo "Existing Wireguard configuration file found in /etc/wireguard."
  fi
}

set_envvars() {
  printf "\n------------- SETTING ENVIRONMENT VARIABLES ----------------\n"

  # Check if config file is empty
  if [ ! -s "${config_file}" ]; then
    echo "Config file is empty. Creating initial structure."
  fi

  echo "Checking basic configuration:"
  set_ini Peers peer_global_dns "${global_dns}"

  if [ -z "${public_ip}" ]; then
    public_ip=$(curl -s ifconfig.me)
    echo "Automatically detected public IP: ${public_ip}" 
  fi

  set_ini Peers remote_endpoint "${public_ip}"
  set_ini Server app_port "${wgd_port}"
  set_ini Server log_level "${log_level}"
  
  # Account settings - process all parameters
  [[ -n "$username" ]] && echo "Configuring user account:"
  # Basic account variables
  [[ -n "$username" ]] && set_ini Account username "${username}"

  if [[ -n "$password" ]]; then
    echo "- Setting password"
    set_ini Account password "$(hash_password "${password}")"
  fi

  # Additional account variables
  [[ -n "$enable_totp" ]] && set_ini Account enable_totp "${enable_totp}"
  [[ -n "$totp_verified" ]] && set_ini Account totp_verified "${totp_verified}"
  [[ -n "$totp_key" ]] && set_ini Account totp_key "${totp_key}"

  # Welcome session
  [[ -n "$welcome_session" ]] && set_ini Other welcome_session "${welcome_session}"
  # If username and password are set but welcome_session isn't, disable it
  if [[ -n "$username" && -n "$password" && -z "$welcome_session" ]]; then
    set_ini Other welcome_session "false"
  fi

  # Autostart WireGuard
  if [[ -n "$wg_autostart" ]]; then
    echo "Configuring WireGuard autostart:"
    set_ini WireGuardConfiguration autostart "${wg_autostart}"
  fi

  # Email (check if any settings need to be configured)
  email_vars=("email_server" "email_port" "email_encryption" "email_username" "email_password" "email_from" "email_template")
  for var in "${email_vars[@]}"; do
    if [ -n "${!var}" ]; then
      echo "Configuring email settings:"
      break
    fi
  done

  # Email (iterate through all possible fields)
  email_fields=("server:email_server" "port:email_port" "encryption:email_encryption" 
                "username:email_username" "email_password:email_password" 
                "send_from:email_from" "email_template:email_template")

  for field_pair in "${email_fields[@]}"; do
    IFS=: read -r field var <<< "$field_pair"
    [[ -n "${!var}" ]] && set_ini Email "$field" "${!var}"
  done
}

start_service(){
  printf "\n---------------------- STARTING CORE -----------------------\n"

  # Due to some instances complaining about this, making sure its there every time.
  if [ ! -c /dev/net/tun ]; then
    mkdir -p /dev/net
    mknod /dev/net/tun c 10 200
    chmod 600 /dev/net/tun
  fi

  gunicorn --config ./gunicorn.conf.py &

  echo "Waiting for Gunicorn PID file..."
  local checkPIDExist=0
  local timeout=40
  local waited=0

  while [ $checkPIDExist -eq 0 ]; do
    if [[ -f "$WGD_PID_FILE" ]]; then
      checkPIDExist=1
      GUNICORN_PID="$(cat "$WGD_PID_FILE")"
      echo "Gunicorn PID file found, WGDashboard starting"
    else
      sleep 1
      waited=$((waited+1))
      if [ $waited -ge $timeout ]; then
        echo "Gunicorn PID file not found after $timeout seconds, exiting"
        exit 1
      fi
    fi
  done
  echo "WGDashboard started successfully (PID: $GUNICORN_PID)"
}

# Start service and monitor logs
monitor() {
  echo -e "\nEnsuring container continuation."

  # Find and monitor log file
  local logdir="${WGDASH}/log"
  latestErrLog=$(find "$logdir" -name "error_*.log" -type f -print | sort -r | head -n 1)

  # Only tail the logs if they are found
  if [ -n "$latestErrLog" ]; then
    tail -f "$latestErrLog" &
    TAIL_PID=$!
    echo "Tailing logs (PID: $TAIL_PID)"
    # Wait for the tail process to end.
    wait "$TAIL_PID"
  else
    echo "No log files found to tail. Something went wrong, exiting..."
    exit 1
  fi
}

stop_service() {
  echo "Stopping WGDashboard..."
  if [[ -f "$WGD_PID_FILE" ]]; then
    if kill -0 "$GUNICORN_PID" 2>/dev/null; then
      echo "Stopping Gunicorn (PID $GUNICORN_PID)..."
      kill -TERM "$GUNICORN_PID"
    fi
  fi

 if [[ -n "$TAIL_PID" ]] && kill -0 "$TAIL_PID" 2>/dev/null; then
    echo "Stopping log tail (PID $TAIL_PID)..."
    kill -TERM "$TAIL_PID"
    wait "$TAIL_PID"
  fi
  exit 0
}

trap 'stop_service' SIGTERM SIGINT

# Main execution flow
ensure_installation
set_envvars
start_service
monitor
