from __future__ import annotations

import re
import shutil
import sys
import platform
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.staticfiles import finders


# === Patch indikatoriai (sprendimas Firefox Blob worker'io URL rezoliucijai) ===
PATCH_OLD = 'let n="/static/pozicijos/o3dv/ext/occt-import-js/"'
PATCH_NEW = 'let n=new URL("/static/pozicijos/o3dv/ext/occt-import-js/",location.href).href'

# Jei O3DV build'as šiek tiek kitoks (tarpai/kabutės), regex padeda "check" režime:
PATCH_NEW_REGEX = re.compile(
    r'let\s+n\s*=\s*new\s+URL\(\s*["\']/static/pozicijos/o3dv/ext/occt-import-js/["\']\s*,\s*location\.href\s*\)\.href'
)

STATIC_TARGETS = [
    ("o3dv.min.js", "pozicijos/js/o3dv.min.js"),
    ("occt-import-js.js", "pozicijos/o3dv/ext/occt-import-js/occt-import-js.js"),
    ("occt-import-js.wasm", "pozicijos/o3dv/ext/occt-import-js/occt-import-js.wasm"),
    ("occt-import-js-worker.js", "pozicijos/o3dv/ext/occt-import-js/occt-import-js-worker.js"),
]


@dataclass
class CheckResult:
    status: str  # "OK" | "FAIL" | "WARN"
    message: str


@dataclass
class HttpCheck:
    name: str
    url: str
    ok: bool
    status: Optional[int]
    content_type: Optional[str]
    length: Optional[int]
    note: str = ""


# -----------------------------
# Helpers: static file location
# -----------------------------
def _iter_candidate_paths(static_rel_path: str) -> Iterable[Path]:
    found = finders.find(static_rel_path, all=True) or []
    for p in found:
        try:
            yield Path(p)
        except Exception:
            continue


