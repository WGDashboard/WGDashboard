#!/bin/bash

# ===========================================
# WireGuard Dashboard - GCP Deploy Tool
# ===========================================
#
# Usage:
#   ./run.sh deploy                     # Deploy new VM (interactive)
#   ./run.sh deploy --region us-west1   # Deploy to specific region
#   ./run.sh destroy                    # Remove VM
#   ./run.sh destroy --all              # Remove VM + firewall + IPs
#   ./run.sh status                     # Show VM status
#   ./run.sh ssh                        # Connect to VM
#   ./run.sh logs                       # View container logs
#   ./run.sh regions                    # List all regions
#   ./run.sh help                       # Show help

set -e

# ===========================================
# CONFIGURATION
# ===========================================

PROJECT_ID=""
DEFAULT_REGION="us-central1"
DEFAULT_NAME="wireguard-vpn"
DEFAULT_MACHINE_TYPE="e2-micro"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"

# Machine types with pricing (approximate monthly cost in USD)
# Format: "type:vCPUs:RAM:monthly_price:description"
MACHINE_TYPES=(
    "e2-micro:0.25 vCPU:1 GB:FREE:Free tier (1 instance/month)"
    "e2-small:0.5 vCPU:2 GB:\$12/mo:Good for personal use"
    "e2-medium:1 vCPU:4 GB:\$24/mo:Small teams (5-10 users)"
    "e2-standard-2:2 vCPUs:8 GB:\$48/mo:Medium teams (10-25 users)"
    "e2-standard-4:4 vCPUs:16 GB:\$96/mo:Large teams (25-50 users)"
    "e2-standard-8:8 vCPUs:32 GB:\$192/mo:Enterprise (50+ users)"
)

# Regions by area
AMERICAS_REGIONS=(
    "us-central1:Iowa, USA"
    "us-east1:South Carolina, USA"
    "us-east4:Virginia, USA"
    "us-east5:Columbus, USA"
    "us-west1:Oregon, USA"
    "us-west2:Los Angeles, USA"
    "us-west3:Salt Lake City, USA"
    "us-west4:Las Vegas, USA"
    "us-south1:Dallas, USA"
    "northamerica-northeast1:Montreal, Canada"
    "northamerica-northeast2:Toronto, Canada"
    "southamerica-east1:Sao Paulo, Brazil"
    "southamerica-west1:Santiago, Chile"
)

EUROPE_REGIONS=(
    "europe-west1:Belgium"
    "europe-west2:London, UK"
    "europe-west3:Frankfurt, Germany"
    "europe-west4:Netherlands"
    "europe-west6:Zurich, Switzerland"
    "europe-west8:Milan, Italy"
    "europe-west9:Paris, France"
    "europe-west10:Berlin, Germany"
    "europe-west12:Turin, Italy"
    "europe-north1:Finland"
    "europe-central2:Warsaw, Poland"
    "europe-southwest1:Madrid, Spain"
)

ASIA_REGIONS=(
    "asia-east1:Taiwan"
    "asia-east2:Hong Kong"
    "asia-northeast1:Tokyo, Japan"
    "asia-northeast2:Osaka, Japan"
    "asia-northeast3:Seoul, South Korea"
    "asia-south1:Mumbai, India"
    "asia-south2:Delhi, India"
    "asia-southeast1:Singapore"
    "asia-southeast2:Jakarta, Indonesia"
    "australia-southeast1:Sydney, Australia"
    "australia-southeast2:Melbourne, Australia"
)

MIDDLE_EAST_REGIONS=(
    "me-west1:Tel Aviv, Israel"
    "me-central1:Doha, Qatar"
    "me-central2:Dammam, Saudi Arabia"
    "africa-south1:Johannesburg, South Africa"
)

