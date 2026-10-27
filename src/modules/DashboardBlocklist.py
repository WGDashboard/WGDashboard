"""
Блокировка подсетей на уровне всего сервера (nftables).

Зачем: пользователи туннеля не должны открывать ресурсы, которые логируют
IP-адреса (российские сервисы и т.п.) - иначе VPN-адрес сервера попадает в
их базы. Блок ставится по адресам назначения:

- chain forward_block: трафик пиров через туннель (FORWARD);
- chain output_block: собственный исходящий трафик сервера (OUTPUT),
  с исключением по udp sport = listen порт конфигураций, иначе сервер не
  смог бы отвечать клиентам, чей реальный IP попал в заблокированную
  подсеть (крупные блоки провайдеров есть в списке).

INPUT сознательно не фильтруется: блокировка входящего по списку
отрезала бы рукопожатия клиентов из российских провайдерских сетей.

Источник списка: репозиторий lib4u/amnezia-tunneling-ru (lite/full),
формат AmneziaVPN [{"hostname": "<CIDR>", "ip": ""}, ...]. Список
хранится в файле и обновляется фоновым потоком; ручные записи
дополняют его в таблице BlocklistManual.
"""
import datetime
import ipaddress
import json
import os
import re
import shutil
import subprocess
import urllib.request

from flask import current_app
import sqlalchemy as db

from .DatabaseConnection import ConnectionString

LITE_URL = "https://raw.githubusercontent.com/lib4u/amnezia-tunneling-ru/main/amnezia-ip-lite.json"
FULL_URL = "https://raw.githubusercontent.com/lib4u/amnezia-tunneling-ru/main/amnezia-ip.json"
USER_AGENT = "WGDashboard-Blocklist"


