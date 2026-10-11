"""Classify WGDashboard configuration files before constructing database-backed objects."""

from pathlib import Path

# Keys supported by wg-quick and WGDashboard. Match keys case-insensitively,
# while preserving the original file for the actual protocol parser.
WG_INTERFACE_KEYS = frozenset({
    "privatekey", "address", "listenport", "fwmark", "dns", "mtu", "table",
    "preup", "postup", "predown", "postdown", "saveconfig",
})
WG_PEER_KEYS = frozenset({
    "publickey", "presharedkey", "allowedips", "endpoint", "persistentkeepalive", "advancedsecurity",
})
AWG_INTERFACE_KEYS = frozenset({
    "jc", "jmin", "jmax", "s1", "s2", "s3", "s4", "h1", "h2", "h3", "h4",
    "i1", "i2", "i3", "i4", "i5",
    "headerprotectionkey", "contentpaddingaddition", "randomtrailers",
    "rekeyaftertime", "rekeytimeout", "rejectaftertime",
    "keepalivetimeout", "maxhandshakeattempts", "disablecookies",
})


def detect_configuration_protocol(path):
    """Return (protocol, reason), with protocol 'wg', 'awg' or None.

    Strict allowlists reject foreign formats, including unrecognised sections.
    Files without AWG-only keys are indistinguishable from ordinary WireGuard.
    """
    section = None
    found_interface = False
    found_private_key = False
    has_awg_keys = False

    try:
        with Path(path).open(encoding="utf-8-sig") as config:
            for line_number, line in enumerate(config, 1):
                line = line.strip()
                if not line or line.startswith(("#", ";")):
                    continue
                if line.startswith("["):
                    if line not in ("[Interface]", "[Peer]"):
                        return None, f"unsupported section on line {line_number}: {line}"
                    section = line
                    if section == "[Interface]":
                        if found_interface:
                            return None, "duplicate [Interface] section"
                        found_interface = True
                    elif not found_interface:
                        return None, "[Peer] before [Interface]"
                    continue
                if section is None or "=" not in line:
                    return None, f"invalid directive on line {line_number}"
                key, value = line.split("=", 1)
                key = key.strip().lower()
                if not key:
                    return None, f"empty key on line {line_number}"
                if section == "[Interface]":
                    if key in AWG_INTERFACE_KEYS:
                        has_awg_keys = True
                    elif key not in WG_INTERFACE_KEYS:
                        return None, f"unknown interface parameter on line {line_number}: {key}"
                    if key == "privatekey" and value.strip():
                        found_private_key = True
                elif key not in WG_PEER_KEYS:
                    return None, f"unknown peer parameter on line {line_number}: {key}"
    except (OSError, UnicodeError) as error:
        return None, f"cannot read configuration: {error}"

    if not found_interface or not found_private_key:
        return None, "missing [Interface] or PrivateKey"
    return ("awg" if has_awg_keys else "wg"), None