ALL_REGIONS=(
    "${AMERICAS_REGIONS[@]}"
    "${EUROPE_REGIONS[@]}"
    "${ASIA_REGIONS[@]}"
    "${MIDDLE_EAST_REGIONS[@]}"
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_SCRIPT="$DEPLOY_DIR/install.sh"

# ===========================================
# VARIABLES
# ===========================================

COMMAND=""
VM_NAME="$DEFAULT_NAME"
REGION="$DEFAULT_REGION"
ZONE=""
MACHINE_TYPE="$DEFAULT_MACHINE_TYPE"
FORCE=false
REMOVE_ALL=false
INTERACTIVE=true

# ===========================================
# HELPER FUNCTIONS
# ===========================================

print_header() {
    echo ""
    echo "=========================================="
    echo "  $1"
    echo "=========================================="
    echo ""
}

print_usage() {
    cat << 'EOF'
WireGuard Dashboard - GCP Deploy Tool

USAGE:
    ./run.sh <command> [options]

COMMANDS:
    deploy      Create VM and install WireGuard Dashboard
    destroy     Remove VM and optionally other resources
    status      Show current VM status and info
    ssh         SSH into the VM
    logs        View WireGuard Dashboard logs
    start       Start a stopped VM
    stop        Stop the VM (saves costs)
    regions     List all available regions
    help        Show this help message

DEPLOY OPTIONS:
    -r, --region REGION    GCP region (default: us-central1)
    -z, --zone ZONE        GCP zone (overrides region)
    -n, --name NAME        VM instance name (default: wireguard-vpn)
    -p, --project ID       GCP project ID (auto-detected)
    -t, --type TYPE        Machine type (default: e2-micro)

DESTROY OPTIONS:
    -a, --all              Remove VM + firewall rules + static IPs
    -f, --force            Skip confirmation prompts
    -n, --name NAME        VM instance name
    -p, --project ID       GCP project ID

EXAMPLES:
    ./run.sh deploy                           # Interactive deploy
    ./run.sh deploy --region europe-west3     # Deploy to Frankfurt
    ./run.sh deploy --region asia-northeast1  # Deploy to Tokyo
    ./run.sh status                           # Check VM status
    ./run.sh ssh                              # Connect to VM
    ./run.sh logs                             # View logs
    ./run.sh stop                             # Stop VM
    ./run.sh start                            # Start VM
    ./run.sh destroy                          # Remove VM only
    ./run.sh destroy --all --force            # Remove everything

EOF
}

check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        echo "ERROR: gcloud CLI not found"
        echo "Install: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1 | grep -q "@"; then
        echo "ERROR: Not logged into gcloud"
        echo "Run: gcloud auth login"
        exit 1
    fi
}

get_project() {
    if [ -n "$PROJECT_ID" ]; then
        return 0
    fi

    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

    if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
        echo ""
        echo "Available projects:"
        gcloud projects list --format="table(projectId,name)" 2>/dev/null | head -20
        echo ""
        read -p "Enter GCP Project ID: " PROJECT_ID

        if [ -z "$PROJECT_ID" ]; then
            echo "ERROR: Project ID is required"
            exit 1
        fi
    fi

    if ! gcloud projects describe "$PROJECT_ID" &>/dev/null; then
        echo "ERROR: Cannot access project '$PROJECT_ID'"
        exit 1
    fi
}

find_vm() {
    if [ -z "$ZONE" ]; then
        local vm_info=$(gcloud compute instances list \
            --project="$PROJECT_ID" \
            --filter="name=$VM_NAME" \
            --format="value(name,zone)" 2>/dev/null | head -1)

        if [ -z "$vm_info" ]; then
            return 1
        fi

        ZONE=$(echo "$vm_info" | awk '{print $2}' | rev | cut -d'/' -f1 | rev)
    else
        if ! gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
            return 1
        fi
    fi
    return 0
}