class DashboardBlocklist:
    def __init__(self, wireguardConfigurations, dashboardConfig):
        self.wireguardConfigurations = wireguardConfigurations
        self.dashboardConfig = dashboardConfig
        self.engine = db.create_engine(ConnectionString("wgdashboard"))
        self.metadata = db.MetaData()
        self.manualTable = db.Table(
            "BlocklistManual", self.metadata,
            db.Column("cidr", db.String(64), primary_key=True),
            db.Column("comment", db.Text),
            db.Column(
                "CreatedAt",
                (db.DATETIME if self.dashboardConfig.GetConfig("Database", "type")[1] == "sqlite" else db.TIMESTAMP),
                server_default=db.func.now()
            ),
            extend_existing=True
        )
        self.metadata.create_all(self.engine)

        # Файлы живут рядом с wg-dashboard.ini (ConfigurationPath = каталог src)
        self.remoteFilePath = os.path.join(
            self.dashboardConfig.ConfigurationPath, "wgdashboard_blocklist_remote.txt")
        self.nftFilePath = os.path.join(
            self.dashboardConfig.ConfigurationPath, "wgdashboard_blocklist.nft")
        self.tableName = "inet wgdashboard_blocklist"

    # ------------------------------------------------------------------
    # Настройки (секция Blocklist в wg-dashboard.ini)
    # ------------------------------------------------------------------

    def _cfg(self, key):
        return self.dashboardConfig.GetConfig("Blocklist", key)

    def _set(self, key, value):
        status, msg = self.dashboardConfig.SetConfig("Blocklist", key, value)
        if not status:
            current_app.logger.error(f"Blocklist: cannot save {key}: {msg}")

    def IsEnabled(self) -> bool:
        return bool(self._cfg("enabled")[1])

    def GetFetchUrl(self) -> str:
        """URL для скачивания списка: пользовательский, если задан."""
        custom = (self._cfg("custom_url")[1] or "").strip()
        if custom:
            return custom
        size = self._cfg("list_size")[1] or "full"
        return FULL_URL if size == "full" else LITE_URL

    def IsListStale(self) -> bool:
        """
        Список надо перекачать: файла нет или источник менялся
        (UpdateSettings сбрасывает last_update при смене источника).
        """
        if not os.path.exists(self.remoteFilePath):
            return True
        return len((self._cfg("last_update")[1] or "").strip()) == 0

    def IsAutoUpdate(self) -> bool:
        return bool(self._cfg("auto_update")[1])

    def GetIntervalHours(self) -> int:
        try:
            return max(1, int(self._cfg("update_interval_hours")[1] or 6))
        except (TypeError, ValueError):
            return 6

    def IsAutoUpdateDue(self) -> bool:
        """Пора ли фоновому потоку обновлять список."""
        if not self.IsAutoUpdate():
            return False
        last = (self._cfg("last_update")[1] or "").strip()
        if len(last) == 0:
            return True
        try:
            lastDT = datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return True
        delta = datetime.datetime.now() - lastDT
        return delta.total_seconds() >= self.GetIntervalHours() * 3600

    def GetLastUpdate(self) -> str:
        return (self._cfg("last_update")[1] or "").strip()

    def GetNextUpdate(self) -> str:
        """Примерное время следующего автообновления, для UI."""
        last = self.GetLastUpdate()
        if len(last) == 0 or not self.IsAutoUpdate():
            return ""
        try:
            lastDT = datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return ""
        nextDT = lastDT + datetime.timedelta(hours=self.GetIntervalHours())
        return nextDT.strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Ручные записи
    # ------------------------------------------------------------------

    def GetManualEntries(self) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                self.manualTable.select().order_by(self.manualTable.columns.CreatedAt.desc())
            ).mappings().fetchall()
            return [
                {
                    "cidr": r["cidr"],
                    "comment": r["comment"] or "",
                    "created": (r["CreatedAt"].strftime("%Y-%m-%d %H:%M:%S")
                                if r["CreatedAt"] else "")
                }
                for r in rows
            ]

    def AddManualEntry(self, cidr: str, comment: str = "") -> tuple[bool, str]:
        cidr = (cidr or "").strip()
        if len(cidr) == 0:
            return False, "Please provide a subnet"
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError as e:
            return False, f"Invalid subnet: {e}"
        cidr = str(net)
        with self.engine.begin() as conn:
            existing = conn.execute(
                self.manualTable.select().where(self.manualTable.columns.cidr == cidr)
            ).mappings().fetchone()
            if existing is not None:
                return False, f"{cidr} is already in the list"
            conn.execute(self.manualTable.insert().values({
                "cidr": cidr,
                "comment": (comment or "").strip(),
                # Явное локальное время: server_default=CURRENT_TIMESTAMP
                # в SQLite возвращает UTC и расходится с остальными логами
                "CreatedAt": datetime.datetime.now()
            }))
        if self.IsEnabled():
            applyStatus, applyMsg = self.apply()
            if not applyStatus:
                return True, (f"Entry added, but applying failed: {applyMsg}")
        return True, ""

    def DeleteManualEntry(self, cidr: str) -> tuple[bool, str]:
        cidr = (cidr or "").strip()
        if len(cidr) == 0:
            return False, "Please provide a subnet"
        with self.engine.begin() as conn:
            result = conn.execute(
                self.manualTable.delete().where(self.manualTable.columns.cidr == cidr)
            )
            if result.rowcount == 0:
                return False, "Entry does not exist"
        if self.IsEnabled():
            applyStatus, applyMsg = self.apply()
            if not applyStatus:
                return True, (f"Entry deleted, but applying failed: {applyMsg}")
        return True, ""

    # ------------------------------------------------------------------
    # Скачивание списка
    # ------------------------------------------------------------------

    def download(self, url: str) -> str:
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        with urllib.request.urlopen(request, timeout=60) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, "replace")

    def parseList(self, text: str) -> list[str]:
        """
        Разбор содержимого списка. Поддерживаются:
        - JSON-массив [{"hostname": "<CIDR>", "ip": ""}, ...] (AmneziaVPN ip-list.json);
        - JSON-объект {"ip_list": [{"ip": "<CIDR>"}, ...]};
        - обычный текст: одна подсеть в строке (# и ; - комментарии).
        """
        networks: list[str] = []
        stripped = text.strip()

        parsed = None
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
            except ValueError:
                parsed = None

        if isinstance(parsed, list):
            for item in parsed:
                value = (item.get("hostname") if isinstance(item, dict) else item) or ""
                networks.append(str(value).strip())
        elif isinstance(parsed, dict) and isinstance(parsed.get("ip_list"), list):
            for item in parsed["ip_list"]:
                value = (item.get("ip") if isinstance(item, dict) else item) or ""
                networks.append(str(value).strip())
        elif parsed is not None:
            return []
        else:
            for line in stripped.splitlines():
                line = line.split("#", 1)[0].split(";", 1)[0].strip()
                if line:
                    networks.append(line)

        valid: list[str] = []
        seen = set()
        skipped = 0
        for value in networks:
            if len(value) == 0:
                continue
            try:
                net = ipaddress.ip_network(value, strict=False)
            except ValueError:
                skipped += 1
                continue
            normalized = str(net)
            if normalized not in seen:
                seen.add(normalized)
                valid.append(normalized)
        if skipped:
            current_app.logger.info(
                f"Blocklist: skipped {skipped} unparseable entries")
        return valid

    def FetchRemote(self) -> tuple[bool, str]:
        """Скачивает список с GetFetchUrl() и сохраняет в файл."""
        url = self.GetFetchUrl()
        try:
            text = self.download(url)
        except Exception as e:
            current_app.logger.error(f"Blocklist: fetch failed from {url}: {e}")
            return False, f"Download failed: {e}"
        networks = self.parseList(text)
        if len(networks) == 0:
            return False, "Downloaded list is empty or invalid"
        tmp = self.remoteFilePath + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(networks) + "\n")
        os.replace(tmp, self.remoteFilePath)
        self._set("last_update", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        current_app.logger.info(
            f"Blocklist: fetched {len(networks)} subnets from {url}")
        return True, ""

    def LoadRemoteFile(self) -> list[str]:
        if not os.path.exists(self.remoteFilePath):
            return []
        with open(self.remoteFilePath, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    # ------------------------------------------------------------------
    # nftables
    # ------------------------------------------------------------------

    def _nftBinary(self) -> str:
        path = shutil.which("nft")
        return path

    def GetListenPorts(self) -> list[int]:
        """Порты прослушивания всех конфигураций - для исключения в OUTPUT."""
        ports = []
        for configuration in self.wireguardConfigurations.values():
            try:
                port = int(configuration.ListenPort)
            except (TypeError, ValueError):
                continue
            if port > 0 and port not in ports:
                ports.append(port)
        return ports

    def GetDnsServers(self) -> list[str]:
        """
        DNS, которым нужен доступ сквозь блок:
        - peer_global_DNS (раздаётся пирам в конфиге, запросы идут FORWARD'ом);
        - системные nameserver из /etc/resolv.conf (исходящие запросы сервера).
        Без этого блок списка, содержащий адрес резолвера (например
        1.1.1.1/32 в lite-списке), ломал бы разрешение имён.
        """
        servers: list[str] = []
        dnsConfig = (self.dashboardConfig.GetConfig("Peers", "peer_global_DNS")[1] or "")
        try:
            resolv = open("/etc/resolv.conf", "r").read()
        except OSError:
            resolv = ""
        for line in resolv.splitlines():
            line = line.strip()
            if line.startswith("nameserver "):
                servers.append(line.split()[1].strip())
        for value in re.split(r"[,\s]+", dnsConfig) if dnsConfig else []:
            if len(value) > 0:
                servers.append(value)
        unique: list[str] = []
        for value in servers:
            try:
                addr = ipaddress.ip_address(value)
            except ValueError:
                continue
            if str(addr) not in unique:
                unique.append(str(addr))
        return unique

    def _generateNftFile(self, networks: list[str], dnsServers: list[str],
                         listenPorts: list[int]) -> tuple[bool, str]:
        v4 = [str(ipaddress.ip_network(n, strict=False))
              for n in networks if ":" not in n]
        v6 = [str(ipaddress.ip_network(n, strict=False))
              for n in networks if ":" in n]
        dnsV4 = [n for n in dnsServers if ":" not in n]
        dnsV6 = [n for n in dnsServers if ":" in n]

        def elements(values: list[str]) -> str:
            # Порциями: одна строка на ~200 подсетей читаемее в diff'ах
            # и не упирается в лимиты парсера nft
            chunks = [", ".join(values[i:i + 200]) for i in range(0, len(values), 200)]
            return (",\n\t\t\t").join(chunks)

        lines = [
            "#!/usr/sbin/nft -f",
            "# Generated by WGDashboard - do not edit manually",
            "",
            f"table inet {self.tableName.split(' ', 1)[1]} {{",
            "",
            "\tset dns_allow_v4 {",
            "\t\ttype ipv4_addr",
        ]
        if len(dnsV4) > 0:
            lines.append(f"\t\telements = {{ {', '.join(dnsV4)} }}")
        lines += [
            "\t}",
            "",
            "\tset dns_allow_v6 {",
            "\t\ttype ipv6_addr",
        ]
        if len(dnsV6) > 0:
            lines.append(f"\t\telements = {{ {', '.join(dnsV6)} }}")
        lines += [
            "\t}",
            "",
            "\tset blocked_v4 {",
            "\t\ttype ipv4_addr",
            "\t\tflags interval",
            "\t\tauto-merge",
        ]
        if len(v4) > 0:
            lines.append(f"\t\telements = {{ {elements(v4)} }}")
        lines += [
            "\t}",
            "",
            "\tset blocked_v6 {",
            "\t\ttype ipv6_addr",
            "\t\tflags interval",
            "\t\tauto-merge",
        ]
        if len(v6) > 0:
            lines.append(f"\t\telements = {{ {elements(v6)} }}")
        lines += [
            "\t}",
            "",
            "\tchain forward_block {",
            "\t\ttype filter hook forward priority filter + 15; policy accept;",
            "\t\tip daddr @dns_allow_v4 accept",
            "\t\tip6 daddr @dns_allow_v6 accept",
            "\t\tip daddr @blocked_v4 counter drop",
            "\t\tip6 daddr @blocked_v6 counter drop",
            "\t}",
            "",
            "\tchain output_block {",
            "\t\ttype filter hook output priority filter + 15; policy accept;",
        ]
        if len(listenPorts) > 0:
            # Исключение для ответов AWG-клиентам: все пакеты от сервера к
            # клиенту уходят с исходным портом = listen port. Без этого
            # клиенты, чей реальный IP попал в заблокированную подсеть
            # (крупные провайдерские блоки), не смогли бы даже
            # завершить рукопожатие.
            ports = ", ".join(str(p) for p in listenPorts)
            lines.append(f"\t\tudp sport {{ {ports} }} accept")
        lines += [
            "\t\tip daddr @dns_allow_v4 accept",
            "\t\tip daddr @blocked_v4 counter drop",
            "\t\tip6 daddr @blocked_v6 counter drop",
            "\t}",
            "}",
            "",
        ]
        try:
            # newline="\n": на Windows по умолчанию "\r\n", nft парсер
            # спотыкается о \r ("syntax error, unexpected junk")
            with open(self.nftFilePath, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines))
        except OSError as e:
            return False, f"Cannot write ruleset: {e}"
        return True, ""

    def IsApplied(self) -> bool:
        nft = self._nftBinary()
        if not nft:
            return False
        result = subprocess.run(
            [nft, "list", "table", *self.tableName.split()],
            capture_output=True, text=True, timeout=30)
        return result.returncode == 0

    def GetCounters(self) -> dict:
        """
        Счётчики сработавших правил: сколько пакетов/байт было отброшено
        в каждой цепочке с последнего применения.
        """
        nft = self._nftBinary()
        if not nft:
            return {}
        result = subprocess.run(
            [nft, "-j", "list", "table", *self.tableName.split()],
            capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {}
        try:
            data = json.loads(result.stdout)
        except ValueError:
            return {}
        counters = {"forward_block": {"packets": 0, "bytes": 0},
                    "output_block": {"packets": 0, "bytes": 0}}
        for obj in data.get("nftables", []):
            rule = obj.get("rule")
            if not rule or rule.get("chain") not in counters:
                continue
            for expr in rule.get("expr", []):
                counter = expr.get("counter")
                if counter is not None:
                    counters[rule["chain"]]["packets"] += counter.get("packets", 0)
                    counters[rule["chain"]]["bytes"] += counter.get("bytes", 0)
        return counters

    def apply(self) -> tuple[bool, str]:
        nft = self._nftBinary()
        if not nft:
            return False, "nftables binary (nft) not found"
        if not os.path.exists(self.remoteFilePath):
            fetchStatus, fetchMsg = self.FetchRemote()
            if not fetchStatus:
                return False, f"List download failed: {fetchMsg}"
        networks = self.LoadRemoteFile()
        entries = self.GetManualEntries()
        for entry in entries:
            if entry["cidr"] not in networks:
                networks.append(entry["cidr"])
        if len(networks) == 0:
            return False, "No subnets to block"
        status, msg = self._generateNftFile(
            networks, self.GetDnsServers(), self.GetListenPorts())
        if not status:
            return False, msg
        # Пересоздаём таблицу: delete игнорируем ошибку (таблицы может не быть)
        subprocess.run(
            [nft, "delete", "table", *self.tableName.split()],
            capture_output=True, text=True, timeout=30)
        result = subprocess.run(
            [nft, "-f", self.nftFilePath],
            capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            current_app.logger.error(
                f"Blocklist: nft apply failed: {result.stderr.strip()}")
            return False, (result.stderr.strip() or "nft apply failed")
        current_app.logger.info(
            f"Blocklist applied: {len(networks)} subnets, "
            f"{len(self.GetListenPorts())} listen port(s)")
        return True, ""

    def remove(self) -> tuple[bool, str]:
        nft = self._nftBinary()
        if not nft:
            return False, "nftables binary (nft) not found"
        subprocess.run(
            [nft, "delete", "table", *self.tableName.split()],
            capture_output=True, text=True, timeout=30)
        return True, ""

    # ------------------------------------------------------------------
    # Переключение и обновление
    # ------------------------------------------------------------------

    def Toggle(self, enabled: bool) -> tuple[bool, str]:
        if enabled:
            if self.IsListStale():
                fetchStatus, fetchMsg = self.FetchRemote()
                if not fetchStatus:
                    return False, fetchMsg
            self._set("enabled", True)
            status, msg = self.apply()
            if not status:
                self._set("enabled", False)
                return False, msg
            return True, ""
        self._set("enabled", False)
        status, msg = self.remove()
        if not status:
            return False, msg
        return True, ""

    def Refresh(self) -> tuple[bool, str]:
        fetchStatus, fetchMsg = self.FetchRemote()
        if not fetchStatus:
            return False, fetchMsg
        if self.IsEnabled():
            return self.apply()
        return True, ""

    def UpdateSettings(self, listSize: str = None, customUrl: str = None,
                       autoUpdate: bool = None,
                       updateIntervalHours: int = None) -> tuple[bool, str]:
        oldUrl = self.GetFetchUrl()
        if listSize is not None:
            if listSize not in ("lite", "full"):
                return False, "list_size must be 'lite' or 'full'"
            self._set("list_size", listSize)
            # Пользовательский URL перекрывает выбор встроенного списка
            if (self._cfg("custom_url")[1] or "").strip():
                self._set("custom_url", "")
        if customUrl is not None:
            customUrl = customUrl.strip()
            if len(customUrl) > 0 and not customUrl.startswith(("http://", "https://")):
                return False, "Custom URL must start with http:// or https://"
            self._set("custom_url", customUrl)
        if autoUpdate is not None:
            self._set("auto_update", bool(autoUpdate))
        if updateIntervalHours is not None:
            try:
                hours = int(updateIntervalHours)
            except (TypeError, ValueError):
                return False, "update_interval_hours must be an integer"
            if hours < 1 or hours > 168:
                return False, "update_interval_hours must be between 1 and 168"
            self._set("update_interval_hours", hours)
        if self.GetFetchUrl() != oldUrl:
            # Источник списка сменился: кэш больше не актуален, при
            # следующем включении/автообновлении скачается заново
            self._set("last_update", "")
        return True, ""

    def toJson(self) -> dict:
        remoteNetworks = self.LoadRemoteFile()
        manual = self.GetManualEntries()
        return {
            "enabled": self.IsEnabled(),
            "applied": self.IsApplied(),
            "list_size": self._cfg("list_size")[1] or "full",
            "custom_url": (self._cfg("custom_url")[1] or "").strip(),
            "auto_update": self.IsAutoUpdate(),
            "update_interval_hours": self.GetIntervalHours(),
            "last_update": self.GetLastUpdate(),
            "next_update": self.GetNextUpdate(),
            "remote_count": len(remoteNetworks),
            "manual_count": len(manual),
            "manual_entries": manual,
            "listen_ports": self.GetListenPorts(),
            "counters": self.GetCounters()
        }