def _pick_best_writable(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        if not (p.exists() and p.is_file()):
            continue
        try:
            with open(p, "a", encoding="utf-8", errors="ignore"):
                pass
            return p
        except Exception:
            continue
    return None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _check_patch(content: str) -> CheckResult:
    if PATCH_NEW in content or PATCH_NEW_REGEX.search(content):
        return CheckResult("OK", "O3DV OCCT URL patch yra (absoliutus URL per new URL(..., location.href).href).")

    if PATCH_OLD in content:
        return CheckResult("FAIL", "Rasta sena eilutė (let n=\"/static/...\"), Firefox/Blob worker režime gali lūžti.")

    return CheckResult(
        "WARN",
        "Neradau nei patched, nei senos tikslios eilutės. Gali būti kitas O3DV build'as – reikės peržiūrėti ranka."
    )


def _apply_patch(path: Path, content: str) -> CheckResult:
    if PATCH_NEW in content or PATCH_NEW_REGEX.search(content):
        return CheckResult("OK", "Jau patched – nieko nekeičiau.")

    if PATCH_OLD not in content:
        return CheckResult("WARN", "Automatiškai nepataisiau: nerasta sena needle eilutė šiame build'e.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak_{ts}")
    shutil.copy2(path, bak)

    updated = content.replace(PATCH_OLD, PATCH_NEW, 1)
    path.write_text(updated, encoding="utf-8")
    return CheckResult("OK", f"Pataisyta. Backup: {bak}")


# -----------------------------
# Helpers: HTTP checks
# -----------------------------
def _http_head_or_get(url: str, timeout: float = 5.0) -> HttpCheck:
    def do_req(method: str) -> tuple[int, str, Optional[int]]:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            ct = resp.headers.get("Content-Type", "") or ""
            cl = resp.headers.get("Content-Length")
            length: Optional[int]
            if cl is not None:
                try:
                    length = int(cl)
                except Exception:
                    length = None
            else:
                _ = resp.read(1)
                length = None
            return int(status), ct, length

    # HEAD
    try:
        status, ct, length = do_req("HEAD")
        return HttpCheck(name="", url=url, ok=(status in (200, 304)), status=status, content_type=ct, length=length)
    except urllib.error.HTTPError as e:
        if e.code not in (405, 501):
            return HttpCheck(name="", url=url, ok=False, status=e.code, content_type=None, length=None, note=str(e))
    except Exception as e:
        return HttpCheck(name="", url=url, ok=False, status=None, content_type=None, length=None, note=str(e))

    # GET fallback
    try:
        status, ct, length = do_req("GET")
        return HttpCheck(name="", url=url, ok=(status in (200, 304)), status=status, content_type=ct, length=length)
    except urllib.error.HTTPError as e:
        return HttpCheck(name="", url=url, ok=False, status=e.code, content_type=None, length=None, note=str(e))
    except Exception as e:
        return HttpCheck(name="", url=url, ok=False, status=None, content_type=None, length=None, note=str(e))


def _http_get_text(url: str, timeout: float = 5.0, max_bytes: int = 2_000_000) -> tuple[Optional[int], Optional[str], Optional[str]]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            ct = resp.headers.get("Content-Type", "") or ""
            raw = resp.read(max_bytes)
            text = raw.decode("utf-8", errors="ignore")
            return int(status), ct, text
    except urllib.error.HTTPError as e:
        return e.code, None, None
    except Exception:
        return None, None, None


# -----------------------------
# Helpers: report content
# -----------------------------
def _fmt_kv(k: str, v) -> str:
    return f"{k}: {v}"


def _settings_snapshot_lines() -> list[str]:
    out: list[str] = []
    out.append(_fmt_kv("DEBUG", getattr(settings, "DEBUG", None)))
    out.append(_fmt_kv("ALLOWED_HOSTS", getattr(settings, "ALLOWED_HOSTS", None)))
    out.append(_fmt_kv("STATIC_URL", getattr(settings, "STATIC_URL", None)))
    out.append(_fmt_kv("STATIC_ROOT", getattr(settings, "STATIC_ROOT", None)))
    out.append(_fmt_kv("STATICFILES_DIRS", getattr(settings, "STATICFILES_DIRS", None)))
    out.append(_fmt_kv("STATICFILES_FINDERS", getattr(settings, "STATICFILES_FINDERS", None)))
    out.append(_fmt_kv("MEDIA_URL", getattr(settings, "MEDIA_URL", None)))
    out.append(_fmt_kv("MEDIA_ROOT", getattr(settings, "MEDIA_ROOT", None)))

    mw = list(getattr(settings, "MIDDLEWARE", []) or [])
    out.append(_fmt_kv("MIDDLEWARE has WhiteNoise", any("whitenoise" in m.lower() for m in mw)))
    out.append(_fmt_kv("STATICFILES_STORAGE", getattr(settings, "STATICFILES_STORAGE", None)))
    out.append(_fmt_kv("STORAGES", getattr(settings, "STORAGES", None)))
    return out


def _static_findings_lines() -> list[str]:
    out: list[str] = []
    for name, rel in STATIC_TARGETS:
        found_all = finders.find(rel, all=True) or []
        if not found_all:
            out.append(f"MISSING: {name} ({rel}) -> finders nerado")
            continue
        out.append(f"FOUND: {name} ({rel}) -> {len(found_all)} kandidatų:")
        for p in found_all:
            out.append(f"  - {p}")
    return out


def _patch_status_from_file(o3dv_path: Path) -> str:
    try:
        s = _read_text(o3dv_path)
    except Exception as e:
        return f"WARN: nepavyko perskaityti o3dv.min.js ({e})"

    if PATCH_NEW in s or PATCH_NEW_REGEX.search(s):
        return "OK: pataisa yra (absoliutus OCCT base URL)."
    if PATCH_OLD in s:
        return "FAIL: rasta sena eilutė (let n=\"/static/...\"), Firefox Blob worker režime lūš."
    return "WARN: neradau nei patched, nei senos tikslios eilutės (gal kitas O3DV build'as)."


# -----------------------------
# Main command
# -----------------------------
class Command(BaseCommand):
    help = (
        "O3DV/OCCT įrankiai vienoje komandoje (check/fix/smoke/report) "
        "offline STEP importo stabilumui (Firefox Blob worker URL rezoliucija)."
    )

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcmd")

        # check
        p_check = subparsers.add_parser("check", help="Patikrina ar o3dv.min.js turi OCCT base URL patch'ą.")
        p_check.add_argument(
            "--path",
            dest="path",
            default=None,
            help="Kelias iki o3dv.min.js (jei nenori naudoti staticfiles finders). Pvz: pozicijos/static/pozicijos/js/o3dv.min.js",
        )

        # fix
        p_fix = subparsers.add_parser("fix", help="Pritaiko patch'ą o3dv.min.js (sukuria .bak backup).")
        p_fix.add_argument(
            "--path",
            dest="path",
            default=None,
            help="Kelias iki o3dv.min.js (rekomenduojama nurodyti app static failą).",
        )

        # smoke
        p_smoke = subparsers.add_parser("smoke", help="HTTP smoketest O3DV/OCCT resursams (reikia veikiančio serverio).")
        p_smoke.add_argument(
            "--base-url",
            dest="base_url",
            default="http://127.0.0.1:8000",
            help='Serverio bazinis URL (default: "http://127.0.0.1:8000").',
        )
        p_smoke.add_argument(
            "--step-url",
            dest="step_url",
            default=None,
            help='Pilnas STEP/STP URL arba kelias nuo root (pvz. "/media/.../file.stp").',
        )
        p_smoke.add_argument(
            "--timeout",
            dest="timeout",
            type=float,
            default=5.0,
            help="HTTP timeout sekundėmis (default: 5.0).",
        )

        # report
        p_report = subparsers.add_parser("report", help="Sugeneruoja diagnostinę ataskaitą į logs/ (settings+finders+optional HTTP).")
        p_report.add_argument(
            "--base-url",
            dest="base_url",
            default=None,
            help='Serverio bazinis URL HTTP daliai (pvz. "http://127.0.0.1:8000"). Jei nepaduota – HTTP dalis praleidžiama.',
        )
        p_report.add_argument(
            "--step-url",
            dest="step_url",
            default=None,
            help='STEP/STP URL HTTP daliai (pilnas arba pvz. "/media/.../file.stp"). Veikia tik kartu su --base-url.',
        )
        p_report.add_argument(
            "--timeout",
            dest="timeout",
            type=float,
            default=5.0,
            help="HTTP timeout sekundėmis (default: 5.0).",
        )
        p_report.add_argument(
            "--out",
            dest="out",
            default=None,
            help='Output failas (pvz. "logs/o3dv_diag.txt"). Jei nepaduota – sugeneruojamas timestamped logs/o3dv_diag_*.txt',
        )

    def handle(self, *args, **options):
        subcmd = options.get("subcmd")
        if not subcmd:
            self.stdout.write(self.style.ERROR("Nenurodyta subkomanda. Naudok: check | fix | smoke | report"))
            return

        if subcmd in ("check", "fix"):
            self._handle_check_or_fix(subcmd, options)
            return

        if subcmd == "smoke":
            self._handle_smoke(options)
            return

        if subcmd == "report":
            self._handle_report(options)
            return

        self.stdout.write(self.style.ERROR(f"Nežinoma subkomanda: {subcmd}"))

    # ----- check/fix -----
    def _resolve_o3dv_file(self, explicit_path: Optional[str], want_writable: bool) -> Optional[Path]:
        rel = "pozicijos/js/o3dv.min.js"
        candidates: list[Path] = []

        if explicit_path:
            candidates = [Path(explicit_path)]
        else:
            candidates = list(_iter_candidate_paths(rel))

        if not candidates:
            return None

        if want_writable:
            # jei fix – rinkis rašomą
            p = _pick_best_writable(candidates)
            return p
        else:
            # check – pakanka pirmo egzistuojančio
            for p in candidates:
                if p.exists() and p.is_file():
                    return p
            return None

    def _handle_check_or_fix(self, subcmd: str, options):
        explicit = options.get("path")
        want_writable = (subcmd == "fix")

        p = self._resolve_o3dv_file(explicit, want_writable=want_writable)
        if not p:
            self.stderr.write(self.style.ERROR("NERASTA o3dv.min.js (per finders arba --path)."))
            return

        self.stdout.write(f"Naudojamas failas: {p}")
        content = _read_text(p)

        check = _check_patch(content)
        if check.status == "OK":
            self.stdout.write(self.style.SUCCESS(f"{check.status}: {check.message}"))
        elif check.status == "FAIL":
            self.stderr.write(self.style.ERROR(f"{check.status}: {check.message}"))
        else:
            self.stdout.write(self.style.WARNING(f"{check.status}: {check.message}"))

        if subcmd == "fix":
            res = _apply_patch(p, content)
            if res.status == "OK":
                self.stdout.write(self.style.SUCCESS(f"{res.status}: {res.message}"))
            elif res.status == "FAIL":
                self.stderr.write(self.style.ERROR(f"{res.status}: {res.message}"))
            else:
                self.stdout.write(self.style.WARNING(f"{res.status}: {res.message}"))

        # papildomai – ar finders randa OCCT failus
        self.stdout.write("\nOCCT static failų patikra (finders):")
        for name, rel in STATIC_TARGETS[1:]:  # praleidžiam o3dv
            fp = finders.find(rel, all=False)
            if fp:
                self.stdout.write(self.style.SUCCESS(f" OK: {name:22} -> {fp}"))
            else:
                self.stdout.write(self.style.ERROR(f" MISSING: {name:22} ({rel})"))

    # ----- smoke -----
    def _handle_smoke(self, options):
        base_url = (options.get("base_url") or "http://127.0.0.1:8000").rstrip("/") + "/"
        step_url_opt = options.get("step_url")
        timeout = float(options.get("timeout") or 5.0)

        self.stdout.write(f"BASE URL: {base_url}")
        self.stdout.write("HTTP smoketest:")

        targets = [
            ("o3dv.min.js", "/static/pozicijos/js/o3dv.min.js"),
            ("occt-import-js.js", "/static/pozicijos/o3dv/ext/occt-import-js/occt-import-js.js"),
            ("occt-import-js.wasm", "/static/pozicijos/o3dv/ext/occt-import-js/occt-import-js.wasm"),
            ("occt-import-js-worker.js", "/static/pozicijos/o3dv/ext/occt-import-js/occt-import-js-worker.js"),
        ]

        checks: list[HttpCheck] = []
        any_fail = False

        for name, rel in targets:
            url = urljoin(base_url, rel.lstrip("/"))
            c = _http_head_or_get(url, timeout=timeout)
            c.name = name
            checks.append(c)

        if step_url_opt:
            if step_url_opt.startswith("http://") or step_url_opt.startswith("https://"):
                step_url = step_url_opt
            else:
                step_url = urljoin(base_url, step_url_opt.lstrip("/"))
            c = _http_head_or_get(step_url, timeout=timeout)
            c.name = "STEP/STP"
            checks.append(c)

        for c in checks:
            status_str = str(c.status) if c.status is not None else "NO-CONN"
            ct = c.content_type or "-"
            ln = str(c.length) if c.length is not None else "-"
            if c.ok:
                self.stdout.write(self.style.SUCCESS(f" OK  {c.name:22} {status_str:7}  {ct:40}  len={ln}  {c.url}"))
            else:
                any_fail = True
                note = f"  note={c.note}" if c.note else ""
                self.stdout.write(self.style.ERROR(f" FAIL {c.name:22} {status_str:7}  {ct:40}  len={ln}  {c.url}{note}"))

        # HTTP patch check iš realaus atsakymo
        o3dv_url = urljoin(base_url, "static/pozicijos/js/o3dv.min.js")
        status, ct, text = _http_get_text(o3dv_url, timeout=timeout)
        if status in (200, 304) and text:
            if PATCH_NEW in text:
                self.stdout.write(self.style.SUCCESS(" OK  PATCH: HTTP atsakyme matosi PATCH_NEW (absoliutus OCCT base URL)."))
            elif PATCH_OLD in text:
                self.stdout.write(self.style.ERROR(" FAIL PATCH: HTTP atsakyme matosi PATCH_OLD (sena /static bazė)."))
                any_fail = True
            else:
                self.stdout.write(self.style.WARNING(" WARN PATCH: HTTP atsakyme neradau nei PATCH_NEW, nei PATCH_OLD (gal kitas build'as)."))
        else:
            self.stdout.write(self.style.WARNING(" WARN PATCH: nepavyko perskaityti o3dv.min.js per HTTP patch patikrai."))

        # MIME rekomendacija wasm
        wasm = next((x for x in checks if x.name == "occt-import-js.wasm"), None)
        if wasm and wasm.ok:
            ct_low = (wasm.content_type or "").lower()
            if "application/wasm" in ct_low:
                self.stdout.write(self.style.SUCCESS(" OK  MIME: .wasm Content-Type yra application/wasm."))
            else:
                self.stdout.write(self.style.WARNING(f" WARN MIME: .wasm Content-Type yra '{wasm.content_type}'. Rekomenduotina application/wasm."))

        if any_fail:
            sys.exit(2)

    # ----- report -----
    def _handle_report(self, options):
        base_url_opt = options.get("base_url")
        step_url_opt = options.get("step_url")
        timeout = float(options.get("timeout") or 5.0)
        out_opt = options.get("out")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        report_path = Path(out_opt) if out_opt else (logs_dir / f"o3dv_diag_{ts}.txt")

        lines: list[str] = []
        lines.append("O3DV / OCCT DIAGNOSTIC REPORT")
        lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
        lines.append("")
        lines.append("== Environment ==")
        lines.append(_fmt_kv("Python", sys.version.replace("\n", " ")))
        lines.append(_fmt_kv("Platform", platform.platform()))
        lines.append(_fmt_kv("Django settings module", getattr(settings, "SETTINGS_MODULE", None)))
        lines.append("")

        lines.append("== Settings snapshot (relevant) ==")
        lines.extend(_settings_snapshot_lines())
        lines.append("")

        lines.append("== Staticfiles finders: target resources ==")
        lines.extend(_static_findings_lines())
        lines.append("")

        # Local patch status (iš pirmo finders kandidato)
        o3dv_candidates = list(finders.find("pozicijos/js/o3dv.min.js", all=True) or [])
        lines.append("== Patch status (local file) ==")
        if o3dv_candidates:
            o3dv_path = Path(o3dv_candidates[0])
            lines.append(_fmt_kv("o3dv.min.js path", o3dv_path))
            lines.append(_patch_status_from_file(o3dv_path))
        else:
            lines.append("WARN: o3dv.min.js nerastas per finders, patch status nepatikrintas.")
        lines.append("")

        # Optional HTTP dalis
        any_fail = False
        lines.append("== HTTP smoketest ==")
        if base_url_opt:
            base_url = base_url_opt.rstrip("/") + "/"
            lines.append(_fmt_kv("BASE URL", base_url))
            lines.append(_fmt_kv("timeout", timeout))
            lines.append("")

            http_targets = [
                ("o3dv.min.js", "/static/pozicijos/js/o3dv.min.js"),
                ("occt-import-js.js", "/static/pozicijos/o3dv/ext/occt-import-js/occt-import-js.js"),
                ("occt-import-js.wasm", "/static/pozicijos/o3dv/ext/occt-import-js/occt-import-js.wasm"),
                ("occt-import-js-worker.js", "/static/pozicijos/o3dv/ext/occt-import-js/occt-import-js-worker.js"),
            ]

            checks: list[HttpCheck] = []
            for name, rel in http_targets:
                url = urljoin(base_url, rel.lstrip("/"))
                c = _http_head_or_get(url, timeout=timeout)
                c.name = name
                checks.append(c)

            if step_url_opt:
                if step_url_opt.startswith("http://") or step_url_opt.startswith("https://"):
                    step_url = step_url_opt
                else:
                    step_url = urljoin(base_url, step_url_opt.lstrip("/"))
                c = _http_head_or_get(step_url, timeout=timeout)
                c.name = "STEP/STP"
                checks.append(c)

            for c in checks:
                status_str = str(c.status) if c.status is not None else "NO-CONN"
                ct = c.content_type or "-"
                ln = str(c.length) if c.length is not None else "-"
                ok = "OK" if c.ok else "FAIL"
                note = f" note={c.note}" if c.note else ""
                lines.append(f"{ok:4} {c.name:22} {status_str:7} ct={ct} len={ln}{note}")
                lines.append(f"     {c.url}")
                if not c.ok:
                    any_fail = True

            # HTTP patch check
            o3dv_url = urljoin(base_url, "static/pozicijos/js/o3dv.min.js")
            status, ct, text = _http_get_text(o3dv_url, timeout=timeout)
            lines.append("")
            lines.append("HTTP patch check:")
            lines.append(_fmt_kv("GET o3dv.min.js status", status))
            lines.append(_fmt_kv("Content-Type", ct))
            if status in (200, 304) and text:
                if PATCH_NEW in text:
                    lines.append("OK: HTTP atsakyme matosi PATCH_NEW (absoliutus OCCT base URL).")
                elif PATCH_OLD in text:
                    lines.append("FAIL: HTTP atsakyme matosi PATCH_OLD (sena /static bazė).")
                    any_fail = True
                else:
                    lines.append("WARN: HTTP atsakyme neradau nei PATCH_NEW, nei PATCH_OLD (gal kitas build'as).")
            else:
                lines.append("WARN: nepavyko perskaityti o3dv.min.js per HTTP patch patikrai.")

            # MIME rekomendacija wasm
            wasm = next((x for x in checks if x.name == "occt-import-js.wasm"), None)
            if wasm and wasm.ok:
                ct_low = (wasm.content_type or "").lower()
                if "application/wasm" in ct_low:
                    lines.append("OK: .wasm Content-Type yra application/wasm.")
                else:
                    lines.append(f"WARN: .wasm Content-Type yra '{wasm.content_type}' (rekomenduotina application/wasm).")
            lines.append("")
        else:
            lines.append("Praleista (nepaduotas --base-url).")
            lines.append("")

        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Ataskaita sugeneruota: {report_path}"))

        if any_fail:
            sys.exit(2)