get_vm_ip() {
    gcloud compute instances describe "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --format="value(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null
}

get_zone_for_region() {
    gcloud compute zones list --filter="region:$1" --format="value(name)" 2>/dev/null | head -1
}

# ===========================================
# COMMAND: REGIONS
# ===========================================

cmd_regions() {
    print_header "AVAILABLE REGIONS"

    echo "AMERICAS:"
    for r in "${AMERICAS_REGIONS[@]}"; do
        printf "  %-28s (%s)\n" "${r%%:*}" "${r##*:}"
    done

    echo ""
    echo "EUROPE:"
    for r in "${EUROPE_REGIONS[@]}"; do
        printf "  %-28s (%s)\n" "${r%%:*}" "${r##*:}"
    done

    echo ""
    echo "ASIA PACIFIC:"
    for r in "${ASIA_REGIONS[@]}"; do
        printf "  %-28s (%s)\n" "${r%%:*}" "${r##*:}"
    done

    echo ""
    echo "MIDDLE EAST & AFRICA:"
    for r in "${MIDDLE_EAST_REGIONS[@]}"; do
        printf "  %-28s (%s)\n" "${r%%:*}" "${r##*:}"
    done

    echo ""
    echo "Usage: ./run.sh deploy --region <region-code>"
}

select_region() {
    print_header "SELECT REGION"

    local i=1

    echo "AMERICAS:"
    for r in "${AMERICAS_REGIONS[@]}"; do
        printf "  %2d) %-28s (%s)\n" $i "${r%%:*}" "${r##*:}"
        ((i++))
    done

    echo ""
    echo "EUROPE:"
    for r in "${EUROPE_REGIONS[@]}"; do
        printf "  %2d) %-28s (%s)\n" $i "${r%%:*}" "${r##*:}"
        ((i++))
    done

    echo ""
    echo "ASIA PACIFIC:"
    for r in "${ASIA_REGIONS[@]}"; do
        printf "  %2d) %-28s (%s)\n" $i "${r%%:*}" "${r##*:}"
        ((i++))
    done

    echo ""
    echo "MIDDLE EAST & AFRICA:"
    for r in "${MIDDLE_EAST_REGIONS[@]}"; do
        printf "  %2d) %-28s (%s)\n" $i "${r%%:*}" "${r##*:}"
        ((i++))
    done

    local total=${#ALL_REGIONS[@]}
    echo ""
    read -p "Select region [1-$total] (default: 1): " selection

    if [ -z "$selection" ]; then
        selection=1
    fi

    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "$total" ]; then
        local selected="${ALL_REGIONS[$((selection-1))]}"
        REGION="${selected%%:*}"
        echo "Selected: $REGION (${selected##*:})"
    else
        REGION="$DEFAULT_REGION"
    fi
}

select_machine_type() {
    print_header "SELECT MACHINE TYPE"

    echo "Available instance types:"
    echo ""
    printf "  %-3s %-16s %-10s %-8s %-12s %s\n" "#" "TYPE" "vCPUs" "RAM" "PRICE" "DESCRIPTION"
    printf "  %-3s %-16s %-10s %-8s %-12s %s\n" "---" "----------------" "----------" "--------" "------------" "-------------------------"

    local i=1
    for m in "${MACHINE_TYPES[@]}"; do
        IFS=':' read -r type vcpu ram price desc <<< "$m"
        if [ "$price" = "FREE" ]; then
            printf "  %-3s %-16s %-10s %-8s \033[32m%-12s\033[0m %s\n" "$i)" "$type" "$vcpu" "$ram" "$price" "$desc"
        else
            printf "  %-3s %-16s %-10s %-8s %-12s %s\n" "$i)" "$type" "$vcpu" "$ram" "$price" "$desc"
        fi
        ((i++))
    done

    local total=${#MACHINE_TYPES[@]}
    echo ""
    read -p "Select machine type [1-$total] (default: 1 - FREE): " selection

    if [ -z "$selection" ]; then
        selection=1
    fi

    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "$total" ]; then
        local selected="${MACHINE_TYPES[$((selection-1))]}"
        MACHINE_TYPE="${selected%%:*}"
        IFS=':' read -r type vcpu ram price desc <<< "$selected"
        echo "Selected: $MACHINE_TYPE ($vcpu, $ram) - $price"
    else
        MACHINE_TYPE="$DEFAULT_MACHINE_TYPE"
        echo "Using default: $MACHINE_TYPE"
    fi
}

# ===========================================
# COMMAND: DEPLOY
# ===========================================

cmd_deploy() {
    print_header "WIREGUARD VPN - DEPLOY"

    check_gcloud
    get_project

    echo "Project: $PROJECT_ID"

    if [ "$INTERACTIVE" = true ]; then
        select_region
        select_machine_type
    fi

    if [ -z "$ZONE" ]; then
        ZONE=$(get_zone_for_region "$REGION")
    fi

    echo ""
    echo "Configuration:"
    echo "  Project: $PROJECT_ID"
    echo "  Region:  $REGION"
    echo "  Zone:    $ZONE"
    echo "  VM Name: $VM_NAME"
    echo "  Type:    $MACHINE_TYPE"
    echo ""

    read -p "Continue? [Y/n]: " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        echo "Cancelled."
        exit 0
    fi

    # Create firewall rules
    print_header "CONFIGURING FIREWALL"
    if gcloud compute firewall-rules describe wireguard-vpn --project="$PROJECT_ID" &>/dev/null; then
        echo "OK: Firewall rule already exists"
    else
        echo "Creating firewall rule..."
        gcloud compute firewall-rules create wireguard-vpn \
            --project="$PROJECT_ID" \
            --direction=INGRESS \
            --priority=1000 \
            --network=default \
            --action=ALLOW \
            --rules=udp:51820,tcp:10086 \
            --source-ranges=0.0.0.0/0 \
            --target-tags=wireguard \
            --description="WireGuard VPN and Dashboard"
        echo "OK: Firewall rule created"
    fi

    # Create VM
    print_header "CREATING VM"
    if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
        echo "VM '$VM_NAME' already exists"
        read -p "Delete and recreate? [y/N]: " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            gcloud compute instances delete "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --quiet
        else
            echo "Using existing VM..."
        fi
    fi

    if ! gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
        echo "Creating VM..."
        gcloud compute instances create "$VM_NAME" \
            --project="$PROJECT_ID" \
            --zone="$ZONE" \
            --machine-type="$MACHINE_TYPE" \
            --image-family="$IMAGE_FAMILY" \
            --image-project="$IMAGE_PROJECT" \
            --boot-disk-size=10GB \
            --boot-disk-type=pd-standard \
            --can-ip-forward \
            --tags=wireguard

        echo "Waiting for VM to be ready..."
        sleep 30
    fi

    # Deploy WireGuard
    print_header "INSTALLING WIREGUARD"

    local vm_ip=$(get_vm_ip)
    echo "VM IP: $vm_ip"
    echo ""

    if [ ! -f "$INSTALL_SCRIPT" ]; then
        echo "ERROR: install.sh not found"
        exit 1
    fi

    echo "[1/5] Uploading install script..."
    echo "----------------------------------------"
    gcloud compute scp "$INSTALL_SCRIPT" "$VM_NAME:/tmp/install.sh" \
        --zone="$ZONE" --project="$PROJECT_ID"
    echo "----------------------------------------"
    echo ""

    echo "[2/5] Updating system packages..."
    echo "----------------------------------------"
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --command="
        sudo apt-get update
    "
    echo "----------------------------------------"
    echo ""

    echo "[3/5] Installing iptables-persistent..."
    echo "----------------------------------------"
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --command="
        export DEBIAN_FRONTEND=noninteractive
        export DEBCONF_NONINTERACTIVE_SEEN=true
        echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections
        echo iptables-persistent iptables-persistent/autosave_v6 boolean true | sudo debconf-set-selections
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
            -o Dpkg::Options::='--force-confdef' \
            -o Dpkg::Options::='--force-confold' \
            iptables-persistent netfilter-persistent || true
    "
    echo "----------------------------------------"
    echo ""

    echo "[4/5] Installing WireGuard Dashboard..."
    echo "----------------------------------------"
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --command="
        sudo bash /tmp/install.sh
    "
    echo "----------------------------------------"
    echo ""

    echo "[5/5] Saving firewall rules..."
    echo "----------------------------------------"
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --command="
        sudo netfilter-persistent save || true
    "
    echo "----------------------------------------"

    # Done
    print_header "DEPLOYMENT COMPLETE"

    echo "DASHBOARD:"
    echo "  URL:      http://$vm_ip:10086"
    echo "  User:     admin"
    echo "  Password: Test123"
    echo ""
    echo "WIREGUARD:"
    echo "  Endpoint: $vm_ip:51820"
    echo ""
    echo "COMMANDS:"
    echo "  ./run.sh status    # Check status"
    echo "  ./run.sh ssh       # Connect to VM"
    echo "  ./run.sh logs      # View logs"
    echo "  ./run.sh stop      # Stop VM"
    echo "  ./run.sh destroy   # Remove VM"
    echo ""
}

# ===========================================
# COMMAND: DESTROY
# ===========================================

cmd_destroy() {
    print_header "WIREGUARD VPN - DESTROY"

    check_gcloud
    get_project

    echo "Project: $PROJECT_ID"

    # Find VM
    if find_vm; then
        echo "Found VM: $VM_NAME in $ZONE"

        local vm_ip=$(get_vm_ip)
        echo "IP: $vm_ip"
        echo ""

        if [ "$FORCE" != true ]; then
            read -p "Delete VM '$VM_NAME'? [y/N]: " confirm
            if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
                echo "Skipped VM deletion"
            else
                echo "Deleting VM..."
                gcloud compute instances delete "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --quiet
                echo "OK: VM deleted"
            fi
        else
            echo "Deleting VM..."
            gcloud compute instances delete "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --quiet
            echo "OK: VM deleted"
        fi
    else
        echo "VM '$VM_NAME' not found"
    fi

    # Remove firewall and IPs if --all
    if [ "$REMOVE_ALL" = true ]; then
        echo ""
        if gcloud compute firewall-rules describe wireguard-vpn --project="$PROJECT_ID" &>/dev/null; then
            if [ "$FORCE" = true ]; then
                gcloud compute firewall-rules delete wireguard-vpn --project="$PROJECT_ID" --quiet
                echo "OK: Firewall rule deleted"
            else
                read -p "Delete firewall rule 'wireguard-vpn'? [y/N]: " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    gcloud compute firewall-rules delete wireguard-vpn --project="$PROJECT_ID" --quiet
                    echo "OK: Firewall rule deleted"
                fi
            fi
        fi

        # Check for static IPs
        local static_ips=$(gcloud compute addresses list --project="$PROJECT_ID" --filter="name~wireguard" --format="value(name,region)" 2>/dev/null)
        if [ -n "$static_ips" ]; then
            echo ""
            echo "Found static IPs:"
            echo "$static_ips"
            if [ "$FORCE" = true ]; then
                echo "$static_ips" | while read -r name region; do
                    [ -n "$name" ] && gcloud compute addresses delete "$name" --region="$region" --project="$PROJECT_ID" --quiet 2>/dev/null || true
                done
                echo "OK: Static IPs deleted"
            else
                read -p "Delete static IPs? [y/N]: " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo "$static_ips" | while read -r name region; do
                        [ -n "$name" ] && gcloud compute addresses delete "$name" --region="$region" --project="$PROJECT_ID" --quiet 2>/dev/null || true
                    done
                    echo "OK: Static IPs deleted"
                fi
            fi
        fi
    fi

    print_header "DESTROY COMPLETE"
    echo "To redeploy: ./run.sh deploy"
}

# ===========================================
# COMMAND: STATUS
# ===========================================

cmd_status() {
    print_header "WIREGUARD VPN - STATUS"

    check_gcloud
    get_project

    echo "Project: $PROJECT_ID"
    echo ""

    if find_vm; then
        local vm_ip=$(get_vm_ip)
        local status=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --format="value(status)" 2>/dev/null)

        echo "VM:"
        echo "  Name:   $VM_NAME"
        echo "  Zone:   $ZONE"
        echo "  Status: $status"
        echo "  IP:     $vm_ip"
        echo ""

        if [ "$status" = "RUNNING" ]; then
            echo "DASHBOARD:"
            echo "  URL: http://$vm_ip:10086"
            echo ""
            echo "WIREGUARD:"
            echo "  Endpoint: $vm_ip:51820"
        fi
    else
        echo "VM '$VM_NAME' not found in project"
        echo ""
        echo "To deploy: ./run.sh deploy"
    fi
}

