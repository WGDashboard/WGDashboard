import shutil, subprocess, time, threading, psutil, re, os
from flask import current_app
from pathlib import Path

class SystemStatus:
    def __init__(self):
        self.CPU = CPU()
        self.MemoryVirtual = Memory('virtual')
        self.MemorySwap = Memory('swap')
        self.Disks = Disks()
        self.NetworkInterfaces = NetworkInterfaces()
        self.Processes = Processes()
        self.GPU = GPU()
        self.SystemTemperature = SystemTemperature()
        self.DiskIO = DiskIO()
        self.FanSpeed = FanSpeed()
        self.SystemInfo = SystemInfo()
        
    def toJson(self):
        process = [
            threading.Thread(target=self.CPU.getCPUPercent), 
            threading.Thread(target=self.CPU.getPerCPUPercent),
            threading.Thread(target=self.CPU.getCPUTemperature),
            threading.Thread(target=self.CPU.getCPUFrequencies),
            threading.Thread(target=self.CPU.getLoadAverage),
            threading.Thread(target=self.NetworkInterfaces.getData),
            threading.Thread(target=self.GPU.getData),
            threading.Thread(target=self.SystemTemperature.getData),
            threading.Thread(target=self.DiskIO.getData),
            threading.Thread(target=self.FanSpeed.getData),
            threading.Thread(target=self.SystemInfo.getData)
        ]
        for p in process:
            p.start()
        for p in process:
            p.join()
        
        
        return {
            "CPU": self.CPU,
            "Memory": {
                "VirtualMemory": self.MemoryVirtual,
                "SwapMemory": self.MemorySwap
            },
            "Disks": self.Disks,
            "NetworkInterfaces": self.NetworkInterfaces,
            "NetworkInterfacesPriority": self.NetworkInterfaces.getInterfacePriorities(),
            "Processes": self.Processes,
            "GPU": self.GPU,
            "SystemTemperature": self.SystemTemperature,
            "DiskIO": self.DiskIO,
            "FanSpeed": self.FanSpeed,
            "SystemInfo": self.SystemInfo
        }
        

class CPU:
    def __init__(self):
        self.cpu_percent: float = 0
        self.cpu_percent_per_cpu: list[float] = []
        self.cpu_temperatures: dict = {}
        self.cpu_frequencies: list[dict] = []
        self.load_average: dict = {}
        
    def getCPUPercent(self):
        try:
            self.cpu_percent = psutil.cpu_percent(interval=1)
        except Exception as e:
            current_app.logger.error("Get CPU Percent error", e)
    
    def getPerCPUPercent(self):
        try:
            self.cpu_percent_per_cpu = psutil.cpu_percent(interval=1, percpu=True)
        except Exception as e:
            current_app.logger.error("Get Per CPU Percent error", e)
    
    def getCPUTemperature(self):
        try:
            # Try psutil first (newer versions)
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        self.cpu_temperatures[name] = []
                        for entry in entries:
                            self.cpu_temperatures[name].append({
                                "label": entry.label or name,
                                "current": entry.current,
                                "high": entry.high,
                                "critical": entry.critical
                            })
                return
            
            # Fallback to lm_sensors if available
            if shutil.which("sensors"):
                result = subprocess.check_output(["sensors", "-u", "-A"], text=True)
                self._parse_sensors_output(result)
        except Exception as e:
            current_app.logger.error("Get CPU Temperature error", e)
    
    def getCPUFrequencies(self):
        """Get CPU frequency per core in MHz"""
        try:
            if hasattr(psutil, 'cpu_freq'):
                freq = psutil.cpu_freq(percpu=True)
                if freq:
                    self.cpu_frequencies = []
                    for i, f in enumerate(freq):
                        self.cpu_frequencies.append({
                            "core": i,
                            "current": round(f.current, 2),
                            "min": round(f.min, 2),
                            "max": round(f.max, 2)
                        })
        except Exception as e:
            current_app.logger.debug(f"Get CPU Frequencies error: {e}")
    
    def getLoadAverage(self):
        """Get system load average (1, 5, 15 minutes)"""
        try:
            load = os.getloadavg()
            cpu_count = psutil.cpu_count()
            self.load_average = {
                "one_minute": round(load[0], 2),
                "five_minutes": round(load[1], 2),
                "fifteen_minutes": round(load[2], 2),
                "cpu_count": cpu_count,
                "load_percent": round((load[0] / cpu_count * 100), 2) if cpu_count else 0
            }
        except Exception as e:
            current_app.logger.debug(f"Get Load Average error: {e}")
    
    def _parse_sensors_output(self, output):
        """Parse lm_sensors output"""
        lines = output.split('\n')
        current_chip = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Adapter:'):
                if line.startswith('Adapter:'):
                    current_chip = line.replace('Adapter:', '').strip()
                    if current_chip not in self.cpu_temperatures:
                        self.cpu_temperatures[current_chip] = []
            elif current_chip and ('°C' in line or '_input' in line):
                match = re.search(r'(.+?):\s*([\d.]+)\s*°?C?', line)
                if match:
                    label = match.group(1).strip()
                    temp = float(match.group(2))
                    self.cpu_temperatures[current_chip].append({
                        "label": label,
                        "current": temp,
                        "high": None,
                        "critical": None
                    })
    
    def toJson(self):
        return self.__dict__

