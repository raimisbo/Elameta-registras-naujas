#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "registras.settings")

import django  # noqa
django.setup()

from django.urls import reverse  # noqa

# Čia laikom “sutartinius” URL vardus, kuriuos turi turėti flow
NAMES = [
    ("pozicijos:list", None),
    ("pozicijos:tbody", None),
    ("pozicijos:stats", None),
    ("pozicijos:create", None),
    ("pozicijos:import_csv", None),
    ("pozicijos:detail", {"pk": 1}),
    ("pozicijos:edit", {"pk": 1}),
    ("pozicijos:brezinys_upload", {"pk": 1}),
    ("pozicijos:brezinys_delete", {"pk": 1, "bid": 1}),
    ("pozicijos:brezinys_3d", {"pk": 1, "bid": 1}),
    ("pozicijos:proposal_prepare", {"pk": 1}),
    ("pozicijos:pdf", {"pk": 1}),
    ("pozicijos:kainos_list", {"pk": 1}),
    ("pozicijos:kaina_create", {"pk": 1}),
]

failed = 0
for name, kwargs in NAMES:
    try:
        url = reverse(name, kwargs=kwargs) if kwargs else reverse(name)
        print(f"[OK]   {name:28s} -> {url}")
    except Exception as e:
        failed += 1
        print(f"[FAIL] {name:28s} -> {repr(e)}")

print(f"\nSummary: failed={failed}")
sys.exit(1 if failed else 0)