# ===========================================
# COMMAND: SSH
# ===========================================

cmd_ssh() {
    check_gcloud
    get_project

    if ! find_vm; then
        echo "ERROR: VM '$VM_NAME' not found"
        exit 1
    fi

    echo "Connecting to $VM_NAME..."
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID"
}

# ===========================================
# COMMAND: LOGS
# ===========================================

cmd_logs() {
    check_gcloud
    get_project

    if ! find_vm; then
        echo "ERROR: VM '$VM_NAME' not found"
        exit 1
    fi

    echo "Fetching logs from $VM_NAME..."
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --command="cd /opt/wgdashboard && sudo docker-compose logs -f --tail=100"
}

# ===========================================
# COMMAND: START
# ===========================================

cmd_start() {
    check_gcloud
    get_project

    if ! find_vm; then
        echo "ERROR: VM '$VM_NAME' not found"
        exit 1
    fi

    echo "Starting $VM_NAME..."
    gcloud compute instances start "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID"
    echo "OK: VM started"

    sleep 10
    local vm_ip=$(get_vm_ip)
    echo ""
    echo "Dashboard: http://$vm_ip:10086"
}

# ===========================================
# COMMAND: STOP
# ===========================================

cmd_stop() {
    check_gcloud
    get_project

    if ! find_vm; then
        echo "ERROR: VM '$VM_NAME' not found"
        exit 1
    fi

    echo "Stopping $VM_NAME..."
    gcloud compute instances stop "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID"
    echo "OK: VM stopped (saves costs)"
}

