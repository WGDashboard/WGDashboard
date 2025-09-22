#!/bin/bash

# wgd.sh - Copyright(C) 2024 Donald Zou [https://github.com/donaldzou]
# Under Apache-2.0 License
#trap "kill $TOP_PID"
export TOP_PID=$$

app_name="dashboard.py"
app_official_name="WGDashboard"
venv_python="./venv/bin/python3"
venv_gunicorn="./venv/bin/gunicorn"
pythonExecutable="python3"

heavy_checkmark=$(printf "\xE2\x9C\x85")
heavy_crossmark=$(printf "\xE2\x9D\x8C")
install=$(printf "\xF0\x9F\x92\xBF")

msleep=15

PID_FILE=./gunicorn.pid
environment=$(if [[ $ENVIRONMENT ]]; then echo $ENVIRONMENT; else echo 'develop'; fi)
if [[ $CONFIGURATION_PATH ]]; then
  cb_work_dir=$CONFIGURATION_PATH/letsencrypt/work-dir
  cb_config_dir=$CONFIGURATION_PATH/letsencrypt/config-dir
else
  cb_work_dir=/etc/letsencrypt
  cb_config_dir=/var/lib/letsencrypt
fi

dashes='---------------------------------------------------------------------------------'
equals='============================================================'
helpMsg="[WGDashboard] Please check ./log/install.txt for more details. For further assistance, please open a ticket on https://github.com/WGDashboard/WGDashboard/issues/new/choose, I'm more than happy to help :)"
print_header(){
	printf "=================================================================================\n"
	printf "+          <WGDashboard> by Donald Zou - https://github.com/donaldzou           +\n"
	printf "=================================================================================\n"
}

help () {
  printf "| Usage: ./wgd.sh <option>                                                      |\n"
  printf "|                                                                               |\n"
  printf "| Available options:                                                            |\n"
  printf "|    start: To start WGDashboard.                                               |\n"
  printf "|    stop: To stop WGDashboard.                                                 |\n"
  printf "|    debug: To start WGDashboard in debug mode (i.e run in foreground).         |\n"
  printf "|    update: To update WGDashboard to the newest version from GitHub.           |\n"
  printf "|    install: To install WGDashboard.                                           |\n"
  printf "| Thank you for using! Your support is my motivation ;)                         |\n"
  printf "=================================================================================\n"
}

_check_and_set_venv(){
    VIRTUAL_ENV="./venv"
    if [ ! -d $VIRTUAL_ENV ]; then
    	printf "[WGDashboard] %s Creating Python Virtual Environment under ./venv\n" "$install"
        { $pythonExecutable -m venv $VIRTUAL_ENV; } >> ./log/install.txt
    fi
    
    if ! $venv_python --version > /dev/null 2>&1
    then
    	printf "[WGDashboard] %s Python Virtual Environment under ./venv failed to create. Halting now.\n" "$heavy_crossmark"	
    	kill $TOP_PID
    fi
    
    . ${VIRTUAL_ENV}/bin/activate
}

_determineOS(){
	if [ -f /etc/os-release ]; then
		. /etc/os-release
		OS=$ID
	elif [ -f /etc/redhat-release ]; then
		OS="redhat"
	else
		printf "[WGDashboard] %s Sorry, your OS is not supported. Currently the install script only support Debian-based, Red Hat-based OS. With experimental support for Alpine Linux.\n" "$heavy_crossmark"
		printf "%s\n" "$helpMsg"
		kill  $TOP_PID
	fi
	printf "[WGDashboard] OS: %s\n" "$OS"
}

_installPython(){
	{ printf "\n\n [Installing Python] [%s] \n\n""$(date)"; } >> ./log/install.txt 
	printf "[WGDashboard] %s Installing Python\n" "$install"
	case "$OS" in
		ubuntu|debian|raspbian)
			{ sudo apt update ; sudo apt-get install -y python3 net-tools; printf "\n\n"; } >> ./log/install.txt 
		;;
		centos|fedora|redhat|rhel|almalinux|rocky)
			if command -v dnf &> /dev/null; then
				{ sudo dnf install -y python3 net-tools; printf "\n\n"; } >> ./log/install.txt
			else
				{ sudo yum install -y python3 net-tools ; printf "\n\n"; } >> ./log/install.txt
			fi
		;;
		alpine)
			{ sudo apk update; sudo apk add python3 net-tools --no-cache; printf "\n\n"; } &>> ./log/install.txt
		;;
		arch)
			{ sudo pacman -Syu python3 net-tools; printf "\n\n"; } &>> ./log/install.txt
		;;
	esac
	
	if ! python3 --version > /dev/null 2>&1
	then
		printf "[WGDashboard] %s Python is still not installed, halting script now.\n" "$heavy_crossmark"
		printf "%s\n" "$helpMsg"
		kill  $TOP_PID
	else
		printf "[WGDashboard] %s Python is installed\n" "$heavy_checkmark"
	fi
}

