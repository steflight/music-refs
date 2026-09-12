#!/usr/bin/env python3
"""Génère une paire de clés VAPID (Web Push, MR-08) au format attendu par Music Refs.

Usage :
    python3 scripts/gen_vapid.py            # affiche les lignes à coller dans .env
    python3 scripts/gen_vapid.py --append .env   # les ajoute en fin de fichier

Formats : clé privée = scalaire EC P-256 brut (32 octets) en base64url sans « = »
(accepté par pywebpush/py_vapid) ; clé publique = point non compressé (65 octets)
en base64url, tel qu'attendu par `PushManager.subscribe({applicationServerKey})`.
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate() -> tuple[str, str]:
    priv = ec.generate_private_key(ec.SECP256R1())
    private_raw = priv.private_numbers().private_value.to_bytes(32, "big")
    public_raw = priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return b64url(public_raw), b64url(private_raw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--append", metavar="FICHIER", help="ajoute les variables en fin de ce fichier .env")
    ap.add_argument("--subject", default="mailto:contact@kladriva.ca", help="VAPID_SUBJECT (mailto:)")
    args = ap.parse_args()
    pub, priv = generate()
    lines = [
        "# MR-08 — clés VAPID générées par scripts/gen_vapid.py",
        f"VAPID_PUBLIC_KEY={pub}",
        f"VAPID_PRIVATE_KEY={priv}",
        f"VAPID_SUBJECT={args.subject}",
    ]
    if args.append:
        path = Path(args.append)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if "VAPID_PRIVATE_KEY=" in existing:
            print(f"{path} contient déjà VAPID_PRIVATE_KEY — rien ajouté.", file=sys.stderr)
            return 1
        with path.open("a", encoding="utf-8") as fh:
            if existing and not existing.endswith("\n"):
                fh.write("\n")
            fh.write("\n".join(lines) + "\n")
        print(f"Clés VAPID ajoutées à {path} (clé publique : {pub})")
        return 0
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