# ===========================================
# ARGUMENT PARSING
# ===========================================

# Get command
COMMAND="${1:-}"
shift 2>/dev/null || true

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --region|-r)
            REGION="$2"
            INTERACTIVE=false
            shift 2
            ;;
        --zone|-z)
            ZONE="$2"
            REGION="${ZONE%-*}"
            INTERACTIVE=false
            shift 2
            ;;
        --name|-n)
            VM_NAME="$2"
            shift 2
            ;;
        --project|-p)
            PROJECT_ID="$2"
            shift 2
            ;;
        --type|-t)
            MACHINE_TYPE="$2"
            INTERACTIVE=false
            shift 2
            ;;
        --force|-f)
            FORCE=true
            shift
            ;;
        --all|-a)
            REMOVE_ALL=true
            shift
            ;;
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ===========================================
# MAIN
# ===========================================

case "$COMMAND" in
    deploy|install)
        cmd_deploy
        ;;
    destroy|uninstall|remove)
        cmd_destroy
        ;;
    status|info)
        cmd_status
        ;;
    ssh|connect)
        cmd_ssh
        ;;
    logs|log)
        cmd_logs
        ;;
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    regions|region)
        cmd_regions
        ;;
    help|--help|-h|"")
        print_usage
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run './run.sh help' for usage"
        exit 1
        ;;
esac
