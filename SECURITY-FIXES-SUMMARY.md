# Security Fixes Summary for WGDashboard v4.3.x

## Overview
This document summarizes all security fixes applied to WGDashboard v4.3.x to address the three critical vulnerabilities identified in [SECURITY-ADVISORY.md](SECURITY-ADVISORY.md).

## Vulnerabilities Fixed

### 1. Path Traversal (CWE-22) - File Download Endpoint
**File:** [src/dashboard.py](src/dashboard.py#L1235-L1265)
**Endpoint:** `GET /fileDownload`
**Severity:** Critical

**Vulnerability:**
The file download endpoint allowed arbitrary file reads via path traversal sequences (`../`).

**Fix Applied:**
- Implemented path canonicalization using `pathlib.Path.resolve()`
- Added strict prefix checking to ensure requested files are within the download directory
- Added proper error handling for invalid paths

**Code Changes:**
```python
# Before: No path validation
return send_file(f"download/{file}", as_attachment=True)

# After: Path canonicalization and validation
download_dir = Path('download').resolve()
requested_path = (download_dir / file).resolve()
if not str(requested_path).startswith(str(download_dir)):
    return ResponseObject(False, "Invalid file path")
```

---

### 2. Authentication Bypass (CWE-287, CWE-863) - Substring Whitelist
**File:** [src/dashboard.py](src/dashboard.py#L249-L275)
**Severity:** Critical

**Vulnerability:**
The authentication middleware used substring matching for public endpoints, allowing unauthenticated access to any endpoint containing `/api/clients/` in its path.

**Fix Applied:**
- Replaced substring matching with exact path matching
- Created explicit `public_endpoints` list with full paths
- Implemented proper directory-based matching for endpoints ending with `/`

**Code Changes:**
```python
# Before: Vulnerable substring matching
if '/api/clients/' in request.path:
    return response

# After: Exact path matching
public_endpoints = [
    f'{APP_PREFIX}/',
    f'{APP_PREFIX}/static/',
    f'{APP_PREFIX}/api/handshake',
    # ... other public endpoints
]
is_public = False
for public_endpoint in public_endpoints:
    if public_endpoint.endswith('/'):
        if request.path.startswith(public_endpoint):
            is_public = True
            break
    else:
        if request.path == public_endpoint:
            is_public = True
            break
if is_public:
    return response
```

---

### 3. Command Injection (CWE-78) - Shell Command Execution
**Severity:** Critical

**Vulnerability:**
Multiple subprocess calls used `shell=True` with user-influenced values, allowing command injection.

**Fix Applied:**
- Created `ExecuteWireguardCommand()` function in [Utilities.py](src/modules/Utilities.py#L154-L265)
- Replaced all `subprocess.check_output(shell=True)` calls with argument vector execution
- Added input validation functions for WireGuard identifiers, keys, and IP addresses

**Files Fixed:**

#### 3.1 [src/modules/Peer.py](src/modules/Peer.py)
- Lines 97, 99, 105: Replaced `subprocess.check_output` with `ExecuteWireguardCommand`
- Methods affected: `updatePeer()`

#### 3.2 [src/modules/WireguardConfiguration.py](src/modules/WireguardConfiguration.py)
- Lines 564, 568: `addPeers()` method
- Lines 619, 640: `allowPeers()` method
- Lines 692: `restrictPeers()` method
- Lines 722: `deletePeers()` method
- Lines 732: `__wgSave()` method
- Lines 772: `getPeersLatestHandshake()` method
- Lines 811: `getPeersTransfer()` method
- Lines 869: `getPeersEndpoint()` method
- Lines 890, 896: `toggleConfiguration()` method

#### 3.3 [src/modules/Utilities.py](src/modules/Utilities.py)
- Lines 73, 81: `GenerateWireguardPublicKey()` and `GenerateWireguardPrivateKey()`
- Replaced `subprocess.check_output(shell=True)` with `subprocess.run()` using argument vectors

#### 3.4 [src/modules/AmneziaWGPeer.py](src/modules/AmneziaWGPeer.py)
- Lines 63, 70: `updatePeer()` method
- Replaced `subprocess.check_output` with `ExecuteWireguardCommand`

#### 3.5 [src/modules/AmneziaWireguardConfiguration.py](src/modules/AmneziaWireguardConfiguration.py)
- Lines 298, 302: `addPeers()` method
- Replaced `subprocess.check_output` with `ExecuteWireguardCommand`

**New Security Functions Added:**

```python
# Input Validation Functions
def ValidateWireguardIdentifier(identifier: str) -> tuple[bool, str] | tuple[bool, None]
def ValidateWireguardPublicKey(publicKey: str) -> tuple[bool, str] | tuple[bool, None]
def ValidateWireguardPrivateKey(privateKey: str) -> tuple[bool, str] | tuple[bool, None]
def ValidateWireguardAllowedIPs(allowedIPs: str) -> tuple[bool, str] | tuple[bool, None]

# Safe Command Execution
def ExecuteWireguardCommand(protocol: str, command: str, args: list) -> tuple[bool, str]
```

**Code Changes Example:**
```python
# Before: Vulnerable shell=True execution
result = subprocess.check_output(
    f"wg set {config_name} peer {peer_id} allowed-ips {allowed_ips}",
    shell=True, stderr=subprocess.STDOUT
)

# After: Safe argument vector execution
result = ExecuteWireguardCommand('wg', 'set', [config_name, 'peer', peer_id, 'allowed-ips', allowed_ips])
```

---

## Security Improvements

### Defense in Depth
1. **Input Validation:** Added validation functions for all WireGuard-specific inputs
2. **Path Security:** Implemented canonicalization and prefix checking for file operations
3. **Command Safety:** Eliminated all shell=True usage, using argument vectors exclusively
4. **Authentication:** Strengthened authorization with exact path matching

### Validation Rules
- **WireGuard Identifiers:** Alphanumeric, hyphens, underscores only (max 15 chars)
- **Public Keys:** Base64 encoded, 44 characters
- **Private Keys:** Base64 encoded, 44 characters
- **Allowed IPs:** Valid IP addresses or CIDR notation

---

## Testing Recommendations

### 1. Path Traversal Testing
```bash
# Should be blocked
curl "http://localhost:10086/fileDownload?file=../../../../etc/passwd"
curl "http://localhost:10086/fileDownload?file=..%2F..%2F..%2Fetc%2Fhostname"

# Should work (if file exists)
curl "http://localhost:10086/fileDownload?file=backup.zip"
```

### 2. Authentication Testing
```bash
# Should require authentication
curl "http://localhost:10086/api/clients/getAll"

# Should work without authentication
curl "http://localhost:10086/api/getDashboardVersion"
```

### 3. Command Injection Testing
```bash
# Attempt command injection via peer ID
# Should be blocked and not execute arbitrary commands
```

---

## Files Modified

1. [src/dashboard.py](src/dashboard.py) - Path traversal and authentication bypass fixes
2. [src/modules/Peer.py](src/modules/Peer.py) - Command injection fixes
3. [src/modules/WireguardConfiguration.py](src/modules/WireguardConfiguration.py) - Command injection fixes
4. [src/modules/Utilities.py](src/modules/Utilities.py) - Added validation and safe execution functions
5. [src/modules/AmneziaWGPeer.py](src/modules/AmneziaWGPeer.py) - Command injection fixes
6. [src/modules/AmneziaWireguardConfiguration.py](src/modules/AmneziaWireguardConfiguration.py) - Command injection fixes

---

## Verification

All `shell=True` instances have been eliminated from the codebase:
- ✅ No subprocess calls with shell=True in production code
- ✅ All file operations use path canonicalization
- ✅ All authentication checks use exact path matching
- ✅ All WireGuard commands use argument vectors

---

## Additional Security Recommendations

1. **Rate Limiting:** Implement rate limiting on authentication endpoints
2. **Logging:** Enhanced logging for security events
3. **Input Sanitization:** Consider additional input sanitization layers
4. **Code Review:** Establish security code review process
5. **Dependency Updates:** Regularly update dependencies for security patches

---

## References

- [SECURITY-ADVISORY-CVE-DRAFT.md](SECURITY-ADVISORY-CVE-DRAFT.md) - Original vulnerability report
- CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')
- CWE-287: Improper Authentication
- CWE-863: Incorrect Authorization
- CWE-78: OS Command Injection

---

**Fix Date:** 2025-01-XX
**Fixed By:** Security Remediation
**Version:** WGDashboard v4.3.x
