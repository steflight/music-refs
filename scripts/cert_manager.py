#!/usr/bin/env python3
"""
Music Refs - SSL Certificate Manager (Task #6)
Automates SSL certificate issuance, SAN configuration, expiry checking, and renewal for music-refs-dev.kladriva.ca.
"""

import os
import sys
import datetime
import subprocess
import json
import argparse
from typing import Dict, Any, Tuple

DOMAIN = "music-refs-dev.kladriva.ca"
CERTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "certs"))
CERT_PATH = os.path.join(CERTS_DIR, f"{DOMAIN}.crt")
KEY_PATH = os.path.join(CERTS_DIR, f"{DOMAIN}.key")
CONFIG_PATH = os.path.join(CERTS_DIR, "openssl.cnf")
DEFAULT_RENEWAL_THRESHOLD_DAYS = 30


def ensure_certs_dir():
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR, exist_ok=True)


def generate_openssl_config(output_path: str = CONFIG_PATH) -> str:
    ensure_certs_dir()
    config_content = f"""[req]
default_bits        = 2048
default_md          = sha256
prompt              = no
distinguished_name  = req_distinguished_name
req_extensions      = req_ext
x509_extensions     = v3_req

[req_distinguished_name]
C  = CA
ST = Quebec
L  = Montreal
O  = Music Refs Dev Team
OU = DevOps
CN = {DOMAIN}

[req_ext]
subjectAltName = @alt_names

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth

[alt_names]
DNS.1 = {DOMAIN}
DNS.2 = *.music-refs-dev.kladriva.ca
DNS.3 = localhost
IP.1  = 127.0.0.1
"""
    with open(output_path, "w") as f:
        f.write(config_content)
    return output_path


def generate_certificate(
    domain: str = DOMAIN,
    cert_path: str = CERT_PATH,
    key_path: str = KEY_PATH,
    days_valid: int = 365,
    force: bool = False
) -> Dict[str, Any]:
    """Generates an SSL certificate with SAN support for the specified domain."""
    ensure_certs_dir()
    openssl_cnf = generate_openssl_config()

    if os.path.exists(cert_path) and os.path.exists(key_path) and not force:
        # Check if cert is still valid
        status = check_certificate_expiry(cert_path)
        if status.get("valid") and status.get("days_remaining", 0) > DEFAULT_RENEWAL_THRESHOLD_DAYS:
            return {
                "status": "skipped",
                "message": f"Certificate for {domain} already exists and is valid for {status.get('days_remaining')} days.",
                "cert_path": cert_path,
                "key_path": key_path,
                "expires_at": status.get("expires_at")
            }

    cmd = [
        "openssl", "req", "-x509", "-nodes",
        "-days", str(days_valid),
        "-newkey", "rsa:2048",
        "-keyout", key_path,
        "-out", cert_path,
        "-config", openssl_cnf
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        os.chmod(key_path, 0o600)
        os.chmod(cert_path, 0o644)
        status = check_certificate_expiry(cert_path)
        return {
            "status": "created_or_renewed",
            "message": f"Successfully generated SSL/TLS certificate for {domain}",
            "cert_path": cert_path,
            "key_path": key_path,
            "expires_at": status.get("expires_at"),
            "days_remaining": status.get("days_remaining")
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"OpenSSL command failed: {e.stderr}",
            "error": str(e)
        }


def check_certificate_expiry(cert_path: str = CERT_PATH) -> Dict[str, Any]:
    """Inspects certificate file and returns validity, expiration date, and remaining days."""
    if not os.path.exists(cert_path):
        return {
            "valid": False,
            "error": "Certificate file does not exist",
            "days_remaining": 0
        }

    cmd = ["openssl", "x509", "-enddate", "-noout", "-in", cert_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # e.g. notAfter=Sep  2 01:23:45 2027 GMT
        output = res.stdout.strip()
        date_str = output.split("=", 1)[1].strip() if "=" in output else ""
        
        # Parse OpenSSL date format
        exp_date = datetime.datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
        now = datetime.datetime.utcnow()
        days_remaining = (exp_date - now).days

        return {
            "valid": days_remaining > 0,
            "expires_at": exp_date.isoformat() + "Z",
            "days_remaining": days_remaining,
            "needs_renewal": days_remaining <= DEFAULT_RENEWAL_THRESHOLD_DAYS
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Failed to parse certificate expiry: {str(e)}",
            "days_remaining": 0
        }


def renew_certificate_if_needed(
    cert_path: str = CERT_PATH,
    key_path: str = KEY_PATH,
    threshold_days: int = DEFAULT_RENEWAL_THRESHOLD_DAYS,
    force: bool = False
) -> Dict[str, Any]:
    """Automated certificate renewal workflow."""
    status = check_certificate_expiry(cert_path)
    
    if force or not status.get("valid") or status.get("needs_renewal"):
        renewal_res = generate_certificate(cert_path=cert_path, key_path=key_path, force=True)
        renewal_res["action_taken"] = "renewed"
        return renewal_res

    return {
        "status": "valid",
        "action_taken": "none",
        "message": f"Certificate is valid. {status.get('days_remaining')} days remaining (threshold: {threshold_days} days).",
        "days_remaining": status.get("days_remaining"),
        "expires_at": status.get("expires_at")
    }


def get_certificate_details(cert_path: str = CERT_PATH) -> Dict[str, Any]:
    """Extracts SAN, subject, and issuer info from certificate."""
    if not os.path.exists(cert_path):
        return {"error": "Certificate file not found"}

    cmd = ["openssl", "x509", "-text", "-noout", "-in", cert_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = res.stdout
        
        san_lines = [line.strip() for line in output.splitlines() if "DNS:" in line or "IP Address:" in line]
        expiry_info = check_certificate_expiry(cert_path)

        return {
            "domain": DOMAIN,
            "cert_path": cert_path,
            "subject_alt_names": san_lines,
            "expiry": expiry_info
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Music Refs SSL Certificate Manager")
    parser.add_argument("--generate", action="store_true", help="Generate SSL certificate")
    parser.add_argument("--check-expiry", action="store_true", help="Check certificate expiry")
    parser.add_argument("--renew", action="store_true", help="Renew certificate if needed")
    parser.add_argument("--force", action="store_true", help="Force renewal/generation")
    parser.add_argument("--details", action="store_true", help="Show certificate details")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    result = {}
    if args.generate:
        result = generate_certificate(force=args.force)
    elif args.renew:
        result = renew_certificate_if_needed(force=args.force)
    elif args.check_expiry:
        result = check_certificate_expiry()
    elif args.details:
        result = get_certificate_details()
    else:
        # Default behavior: ensure valid certificate exists
        result = renew_certificate_if_needed(force=args.force)

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