class Memory:
    def __init__(self, memoryType: str):
        self.__memoryType__ = memoryType
        self.total = 0
        self.available = 0
        self.percent = 0
    def getData(self):
        try:
            if self.__memoryType__ == "virtual":
                memory = psutil.virtual_memory()
                self.available = memory.available
            else:
                memory = psutil.swap_memory()
                self.available = memory.free
            self.total = memory.total
            
            self.percent = memory.percent
        except Exception as e:
            current_app.logger.error("Get Memory percent error", e)
    def toJson(self):
        self.getData()
        return self.__dict__

class Disks:
    def __init__(self):
        self.disks : list[Disk] = []
    def getData(self):
        try:
            self.disks = list(map(lambda x : Disk(x.mountpoint), psutil.disk_partitions()))
        except Exception as e:
            current_app.logger.error("Get Disk percent error", e)
    def toJson(self):
        self.getData()
        return self.disks

class Disk:
    def __init__(self, mountPoint: str):
        self.total = 0
        self.used = 0
        self.free = 0
        self.percent = 0
        self.mountPoint = mountPoint
    def getData(self):
        try:
            disk = psutil.disk_usage(self.mountPoint)
            self.total = disk.total
            self.free = disk.free
            self.used = disk.used
            self.percent = disk.percent
        except Exception as e:
            current_app.logger.error("Get Disk percent error", e)
    def toJson(self):
        self.getData()
        return self.__dict__
    
class NetworkInterfaces:
    def __init__(self):
        self.interfaces = {}
        
    def getInterfacePriorities(self):
        if shutil.which("ip"):
            result = subprocess.check_output(["ip", "route", "show"]).decode()
            priorities = {}
            for line in result.splitlines():
                if "metric" in line and "dev" in line:
                    parts = line.split()
                    dev = parts[parts.index("dev")+1]
                    metric = int(parts[parts.index("metric")+1])
                    if dev not in priorities:
                        priorities[dev] = metric
            return priorities
        return {}

    def getData(self):
        self.interfaces.clear()
        try:
            network = psutil.net_io_counters(pernic=True, nowrap=True)
            for i in network.keys():
                self.interfaces[i] = network[i]._asdict()
            time.sleep(1)
            network = psutil.net_io_counters(pernic=True, nowrap=True)
            for i in network.keys():
                self.interfaces[i]['realtime'] = {
                    'sent': round((network[i].bytes_sent - self.interfaces[i]['bytes_sent']) / 1024 / 1024, 4),
                    'recv': round((network[i].bytes_recv - self.interfaces[i]['bytes_recv']) / 1024 / 1024, 4)
                }
        except Exception as e:
            current_app.logger.error("Get network error", e)

    def toJson(self):
        return self.interfaces

class Process:
    def __init__(self, name, command, pid, percent):
        self.name = name
        self.command = command
        self.pid = pid
        self.percent = percent
    def toJson(self):
        return self.__dict__

class Processes:
    def __init__(self):
        self.CPU_Top_10_Processes: list[Process] = []
        self.Memory_Top_10_Processes: list[Process] = []
    def getData(self):
        try:
            processes = list(psutil.process_iter())

            cpu_processes = []
            memory_processes = []

            for proc in processes:
                try:
                    name = proc.name()
                    cmdline = " ".join(proc.cmdline())
                    pid = proc.pid
                    cpu_percent = proc.cpu_percent()
                    mem_percent = proc.memory_percent()

                    # Create Process object for CPU and memory tracking
                    cpu_process = Process(name, cmdline, pid, cpu_percent)
                    mem_process = Process(name, cmdline, pid, mem_percent)

                    cpu_processes.append(cpu_process)
                    memory_processes.append(mem_process)

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Skip processes we can't access or that no longer exist
                    continue

            # Sort by CPU and memory usage (descending order)
            cpu_sorted = sorted(cpu_processes, key=lambda p: p.percent, reverse=True)
            mem_sorted = sorted(memory_processes, key=lambda p: p.percent, reverse=True)

            # Get top 20 processes for each
            self.CPU_Top_10_Processes = cpu_sorted[:20]
            self.Memory_Top_10_Processes = mem_sorted[:20]

        except Exception as e:
            current_app.logger.error("Get processes error", e)

    def toJson(self):
        self.getData()
        return {
            "cpu_top_10": self.CPU_Top_10_Processes,
            "memory_top_10": self.Memory_Top_10_Processes
        }


