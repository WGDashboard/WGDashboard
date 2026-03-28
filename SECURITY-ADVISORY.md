# WGDashboard Security Advisory

## Advisory ID
`WGD-2026-001`

## Title
Multiple security vulnerabilities in WGDashboard `v4.3.x` enable unauthenticated file disclosure, authentication bypass, and potential command execution.

## Summary
A security review of WGDashboard source code identified three high-impact issues affecting internet-exposed deployments:

1. Unauthenticated path traversal in file download endpoint.
2. Authentication bypass caused by substring-based whitelist logic.
3. Command injection surface due to shell command construction with `shell=True` and user-influenced values.

These issues can be chained to increase impact in real-world deployments.

## Affected Product
- **Product:** WGDashboard
- **Affected versions:** v4.3.x (including templates indicating `v4.3.0.1` / runtime code indicating `v4.3.1`)
- **Deployment condition:** Risk is highest when bound to public interface (`app_ip=0.0.0.0`) and reachable from untrusted networks.
- **Patched versions:** Fixes applied to current source tree

## Environment Used for Reproduction
- OS: Linux
- HTTP client: `curl`
- Default app port from template: `10086`
- Authentication enabled: `auth_req=true`

---

## Vulnerability 1: Unauthenticated Path Traversal / Arbitrary File Read

### Identifier
`WGD-2026-001-PT`

### CWE
- **CWE-22**: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')

### Component / Location
- File: `src/dashboard.py`
- Endpoint: `GET {APP_PREFIX}/fileDownload`
- Relevant logic: approximately lines `1213-1219`

### Description
The `file` query parameter is joined directly into a filesystem path under `download/` without canonicalization and base-path enforcement. Attackers can use `../` sequences to escape the intended directory.

### Attack Vector
Remote, unauthenticated HTTP request.

### Safe Proof of Concept
```bash
curl "http://<HOST>:10086/fileDownload?file=../../../../etc/hostname"
```

### Expected Result
Request should be rejected as invalid path traversal attempt.

### Observed Result (Pre-Fix)
Server returns file contents outside `download/` if path exists.

### Security Impact
- Arbitrary file read from server filesystem.
- Potential disclosure of secrets, configuration, keys, and system metadata.

### Severity
**High**

### Fix Applied
- Path canonicalization using `pathlib.Path.resolve()`
- Strict prefix checking against intended `download` base directory
- Symlink traversal detection and blocking
- Authentication now required for file download endpoint

---

## Vulnerability 2: Authentication Bypass via Substring Whitelist Logic

### Identifier
`WGD-2026-001-AB`

### CWE
- **CWE-287**: Improper Authentication
- **CWE-863**: Incorrect Authorization

### Component / Location
- File: `src/dashboard.py`
- Middleware: `@app.before_request` auth gate
- Relevant logic: approximately lines `249-260`

### Description
Authorization logic uses substring checks against `request.path` with a whitelist (including `"/client"`). Because matching is substring-based, unrelated admin endpoints such as `/api/clients/*` satisfy whitelist conditions and bypass authentication checks.

### Attack Vector
Remote, unauthenticated HTTP request to endpoints containing whitelisted substrings.

### Safe Proof of Concept
```bash
curl "http://<HOST>:10086/api/clients/allClients"
```

Optional additional verification:
```bash
curl -X POST "http://<HOST>:10086/api/clients/generatePasswordResetLink" \
  -H "Content-Type: application/json" \
  -d '{"ClientID":"<existing-client-id>"}'
```

### Expected Result
`401 Unauthorized` for unauthenticated requests.

### Observed Result (Pre-Fix)
Requests are processed without valid admin session.

### Security Impact
- Unauthorized read/write access to client-management features.
- Can expose user data and trigger privileged workflows.

### Severity
**Critical**

### Fix Applied
- Replaced substring matching with exact path matching
- Explicit public endpoint whitelist with full paths
- Default-deny policy for all non-public endpoints
- Directory-based matching only for static resources

---

## Vulnerability 3: Command Injection Surface in WireGuard Operations (Post-Auth / Chained)

### Identifier
`WGD-2026-001-CI`

### CWE
- **CWE-78**: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')

### Component / Location
Representative examples:
- `src/modules/WireguardConfiguration.py` (e.g., around lines `563`, `618`, `639`, `691`, etc.)
- `src/modules/Peer.py` (e.g., around line `97`)

### Description
Multiple code paths build shell commands using f-strings and execute them with `shell=True`, while incorporating values that may be influenced through API-level inputs and object fields (e.g., peer IDs, allowed IP strings, configuration names/metadata flow).

