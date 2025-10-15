import shutil, subprocess, time, threading, psutil
from flask import current_app

class SystemStatus:
    def __init__(self):
        self.CPU = CPU()
        self.MemoryVirtual = Memory('virtual')
        self.MemorySwap = Memory('swap')
        self.Disks = Disks()
        self.NetworkInterfaces = NetworkInterfaces()
        self.Processes = Processes()
    def toJson(self):
        process = [
            threading.Thread(target=self.CPU.getCPUPercent), 
            threading.Thread(target=self.CPU.getPerCPUPercent),
            threading.Thread(target=self.NetworkInterfaces.getData)
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
            "Processes": self.Processes
        }
        

class CPU:
    def __init__(self):
        self.cpu_percent: float = 0
        self.cpu_percent_per_cpu: list[float] = []
        
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
                    # Skip processes we can’t access or that no longer exist
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