class GPU:
    def __init__(self):
        self.nvidia_gpus: list[dict] = []
        self.amd_gpus: list[dict] = []
    
    def getData(self):
        try:
            # Reset lists each poll: SystemStatus is a long-lived singleton,
            # so appending without clearing would duplicate entries over time.
            self.nvidia_gpus = []
            self.amd_gpus = []
            self._get_nvidia_gpus()
            self._get_amd_gpus()
        except Exception as e:
            current_app.logger.error("Get GPU data error", e)
    
    def _get_nvidia_gpus(self):
        """Get NVIDIA GPU stats using nvidia-smi"""
        try:
            if not shutil.which("nvidia-smi"):
                return
            
            result = subprocess.check_output([
                "nvidia-smi", 
                "--query-gpu=index,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit",
                "--format=csv,noheader,nounits"
            ], text=True, stderr=subprocess.DEVNULL)
            
            for line in result.strip().split('\n'):
                if not line:
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 9:
                    self.nvidia_gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "temperature": float(parts[2]),
                        "gpu_utilization": float(parts[3]),
                        "memory_utilization": float(parts[4]),
                        "memory_used": float(parts[5]),
                        "memory_total": float(parts[6]),
                        "power_draw": float(parts[7]),
                        "power_limit": float(parts[8])
                    })
        except Exception as e:
            current_app.logger.debug(f"NVIDIA GPU error: {e}")
    
    def _get_amd_gpus(self):
        """Get AMD GPU stats using rocm-smi"""
        try:
            if not shutil.which("rocm-smi"):
                return
            
            result = subprocess.check_output(["rocm-smi", "--json"], text=True, stderr=subprocess.DEVNULL)
            import json
            data = json.loads(result)
            
            for gpu_data in data:
                self.amd_gpus.append({
                    "index": gpu_data.get("gpu_id"),
                    "name": gpu_data.get("product_name"),
                    "temperature": gpu_data.get("temperature"),
                    "sclk": gpu_data.get("sclk"),
                    "mclk": gpu_data.get("mclk"),
                    "power": gpu_data.get("power")
                })
        except Exception as e:
            current_app.logger.debug(f"AMD GPU error: {e}")
    
    def toJson(self):
        return {
            "nvidia": self.nvidia_gpus,
            "amd": self.amd_gpus
        }


class SystemTemperature:
    def __init__(self):
        self.temperatures: dict = {}
    
    def getData(self):
        try:
            self.temperatures = {}
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        self.temperatures[name] = []
                        for entry in entries:
                            self.temperatures[name].append({
                                "label": entry.label or "Temperature",
                                "current": round(entry.current, 1),
                                "high": entry.high,
                                "critical": entry.critical
                            })
            else:
                # Fallback to lm_sensors
                self._get_temps_from_sensors()
        except Exception as e:
            current_app.logger.debug(f"Get system temperature error: {e}")
    
    def _get_temps_from_sensors(self):
        """Fallback method using lm_sensors"""
        try:
            if not shutil.which("sensors"):
                return
            
            result = subprocess.check_output(["sensors", "-A"], text=True)
            lines = result.split('\n')
            current_device = None
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('Adapter:') and ':' in line:
                    if line.startswith('Adapter:'):
                        current_device = line.replace('Adapter:', '').strip()
                    elif current_device:
                        match = re.search(r'(.+?):\s*([\d.]+)°C', line)
                        if match:
                            label = match.group(1).strip()
                            temp = float(match.group(2))
                            if current_device not in self.temperatures:
                                self.temperatures[current_device] = []
                            self.temperatures[current_device].append({
                                "label": label,
                                "current": temp,
                                "high": None,
                                "critical": None
                            })
        except Exception as e:
            current_app.logger.debug(f"Sensors fallback error: {e}")
    
    def toJson(self):
        return self.temperatures


