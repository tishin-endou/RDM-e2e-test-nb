#!/usr/bin/env python3
import copy
import hashlib
import json
import os
import sys
import urllib.request
from urllib.error import HTTPError


def request(method: str, url: str, body: dict | None) -> None:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req):
        pass


def put(url: str, body: dict) -> None:
    request("PUT", url, body)


def post(url: str, body: dict | None = None) -> None:
    request("POST", url, body)


def head_exists(url: str) -> bool:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req):
            return True
    except HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: seed_kaken_es.py <json_path> <source_url>")

    json_path = sys.argv[1]
    source_url = sys.argv[2]
    base_uri = os.environ["KAKEN_ELASTIC_URI"].rstrip("/")

    with open(json_path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    payload = copy.deepcopy(document)
    payload["_source_url"] = source_url

    doc_id = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    index_url = f"{base_uri}/kaken_researchers"

    if not head_exists(index_url):
        put(index_url, {"settings": {"number_of_shards": 1, "number_of_replicas": 0}})
    put(f"{index_url}/_doc/{doc_id}", payload)
    post(f"{index_url}/_refresh")


if __name__ == "__main__":
    main()
