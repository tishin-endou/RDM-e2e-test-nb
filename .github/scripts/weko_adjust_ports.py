#!/usr/bin/env python3
"""Apply CI-specific adjustments to WEKO files (compose, Dockerfile)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

import yaml


BITNAMI_PREFIX = "bitnami/"
BITNAMI_LEGACY_PREFIX = "bitnamilegacy/"


def sanitize_ports(
    data: Dict[str, object],
    services: Iterable[str],
    keep: Dict[str, List[str]] | None = None,
) -> bool:
    modified = False
    services_def = data["services"]
    keep = keep or {}

    for service in services:
        service_def = services_def[service]
        ports = service_def["ports"]

        if service in keep:
            allowed = keep[service]
            filtered = [entry for entry in ports if entry in allowed]
            if filtered == ports:
                continue
            service_def["ports"] = filtered
        else:
            service_def.pop("ports", None)

        modified = True

    return modified


def rewrite_images(data: Dict[str, object]) -> bool:
    modified = False
    services_def = data["services"]

    for service_name, service_def in services_def.items():
        if "image" not in service_def:
            continue
        image = service_def["image"]
        if not image.startswith(BITNAMI_PREFIX):
            continue
        service_def["image"] = image.replace(BITNAMI_PREFIX, BITNAMI_LEGACY_PREFIX, 1)
        modified = True

    return modified


def main() -> None:
    parser = argparse.ArgumentParser(description="Adjust WEKO docker-compose for CI use")
    parser.add_argument("compose_file", type=Path, help="Path to docker-compose YAML input")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for the adjusted compose file (default: overwrite input)",
    )
    parser.add_argument(
        "--services",
        nargs="*",
        default=[
            "web",
            "postgresql",
            "pgpool",
            "redis",
            "elasticsearch",
            "rabbitmq",
            "flower",
            "inbox",
            "mongo",
        ],
        help="Service names whose host ports should be removed",
    )
    parser.add_argument(
        "--keep-port",
        action="append",
        default=[],
        metavar="SERVICE:HOSTPORT",
        help="Optional list of service:host_port entries to keep (e.g., nginx:80:80)",
    )
    parser.add_argument(
        "--nginx-dockerfile",
        type=Path,
        help="Optional path to nginx Dockerfile for additional patching",
    )
    args = parser.parse_args()

    compose_path = args.compose_file
    output_path = args.output or compose_path

    with compose_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    keep: Dict[str, List[str]] = {}
    for entry in args.keep_port:
        if ":" not in entry:
            raise SystemExit(f"Invalid --keep-port entry: {entry}")
        service, mapping = entry.split(":", 1)
        keep.setdefault(service, []).append(mapping)

    changed_ports = sanitize_ports(data, args.services, keep)
    changed_images = rewrite_images(data)

    if changed_ports or changed_images:
        with output_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, sort_keys=False)
        print(
            f"Updated {output_path} (ports adjusted: {changed_ports}, images adjusted: {changed_images})"
        )
    else:
        print("No compose adjustments were applied")

    if args.nginx_dockerfile:
        patch_nginx = patch_nginx_dockerfile(args.nginx_dockerfile)
        if patch_nginx:
            print(f"Patched nginx Dockerfile: {args.nginx_dockerfile}")
        else:
            print("No nginx Dockerfile adjustments were applied")


def patch_nginx_dockerfile(dockerfile: Path) -> bool:
    text = dockerfile.read_text(encoding="utf-8")
    updated = text.replace(
        "http://nginx.org/packages/ubuntu", "https://nginx.org/packages/ubuntu"
    )
    if updated == text:
        return False
    dockerfile.write_text(updated, encoding="utf-8")
    return True


if __name__ == "__main__":
    main()