class DiskIO:
    def __init__(self):
        self.disk_io_counters: dict = {}
        self.disk_io_realtime: dict = {}
        self._previous_counters = {}
        self._previous_time = None

    @staticmethod
    def _is_whole_disk(name: str) -> bool:
        """Keep only real whole block devices (drop loops, ram, dm and partitions)."""
        if name.startswith(("loop", "ram", "zram", "dm-", "sr")):
            return False
        if re.match(r'^(nvme\d+n\d+|mmcblk\d+)p\d+$', name):
            return False
        if re.match(r'^(sd[a-z]+|vd[a-z]+|hd[a-z]+|xvd[a-z]+)\d+$', name):
            return False
        return True

    def getData(self):
        try:
            counters = psutil.disk_io_counters(perdisk=True)
            if not counters:
                return

            now = time.time()
            elapsed = (now - self._previous_time) if self._previous_time else None
            if elapsed is not None and (elapsed <= 0 or elapsed > 60):
                elapsed = None

            # Store current counters (whole disks only)
            current_counters = {}
            for disk, io in counters.items():
                if not self._is_whole_disk(disk):
                    continue
                current_counters[disk] = {
                    "read_bytes": io.read_bytes,
                    "write_bytes": io.write_bytes,
                    "read_count": io.read_count,
                    "write_count": io.write_count
                }

            # Calculate real-time I/O (per second)
            self.disk_io_realtime = {}
            for disk, current in current_counters.items():
                prev = self._previous_counters.get(disk)
                if prev and elapsed:
                    self.disk_io_realtime[disk] = {
                        "read_mb_s": round((current["read_bytes"] - prev["read_bytes"]) / 1048576 / elapsed, 2),
                        "write_mb_s": round((current["write_bytes"] - prev["write_bytes"]) / 1048576 / elapsed, 2),
                        "read_iops": int(round((current["read_count"] - prev["read_count"]) / elapsed)),
                        "write_iops": int(round((current["write_count"] - prev["write_count"]) / elapsed))
                    }
                else:
                    self.disk_io_realtime[disk] = {
                        "read_mb_s": 0,
                        "write_mb_s": 0,
                        "read_iops": 0,
                        "write_iops": 0
                    }

            self._previous_counters = current_counters
            self._previous_time = now
            self.disk_io_counters = current_counters

        except Exception as e:
            current_app.logger.debug(f"Get disk IO error: {e}")
    
    def toJson(self):
        return {
            "counters": self.disk_io_counters,
            "realtime": self.disk_io_realtime
        }


class FanSpeed:
    def __init__(self):
        self.fans: dict = {}
    
    def getData(self):
        try:
            self.fans = {}
            if hasattr(psutil, 'sensors_fans'):
                fans = psutil.sensors_fans()
                if fans:
                    for name, entries in fans.items():
                        self.fans[name] = []
                        for entry in entries:
                            self.fans[name].append({
                                "label": entry.label or "Fan",
                                "current": entry.current
                            })
            else:
                # Fallback to lm_sensors
                self._get_fans_from_sensors()
        except Exception as e:
            current_app.logger.debug(f"Get fan speed error: {e}")
    
    def _get_fans_from_sensors(self):
        """Fallback method using lm_sensors"""
        try:
            if not shutil.which("sensors"):
                return
            
            result = subprocess.check_output(["sensors", "-A"], text=True)
            lines = result.split('\n')
            current_device = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('Adapter:'):
                    current_device = line.replace('Adapter:', '').strip()
                elif current_device and 'RPM' in line:
                    match = re.search(r'(.+?):\s*(\d+)\s*RPM', line)
                    if match:
                        label = match.group(1).strip()
                        rpm = int(match.group(2))
                        if current_device not in self.fans:
                            self.fans[current_device] = []
                        self.fans[current_device].append({
                            "label": label,
                            "current": rpm
                        })
        except Exception as e:
            current_app.logger.debug(f"Sensors fans fallback error: {e}")
    
    def toJson(self):
        return self.fans


class SystemInfo:
    """System-wide information (uptime, hostname, etc)"""
    def __init__(self):
        self.uptime_seconds: int = 0
        self.uptime_formatted: str = ""
        self.hostname: str = ""
        self.boot_time: float = 0
    
    def getData(self):
        try:
            # Get uptime
            boot_time = psutil.boot_time()
            self.boot_time = boot_time
            self.uptime_seconds = int(time.time() - boot_time)
            
            # Format uptime as HH:MM:SS
            hours = self.uptime_seconds // 3600
            minutes = (self.uptime_seconds % 3600) // 60
            seconds = self.uptime_seconds % 60
            self.uptime_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Get hostname
            self.hostname = os.uname().nodename
            
        except Exception as e:
            current_app.logger.debug(f"Get system info error: {e}")
    
    def toJson(self):
        return self.__dict__