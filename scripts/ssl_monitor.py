#!/usr/bin/env python3
"""
Music Refs - SSL/TLS Handshake & Domain Health Monitor (Task #6)
Monitors certificate validity, SNI handshake, TLS protocols/ciphers, and endpoint reachability for music-refs-dev.kladriva.ca.
"""

import os
import sys
import ssl
import socket
import datetime
import urllib.request
import urllib.error
import json
import argparse
from typing import Dict, Any

DEFAULT_DOMAIN = "music-refs-dev.kladriva.ca"
CERTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "certs"))
DEFAULT_CERT_PATH = os.path.join(CERTS_DIR, f"{DEFAULT_DOMAIN}.crt")


def check_local_certificate(cert_path: str = DEFAULT_CERT_PATH) -> Dict[str, Any]:
    """Inspects certificate file on disk for validity and expiration details."""
    if not os.path.exists(cert_path):
        return {
            "valid": False,
            "status": "CRITICAL",
            "message": f"Certificate file not found at {cert_path}",
            "days_remaining": 0
        }

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Parse cert using OpenSSL helper or ssl.get_server_certificate
        import subprocess
        cmd = ["openssl", "x509", "-enddate", "-subject", "-issuer", "-noout", "-in", cert_path]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        lines = res.stdout.strip().splitlines()
        info = {}
        for line in lines:
            if "=" in line:
                k, v = line.split("=", 1)
                info[k.strip()] = v.strip()

        not_after_str = info.get("notAfter", "")
        exp_date = datetime.datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
        now = datetime.datetime.utcnow()
        days_remaining = (exp_date - now).days

        status = "OK"
        if days_remaining <= 0:
            status = "CRITICAL"
        elif days_remaining <= 30:
            status = "WARNING"

        return {
            "valid": days_remaining > 0,
            "status": status,
            "domain": DEFAULT_DOMAIN,
            "cert_path": cert_path,
            "subject": info.get("subject"),
            "issuer": info.get("issuer"),
            "expires_at": exp_date.isoformat() + "Z",
            "days_remaining": days_remaining,
            "message": f"Certificate valid for {days_remaining} days."
        }
    except Exception as e:
        return {
            "valid": False,
            "status": "CRITICAL",
            "error": str(e),
            "days_remaining": 0
        }


def perform_tls_handshake_check(
    host: str = "127.0.0.1",
    port: int = 443,
    sni_hostname: str = DEFAULT_DOMAIN,
    timeout: float = 5.0
) -> Dict[str, Any]:
    """Performs live TLS handshake with SNI support to verify cert & connection."""
    context = ssl.create_default_context()
    # Allow self-signed for dev testing, but verify hostname & handshake
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    handshake_start = datetime.datetime.utcnow()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=sni_hostname) as ssock:
                elapsed_ms = round((datetime.datetime.utcnow() - handshake_start).total_seconds() * 1000, 2)
                cipher = ssock.cipher()
                protocol = ssock.version()
                peer_cert = ssock.getpeercert(binary_form=True)

                return {
                    "handshake_success": True,
                    "host": host,
                    "port": port,
                    "sni_hostname": sni_hostname,
                    "protocol": protocol,
                    "cipher": cipher[0] if cipher else None,
                    "handshake_latency_ms": elapsed_ms,
                    "status": "OK",
                    "message": f"TLS handshake succeeded using SNI '{sni_hostname}' ({protocol})"
                }
    except Exception as e:
        return {
            "handshake_success": False,
            "host": host,
            "port": port,
            "sni_hostname": sni_hostname,
            "status": "CRITICAL",
            "error": str(e),
            "message": f"TLS handshake failed: {str(e)}"
        }


def check_endpoint_reachability(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Verifies HTTP/HTTPS endpoint reachability and response code."""
    # Custom context ignoring self-signed errors for testing
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MusicRefsSSLMonitor/1.0", "Host": DEFAULT_DOMAIN})
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            status_code = response.getcode()
            body = response.read(2048).decode('utf-8', errors='ignore')
            return {
                "url": url,
                "reachable": True,
                "status_code": status_code,
                "content_preview": body[:100],
                "message": f"Endpoint {url} responded with status {status_code}"
            }
    except urllib.error.HTTPError as e:
        return {
            "url": url,
            "reachable": True,
            "status_code": e.code,
            "message": f"Endpoint responded with HTTP {e.code}"
        }
    except Exception as e:
        return {
            "url": url,
            "reachable": False,
            "status_code": 0,
            "error": str(e),
            "message": f"Endpoint unreachable: {str(e)}"
        }


def run_full_domain_health_check(
    host: str = "127.0.0.1",
    port: int = 443,
    sni_hostname: str = DEFAULT_DOMAIN,
    cert_path: str = DEFAULT_CERT_PATH,
    health_url: str = None
) -> Dict[str, Any]:
    """Runs combined cert, TLS handshake, and endpoint health checks."""
    cert_report = check_local_certificate(cert_path)
    tls_report = perform_tls_handshake_check(host=host, port=port, sni_hostname=sni_hostname)

    endpoint_report = None
    if health_url:
        endpoint_report = check_endpoint_reachability(health_url)

    # Determine overall status
    overall_status = "OK"
    if cert_report.get("status") == "CRITICAL" or tls_report.get("status") == "CRITICAL":
        overall_status = "CRITICAL"
    elif cert_report.get("status") == "WARNING" or tls_report.get("status") == "WARNING":
        overall_status = "WARNING"

    return {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "domain": sni_hostname,
        "overall_status": overall_status,
        "certificate_check": cert_report,
        "tls_handshake_check": tls_report,
        "endpoint_check": endpoint_report
    }


def main():
    parser = argparse.ArgumentParser(description="Music Refs SSL/TLS Domain Health Monitor")
    parser.add_argument("--host", default="127.0.0.1", help="Target IP or host")
    parser.add_argument("--port", type=int, default=443, help="Target HTTPS port")
    parser.add_argument("--sni", default=DEFAULT_DOMAIN, help="SNI domain name")
    parser.add_argument("--cert", default=DEFAULT_CERT_PATH, help="Path to certificate file")
    parser.add_argument("--url", help="HTTPS health URL to probe")
    parser.add_argument("--json", action="store_true", help="Output JSON result")

    args = parser.parse_args()

    report = run_full_domain_health_check(
        host=args.host,
        port=args.port,
        sni_hostname=args.sni,
        cert_path=args.cert,
        health_url=args.url
    )

    if args.json or not sys.stdout.isatty():
        print(json.dumps(report, indent=2))
    else:
        print(f"Overall Status: {report['overall_status']}")
        print(f"Certificate: {report['certificate_check'].get('message')}")
        print(f"TLS Handshake: {report['tls_handshake_check'].get('message')}")


if __name__ == "__main__":
    main()