_installPythonVenv(){
	{ printf "\n\n [Installing Python Venv] [%s] \n\n""$(date)"; } >> ./log/install.txt 
	printf "[WGDashboard] %s Installing Python Virtual Environment\n" "$install"
	if [ "$pythonExecutable" = "python3" ]; then
		case "$OS" in
			ubuntu|debian|raspbian)
				{ sudo apt update ; sudo apt-get install -y python3-venv; printf "\n\n"; } &>> ./log/install.txt
			;;
			centos|fedora|redhat|rhel|almalinux|rocky)
				if command -v dnf &> /dev/null; then
					{ sudo dnf install -y python3-virtualenv; printf "\n\n"; } >> ./log/install.txt
				else
					{ sudo yum install -y python3-virtualenv; printf "\n\n"; } >> ./log/install.txt
				fi
			;;
			alpine)
				{ sudo apk update; sudo apk add py3-virtualenv ; printf "\n\n"; } >> ./log/install.txt
			;;
			arch)
				{ echo "Python Virtual Environment is installed by default from version Python3.3"; printf "\n\n"; } &>> ./log/install.txt # https://wiki.archlinux.org/title/Python/Virtual_environment
			;;
			*)
				printf "[WGDashboard] %s Sorry, your OS is not supported. Currently the install script only support Debian-based, Red Hat-based OS. With experimental support for Alpine Linux.\n" "$heavy_crossmark"
				printf "%s\n" "$helpMsg"
				kill  $TOP_PID
			;;
		esac
	else
		case "$OS" in
			ubuntu|debian|raspbian)
				{ sudo apt-get update; sudo apt-get install ${pythonExecutable}-venv;  } &>> ./log/install.txt
			;;
		esac
	fi
	
	if ! $pythonExecutable -m venv -h > /dev/null 2>&1
	then
		printf "[WGDashboard] %s Python Virtual Environment is still not installed, halting script now.\n" "$heavy_crossmark"
		printf "%s\n" "$helpMsg"
	else
		printf "[WGDashboard] %s Python Virtual Environment is installed\n" "$heavy_checkmark"
	fi
}

_installPythonPip(){
	{ printf "\n\n [Installing Python Pip] [%s] \n\n""$(date)"; } >> ./log/install.txt 
	
	if ! $pythonExecutable -m pip -h > /dev/null 2>&1
	then
		printf "[WGDashboard] %s Installing Python Package Manager (PIP)\n" "$install"
		case "$OS" in
			ubuntu|debian|raspbian)
				if [ "$pythonExecutable" = "python3" ]; then
					{ sudo apt update ; sudo apt-get install -y python3-pip; printf "\n\n"; } &>> ./log/install.txt
				else
					{ sudo apt update ; sudo apt-get install -y ${pythonExecutable}-distutil python3-pip; printf "\n\n"; } &>> ./log/install.txt
				fi
			;;
			centos|fedora|redhat|rhel|almalinux|rocky)
				if [ "$pythonExecutable" = "python3" ]; then
					{ sudo dnf install -y python3-pip; printf "\n\n"; } >> ./log/install.txt
				else
					{ sudo dnf install -y ${pythonExecutable}-pip; printf "\n\n"; } >> ./log/install.txt
				fi
			;;
			alpine)
				{ sudo apk update; sudo apk add py3-pip --no-cache; printf "\n\n"; } >> ./log/install.txt
			;;
			arch)
				{ sudo pacman -Syu python-pip; printf "\n\n"; } &>> ./log/install.txt
			;;
			*)
				printf "[WGDashboard] %s Sorry, your OS is not supported. Currently the install script only support Debian-based, Red Hat-based OS. With experimental support for Alpine Linux.\n" "$heavy_crossmark"
				printf "%s\n" "$helpMsg"
				kill  $TOP_PID
			;;
		esac
    fi
    	
	if ! $pythonExecutable -m pip -h > /dev/null 2>&1
	then
		printf "[WGDashboard] %s Python Package Manager (PIP) is still not installed, halting script now.\n" "$heavy_crossmark"
		printf "%s\n" "$helpMsg"
		kill  $TOP_PID
	else
		printf "[WGDashboard] %s Python Package Manager (PIP) is installed\n" "$heavy_checkmark"
	fi
}