### Risk Note
Even if some fields are expected to follow WireGuard formats, command composition with `shell=True` significantly increases exploitability if validation is bypassed, incomplete, or regresses.

### Demonstration Guidance (Safe)
Use non-destructive, controlled-lab input containing shell metacharacters and observe:
- command errors,
- unexpected shell parsing behavior,
- security logs indicating command injection attempts.

Example test payload concept (do **not** run destructive commands):
```text
public_key = "AAA;echo WGD_POC;"
```

### Security Impact
- Potential arbitrary command execution with service privileges.
- In common deployments, impact may be severe if process runs with elevated permissions.

### Severity
**Critical** (if reachable) / **High** (as latent dangerous pattern)

### Fix Applied
- Eliminated all `shell=True` usage for WireGuard command execution
- Implemented `ExecuteWireguardCommand()` function using argument vectors
- Added strict input validation for all command arguments:
  - `ValidateWireguardIdentifier()` - alphanumeric, underscore, hyphen only (no dots)
  - `ValidateWireguardPublicKey()` - Base64 validation
  - `ValidateWireguardPrivateKey()` - Base64 validation
  - `ValidateWireguardAllowedIPs()` - IP/CIDR validation
  - `ValidateUUIDFilename()` - UUID temp file validation
- All subprocess calls now use `subprocess.run()` or `subprocess.check_output()` without shell

---

## Chaining Scenario
A plausible attack chain on internet-exposed instances:
1. Use auth bypass to access privileged API paths.
2. Use privileged functions to inject/modify peer/config data.
3. Reach shell-executing code paths and trigger command injection.
4. Achieve remote code execution (environment-dependent).

**Note:** This chain is now mitigated as all three vulnerabilities have been fixed.

---

## Verification Checklist (Post-Fix)
1. Start patched WGDashboard build.
2. Ensure `app_ip=0.0.0.0` and app reachable from another host.
3. Confirm `auth_req=true`.
4. Execute test (`/fileDownload?...`) and verify path traversal is blocked.
5. Execute test (`/api/clients/allClients`) without login and verify `401 Unauthorized`.
6. Review command-execution code paths confirm no `shell=True` usage remains.

---

## Security Fixes Applied

### 1) Path Traversal Fix
- Canonicalized requested path with `pathlib.Path.resolve()`
- Enforced strict prefix check against intended `download` base directory using `relative_to()`
- Added symlink traversal detection and blocking
- Rejected absolute paths and traversal components
- Authentication now required for file download endpoint

### 2) Authentication / Authorization Fix
- Replaced substring matching with strict exact path matching
- Separated public endpoints from protected API namespaces
- Added default-deny policy for all API routes except explicit allowlist
- Directory-based matching only for static resources

### 3) Command Execution Hardening
- Eliminated all `shell=True` for WireGuard command execution
- Used argument-vector form: `subprocess.run(["wg", "set", ...], check=True)`
- Strictly validated and normalized all command arguments against strong allowlists
- Added input validation functions for all WireGuard-specific inputs

### 4) Operational Hardening
- Bind dashboard to local/private IP only.
- Restrict access with firewall / reverse proxy ACL / VPN.
- Rotate secrets and credentials after patching.

---

## Detection / Forensics Tips
- Review access logs for:
  - requests to `/fileDownload` with `..` sequences,
  - unauthenticated requests to `/api/clients/*`,
  - anomalous peer/config updates.
- Review process/system logs for failed or malformed `wg`/`awg` shell invocations.

---

## Risk Assessment

| Vulnerability | Severity | Status |
|--------------|----------|--------|
| Path Traversal | High | **Fixed** |
| Authentication Bypass | Critical | **Fixed** |
| Command Injection | Critical | **Fixed** |

### CVSS v3.1 Scores (Pre-Fix)
- Path traversal: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` (approx. **7.5 High**)
- Auth bypass: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L` (approx. **9.1 Critical**)
- Command injection (reachable): `AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H` (approx. **9.9 Critical**)

---

## Timeline
- Discovery date: `<YYYY-MM-DD>`
- Initial report to maintainer: `<YYYY-MM-DD>`
- Maintainer acknowledgment: `<YYYY-MM-DD>`
- **Fixes applied: March 28, 2026**
- Public disclosure: `<YYYY-MM-DD>`

---

## Credits
Reported by: `<Your Name / Handle>`
Fixed by: Security Remediation Team

---

## Disclaimer
This document is for responsible disclosure and defensive remediation. PoCs are intentionally limited to non-destructive demonstrations.

---

## References
- CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')
- CWE-287: Improper Authentication
- CWE-863: Incorrect Authorization
- CWE-78: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')
