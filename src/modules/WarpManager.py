import os
import platform
import subprocess
import urllib.request
import json
import logging

class WarpManager:
    @staticmethod
    def get_wgcf_path() -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bin_dir = os.path.join(base_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        return os.path.join(bin_dir, "wgcf")

    @classmethod
    def ensure_wgcf(cls) -> bool:
        wgcf_path = cls.get_wgcf_path()
        if os.path.exists(wgcf_path) and os.access(wgcf_path, os.X_OK):
            return True

        arch_map = {
            "x86_64": "amd64",
            "aarch64": "arm64",
            "armv7l": "armv7"
        }
        machine = platform.machine()
        arch = arch_map.get(machine, "amd64")
        
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/ViRb3/wgcf/releases/latest",
                headers={"User-Agent": "WGDashboard"}
            )
            with urllib.request.urlopen(req) as resp:
                release_info = json.loads(resp.read().decode())
            
            download_url = None
            for asset in release_info.get("assets", []):
                name = asset.get("name", "").lower()
                if f"linux_{arch}" in name:
                    download_url = asset.get("browser_download_url")
                    break
            
            if not download_url:
                return False

            urllib.request.urlretrieve(download_url, wgcf_path)
            os.chmod(wgcf_path, 0o755)
            return True
        except Exception as e:
            logging.error(f"Failed to download wgcf: {e}")
            return False

    @classmethod
    def register_warp(cls, license_key: str = None, name: str = "warp0", conf_dir: str = "/etc/wireguard") -> tuple[bool, str]:
        if not cls.ensure_wgcf():
            return False, "Failed to download or locate wgcf binary."

        wgcf_bin = cls.get_wgcf_path()
        work_dir = "/tmp/wgcf_work"
        os.makedirs(work_dir, exist_ok=True)
        acc_toml = os.path.join(work_dir, "wgcf-account.toml")
        if os.path.exists(acc_toml):
            os.remove(acc_toml)

        try:
            # Register device
            res = subprocess.run([wgcf_bin, "register", "--accept-tos"], cwd=work_dir, capture_output=True, text=True)
            if res.returncode != 0 and "account already exists" not in res.stderr.lower():
                return False, f"wgcf register failed: {res.stderr or res.stdout}"

            # Apply license key if provided
            if license_key:
                env = os.environ.copy()
                env["WGCF_LICENSE_KEY"] = license_key.strip()
                res = subprocess.run([wgcf_bin, "update"], cwd=work_dir, env=env, capture_output=True, text=True)
                if res.returncode != 0:
                    return False, f"wgcf update license failed: {res.stderr or res.stdout}"

            # Generate profile
            res = subprocess.run([wgcf_bin, "generate"], cwd=work_dir, capture_output=True, text=True)
            if res.returncode != 0:
                return False, f"wgcf generate failed: {res.stderr or res.stdout}"

            gen_conf = os.path.join(work_dir, "wgcf-profile.conf")
            if not os.path.exists(gen_conf):
                return False, "wgcf-profile.conf was not created."

            target_conf = os.path.join(conf_dir, f"{name}.conf")
            os.makedirs(conf_dir, exist_ok=True)
            
            # Modify or place configuration
            with open(gen_conf, "r") as f:
                content = f.read()

            with open(target_conf, "w") as f:
                f.write(content)

            return True, f"WARP interface configuration written to {target_conf}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def attach_outband(wg_conf_path: str, warp_iface: str = "warp0") -> tuple[bool, str]:
        if not os.path.exists(wg_conf_path):
            return False, f"Configuration file {wg_conf_path} does not exist."

        post_up = f"iptables -A FORWARD -i %i -o {warp_iface} -j ACCEPT; iptables -t nat -A POSTROUTING -o {warp_iface} -j MASQUERADE"
        post_down = f"iptables -D FORWARD -i %i -o {warp_iface} -j ACCEPT; iptables -t nat -A POSTROUTING -o {warp_iface} -j MASQUERADE"

        with open(wg_conf_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        in_interface = False
        post_up_exists = False
        post_down_exists = False

        for line in lines:
            if line.strip().startswith("[Interface]"):
                in_interface = True
            elif line.strip().startswith("[") and not line.strip().startswith("[Interface]"):
                if in_interface:
                    if not post_up_exists:
                        new_lines.append(f"PostUp = {post_up}\n")
                    if not post_down_exists:
                        new_lines.append(f"PostDown = {post_down}\n")
                    in_interface = False
            
            if in_interface:
                if line.strip().startswith("PostUp"):
                    if warp_iface in line:
                        post_up_exists = True
                elif line.strip().startswith("PostDown"):
                    if warp_iface in line:
                        post_down_exists = True

            new_lines.append(line)

        if in_interface:
            if not post_up_exists:
                new_lines.append(f"PostUp = {post_up}\n")
            if not post_down_exists:
                new_lines.append(f"PostDown = {post_down}\n")

        with open(wg_conf_path, "w") as f:
            f.writelines(new_lines)

        return True, f"Successfully routed {os.path.basename(wg_conf_path)} through {warp_iface}"