_checkWireguard(){
    if ! command -v wg > /dev/null 2>&1 || ! command -v wg-quick > /dev/null 2>&1
    then
    	printf "[WGDashboard] %s Installing WireGuard\n" "$install"
        case "$OS" in
            ubuntu|debian|raspbian)
                { 
                    sudo apt update && sudo apt-get install -y wireguard; 
                    printf "\n[WGDashboard] WireGuard installed on %s.\n\n" "$OS"; 
                } &>> ./log/install.txt
                printf "[WGDashboard] %s WireGuard is successfully installed.\n" "$heavy_checkmark"
            ;;
            centos|fedora|redhat|rhel|almalinux|rocky)
                { 
                    sudo dnf install -y wireguard-tools;
                    printf "\n[WGDashboard] WireGuard installed on %s.\n\n" "$OS"; 
                } &>> ./log/install.txt
                printf "[WGDashboard] %s WireGuard is successfully installed.\n" "$heavy_checkmark"
            ;;
            alpine)
                { 
                    sudo apk update && sudo apk add wireguard-tools --no-cache;
                    printf "\n[WGDashboard] WireGuard installed on %s.\n\n" "$OS"; 
                } &>> ./log/install.txt
                printf "[WGDashboard] %s WireGuard is successfully installed.\n" "$heavy_checkmark"
            ;;
			arch)
				{ 
					sudo pacman -Syu wireguard-tools; printf "\n\n"; 
				} &>> ./log/install.txt
				printf "[WGDashboard] %s WireGuard is successfully installed.\n" "$heavy_checkmark"
			;;
            *)
                printf "[WGDashboard] %s Sorry, your OS is not supported. Currently, the install script only supports Debian-based, Red Hat-based, and Alpine Linux.\n" "$heavy_crossmark"
                printf "%s\n" "$helpMsg"
                kill $TOP_PID
            ;;
        esac
    else
        printf "[WGDashboard] %s WireGuard is already installed.\n" "$heavy_checkmark"
    fi
}




_checkPythonVersion(){
	version_pass=$($pythonExecutable -c 'import sys; print("1") if (sys.version_info.major == 3 and sys.version_info.minor >= 10) else print("0");')
	version=$($pythonExecutable --version)
	if [ $version_pass == "1" ]
	  	then 
	  		printf "[WGDashboard] %s Found compatible version of Python. Will be using %s to install WGDashboard.\n" "$heavy_checkmark" "$($pythonExecutable --version)"
			return;
	elif python3.10 --version > /dev/null 2>&1
		then
	 		printf "[WGDashboard] %s Found Python 3.10. Will be using [python3.10] to install WGDashboard.\n" "$heavy_checkmark"
	 		pythonExecutable="python3.10"
	elif python3.11 --version > /dev/null 2>&1
    	 then
    	 	printf "[WGDashboard] %s Found Python 3.11. Will be using [python3.11] to install WGDashboard.\n" "$heavy_checkmark"
    	 	pythonExecutable="python3.11"
    elif python3.12 --version > /dev/null 2>&1
    	 then
    	 	printf "[WGDashboard] %s Found Python 3.12. Will be using [python3.12] to install WGDashboard.\n" "$heavy_checkmark"
    	 	pythonExecutable="python3.12"
	else
		printf "[WGDashboard] %s Could not find a compatible version of Python. Current Python is %s.\n" "$heavy_crossmark" "$version"
		printf "[WGDashboard] WGDashboard required Python 3.10, 3.11 or 3.12. Halting install now.\n"
		kill $TOP_PID
	fi
}

