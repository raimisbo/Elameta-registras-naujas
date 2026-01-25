#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "registras.settings")


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def _print(res: CheckResult) -> None:
    status = "OK" if res.ok else "FAIL"
    line = f"[{status}] {res.name}"
    if res.detail:
        line += f" — {res.detail}"
    print(line)


def main() -> int:
    import django  # noqa
    django.setup()

    from django.conf import settings
    if "testserver" not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append("testserver")

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import transaction
    from django.test import Client
    from django.urls import reverse

    from pozicijos.models import Pozicija, PozicijosBrezinys

    results: list[CheckResult] = []

    # 1) Pozicija (seed)
    poz = Pozicija.objects.order_by("id").first()
    created_here = False
    if poz is None:
        with transaction.atomic():
            poz = Pozicija.objects.create(klientas="UPLOAD_TEST", projektas="UPLOAD_TEST")
        created_here = True
        results.append(CheckResult("create Pozicija (seed)", True, f"id={poz.id}"))
    else:
        results.append(CheckResult("use existing Pozicija", True, f"id={poz.id}"))

    # 2) Upload endpoint
    try:
        url = reverse("pozicijos:brezinys_upload", kwargs={"pk": poz.id})
        results.append(CheckResult("reverse upload endpoint", True, url))
    except Exception as e:
        results.append(CheckResult("reverse upload endpoint", False, repr(e)))
        print("\n== Upload flow test results ==")
        for r in results:
            _print(r)
        return 1

    # 3) POST su failu "failas" (SVARBU: failą dedam į data dict)
    c = Client()
    before = PozicijosBrezinys.objects.filter(pozicija=poz).count()

    upload = SimpleUploadedFile(
        "smoke_upload.txt",
        b"SMOKE UPLOAD CONTENT",
        content_type="text/plain",
    )

    try:
        r = c.post(
            url,
            data={
                "pavadinimas": "SMOKE",
                "failas": upload,  # <- teisingas būdas Django test client
            },
            follow=False,
        )
        ok_status = r.status_code in (200, 302)
        results.append(CheckResult("POST upload (status)", ok_status, f"{r.status_code} {url}"))
    except Exception as e:
        results.append(CheckResult("POST upload (request)", False, repr(e)))

    after = PozicijosBrezinys.objects.filter(pozicija=poz).count()
    results.append(CheckResult("DB insert check", after == before + 1, f"before={before}, after={after}"))

    # papildomas diagnostinis rodiklis (jei kas nors filtruojasi netikėtai)
    total = PozicijosBrezinys.objects.count()
    results.append(CheckResult("DB total PozicijosBrezinys", total >= after, f"total={total}"))

    print("\n== Upload flow test results ==")
    for r in results:
        _print(r)

    failed = [r for r in results if not r.ok]
    print("\n== Summary ==")
    print(f"Total: {len(results)} | Failed: {len(failed)}")

    if created_here:
        print(f"\nNOTE: Sukurta testinė Pozicija id={poz.id} (nešalinau).")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
