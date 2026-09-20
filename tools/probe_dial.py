#!/usr/bin/env python3
"""Discover and inspect a DIAL receiver without launching an application."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any


DIAL_ST = "urn:dial-multiscreen-org:service:dial:1"


def discovery_request() -> bytes:
    return (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 1\r\n"
        f"ST: {DIAL_ST}\r\n"
        "\r\n"
    ).encode("ascii")


def probe(host: str, timeout: float) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(discovery_request(), (host, 1900))
        response, source = sock.recvfrom(64 * 1024)
    finally:
        sock.close()
    status, headers = parse_ssdp(response)
    report: dict[str, Any] = {
        "source_address": source[0],
        "source_port": source[1],
        "status": status,
        "server": headers.get("server"),
        "service_type": headers.get("st"),
    }
    usn = headers.get("usn")
    if usn:
        report["usn_sha256"] = hashlib.sha256(usn.encode()).hexdigest()
    location = headers.get("location")
    if not location:
        return report
    report["location"] = location
    description, description_headers = _http_get(location, timeout)
    report["description_http_status"] = description_headers["status"]
    report["description_bytes"] = len(description)
    application_url = description_headers.get("application-url")
    if not application_url:
        return report
    report["application_url"] = application_url
    youtube_body, youtube_headers = _http_get(
        application_url.rstrip("/") + "/YouTube", timeout
    )
    report["youtube"] = {
        "http_status": youtube_headers["status"],
        "content_type": youtube_headers.get("content-type"),
        "body_bytes": len(youtube_body),
        **_parse_youtube_status(youtube_body),
    }
    return report


def parse_ssdp(data: bytes) -> tuple[str, dict[str, str]]:
    text = data.decode("iso-8859-1")
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or not lines[0]:
        raise ValueError("empty SSDP response")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        key, separator, value = line.partition(":")
        if separator:
            headers[key.strip().lower()] = value.strip()
    return lines[0].strip(), headers


def _http_get(url: str, timeout: float) -> tuple[bytes, dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(64 * 1024)
            headers: dict[str, Any] = {
                key.lower(): value for key, value in response.headers.items()
            }
            headers["status"] = response.status
            return body, headers
    except urllib.error.HTTPError as exc:
        body = exc.read(64 * 1024)
        headers = {key.lower(): value for key, value in exc.headers.items()}
        headers["status"] = exc.code
        return body, headers


def _parse_youtube_status(body: bytes) -> dict[str, Any]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {"parseable_xml": False}
    elements = {
        element.tag.rsplit("}", 1)[-1]: element for element in root.iter()
    }
    link = elements.get("link")
    options = elements.get("options")
    additional = elements.get("additionalData")
    additional_keys: list[str] = []
    screen_id_length = 0
    if additional is not None:
        additional_keys = sorted(
            child.tag.rsplit("}", 1)[-1] for child in additional
        )
        screen_id = next(
            (
                child.text
                for child in additional
                if child.tag.rsplit("}", 1)[-1] == "screenId"
            ),
            None,
        )
        screen_id_length = len(screen_id) if screen_id else 0
    return {
        "parseable_xml": True,
        "state": elements.get("state").text
        if elements.get("state") is not None
        else None,
        "allow_stop": options.attrib.get("allowStop")
        if options is not None
        else None,
        "run_link_present": link is not None
        and link.attrib.get("rel") == "run",
        "run_href": link.attrib.get("href") if link is not None else None,
        "additional_data_keys": additional_keys,
        "screen_id_present": bool(screen_id_length),
        "screen_id_length": screen_id_length,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover and inspect an isolated YouTube DIAL receiver"
    )
    parser.add_argument("host")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    try:
        report = probe(args.host, args.timeout)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"DIAL probe failed: {exc}") from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