_determinePypiMirror(){
	printf "[WGDashboard] %s Pinging list of recommended Python Package Index mirror\n" "$install"
	urls=(
		"https://pypi.org/simple/"
		"https://pypi.tuna.tsinghua.edu.cn/simple/"
		"https://pypi.mirrors.ustc.edu.cn/simple/"
		"https://mirrors.aliyun.com/pypi/simple/"
		"https://pypi.douban.com/simple/"
	)

	# Function to extract hostname and ping it
	index=1
	printf "              ---------------------------------------------------------\n"
	for url in "${urls[@]}"; do
		# Extract the hostname from the URL
		hostname=$(echo "$url" | awk -F/ '{print $3}')
		# Ping the hostname once and extract the RTT
		rtt=$(ping -c 1 -W 1 "$hostname" 2>/dev/null | grep 'time=' | awk -F'time=' '{print $2}' | awk '{print $1}')
		# Handle cases where the hostname is not reachable
		if [ -z "$rtt" ]; then
			rtt="9999"
			printf "              [%i] [FAILED] %s\n" "$index" "$url"
		else
			rtt=${rtt//.*/}
			printf "              [%i] %sms %s\n" "$index" "$rtt" "$url"
		fi
		rtthost[$index]=$rtt
		index=$((index+1))
	done
	printf "              ---------------------------------------------------------\n"
	for i in "${!rtthost[@]}"; do
		[[ -z ${rtthost[i]} ]] && continue  # Skip unset or empty values
		if [[ -z $min_val || ${rtthost[i]} -lt $min_val ]]; then
			min_val=${rtthost[i]}
			min_idx=$i
		fi
	done
	min_idx=$((min_idx - 1))
	
	printf "              Which mirror you would like to use (Hit enter to use default)\n"
	printf "              Default is %s :" "${urls[$min_idx]}"
	read -t ${msleep} -r choice
	printf "\n"

	if [[ -z "$choice" ]]; then
		choice=$((min_idx + 1))
	fi

	if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#urls[@]} )); then
		selected_url="${urls[choice-1]}"
		printf "[WGDashboard] %s Will download Python packages from %s\n" "$heavy_checkmark" "$selected_url"
	else
		selected_url="${urls[0]}"
		printf "[WGDashboard] %s Will download Python packages from %s\n" "$heavy_checkmark" "${urls[0]}"
	fi
}

install_wgd(){
    printf "[WGDashboard] Starting to install WGDashboard\n"
    _determineOS
    
	if [ ! -d "log" ] 
	then 
			mkdir "log"
			printf "[WGDashboard] %s Created ./log folder\n" "$heavy_checkmark"
	else
		printf "[WGDashboard] %s Found existing ./log folder\n" "$heavy_checkmark"
	fi
	
	if [ ! -d "download" ]
	then 
		mkdir "download"
		printf "[WGDashboard] %s Created ./download folder\n" "$heavy_checkmark"
	else
		printf "[WGDashboard] %s Found existing ./download folder\n" "$heavy_checkmark"
	fi
    
    if [ ! -d "db" ] 
	then 
		mkdir "db"
		printf "[WGDashboard] %s Created ./db folder\n" "$heavy_checkmark"
	else
		printf "[WGDashboard] %s Found existing ./db folder\n" "$heavy_checkmark"
	fi
    
    if ! python3 --version > /dev/null 2>&1
    then
    	printf "[WGDashboard] Python is not installed, trying to install now\n"
    	_installPython
    else
    	printf "[WGDashboard] %s Python is installed\n" "$heavy_checkmark"
    fi
    
    _determinePypiMirror
    _checkPythonVersion
    _installPythonVenv
    _installPythonPip
	_checkWireguard
    sudo chmod -R 755 /etc/wireguard/
    
    _check_and_set_venv
    printf "[WGDashboard] %s Upgrading Python Package Manage (PIP)\n" "$install"
	{ date; python3 -m ensurepip --upgrade; printf "\n\n"; } >> ./log/install.txt
    { date; python3 -m pip install --upgrade pip -i "$selected_url"; printf "\n\n"; } >> ./log/install.txt
    printf "[WGDashboard] %s Installing latest Python dependencies\n" "$install"
	{ date; python3 -m pip install -r requirements.txt  -i "$selected_url"; printf "\n\n"; } >> ./log/install.txt #This all works on the default installation.
    
      
	if [ ! -f "ssl-tls.ini" ]
		then
			printf "[SSL/TLS]\ncertificate_path = \nprivate_key_path = \n" >> ssl-tls.ini
			printf "[WGDashboard] %s Created ssl-tls.ini\n" "$heavy_checkmark"
	else
			printf "[WGDashboard] %s Found existing ssl-tls.ini\n" "$heavy_checkmark"
	fi
    printf "[WGDashboard] %s WGDashboard installed successfully!\n" "$heavy_checkmark"
    printf "[WGDashboard] Enter ./wgd.sh start to start the dashboard\n"
}

check_wgd_status(){
  if test -f "$PID_FILE"; then
    if ps aux | grep -v grep | grep $(cat ./gunicorn.pid)  > /dev/null; then
    return 0
    else
      return 1
    fi
  else
    if ps aux | grep -v grep | grep '[p]ython3 '$app_name > /dev/null; then
      return 0
    else
      return 1
    fi
  fi
}

certbot_create_ssl () {
	certbot certonly --config ./certbot.ini --email "$EMAIL" --work-dir $cb_work_dir --config-dir $cb_config_dir --domain "$SERVERURL"
}

certbot_renew_ssl () {
	certbot renew --work-dir $cb_work_dir --config-dir $cb_config_dir
}

gunicorn_start () {
  printf "[WGDashboard] Starting WGDashboard with Gunicorn in the background.\n"
  d=$(date '+%Y%m%d%H%M%S')
  if [[ $USER == root ]]; then
    export PATH=$PATH:/usr/local/bin:$HOME/.local/bin
  fi
  _check_and_set_venv
  sudo "$venv_gunicorn" --config ./gunicorn.conf.py
  sleep 5
  checkPIDExist=0
  while [ $checkPIDExist -eq 0 ]
  do
  		if test -f './gunicorn.pid'; then
  			checkPIDExist=1
  			printf "[WGDashboard] Checking if WGDashboard w/ Gunicorn started successfully\n"
  		fi
  		sleep 2
  done
  printf "[WGDashboard] WGDashboard w/ Gunicorn started successfully\n"
}

gunicorn_stop () {
	checkPIDExist=1
	while [ $checkPIDExist -eq 1 ]
	do
		if test -f "$PID_FILE"; then
			printf "[WGDashboard] Stopping WGDashboard w/ Gunicorn on PID %s\n" "$(cat ./gunicorn.pid)"
			sudo kill "$(cat ./gunicorn.pid)"
		else
			checkPIDExist=0
		fi
		sleep 2
	done
	printf "[WGDashboard] WGDashboard is stopped.\n"
}

start_wgd () {
	_checkWireguard
    gunicorn_start
}

stop_wgd() {
	if test -f "$PID_FILE"; then
		gunicorn_stop
	else
		kill "$(ps aux | grep "[p]ython3 $app_name" | awk '{print $2}')"
	fi
}

start_wgd_debug() {
	_checkWireguard
	printf "[WGDashboard] Starting WGDashboard in the foreground.\n"
	sudo "$venv_python" "$app_name"
}

update_wgd() {
	_determineOS
	if ! python3 --version > /dev/null 2>&1
	then
		printf "[WGDashboard] Python is not installed, trying to install now\n"
		_installPython
	else
		printf "[WGDashboard] %s Python is installed\n" "$heavy_checkmark"
	fi
	
	_checkPythonVersion
	_installPythonVenv
	_installPythonPip	
	
	new_ver=$($venv_python -c "import json; import urllib.request; data = urllib.request.urlopen('https://api.github.com/repos/WGDashboard/WGDashboard/releases/latest').read(); output = json.loads(data);print(output['tag_name'])")

	if [ "$commandConfirmed" = "true" ]; then
		printf "[WGDashboard] Confirmation granted.\n"
		up="Y"
	else
		printf "[WGDashboard] Are you sure you want to update to the %s? (Y/N): " "$new_ver"
		read up
	fi

	if [ "$up" = "Y" ] || [ "$up" = "y" ]; then
		printf "[WGDashboard] Shutting down WGDashboard\n"

		if check_wgd_status; then
			stop_wgd
		fi

		mv wgd.sh wgd.sh.old
		printf "[WGDashboard] Downloading %s from GitHub..." "$new_ver"
		{ date; git stash; git pull https://github.com/WGDashboard/WGDashboard.git $new_ver --force; } >> ./log/update.txt
		chmod +x ./wgd.sh
		sudo ./wgd.sh install
		printf "[WGDashboard] Update completed!\n"
		rm wgd.sh.old
	else
		printf "[WGDashboard] Update Canceled.\n"
	fi
}


print_header
if [ "$#" -lt 1 ]; then
	help
else
	if [ "$2" = "-y" ] || [ "$2" = "-Y" ]; then
		commandConfirmed="true"
	fi

	if [ "$1" = "start" ]; then
		if check_wgd_status; then
			printf "[WGDashboard] WGDashboard is already running.\n"
		else
			start_wgd
		fi
	elif [ "$1" = "stop" ]; then
		if check_wgd_status; then
			stop_wgd			
		else
			printf "[WGDashboard] WGDashboard is not running.\n"
		fi
	elif [ "$1" = "update" ]; then
		update_wgd
	elif [ "$1" = "install" ]; then
		install_wgd
	elif [ "$1" = "restart" ]; then
		if check_wgd_status; then
			stop_wgd
			start_wgd
		else
			start_wgd
		fi
	elif [ "$1" = "debug" ]; then
		if check_wgd_status; then
			printf "[WGDashboard] WGDashboard is already running.\n"
		else
			start_wgd_debug
		fi
	elif [ "$1" = "os" ]; then
    		_determineOS
    elif [ "$1" = "ping" ]; then
        	_determinePypiMirror
	else
		help
	fi
fi
printf "%s\n" "$dashes"
