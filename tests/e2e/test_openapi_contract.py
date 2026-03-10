from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_openapi_has_required_paths() -> None:
    spec_path = ROOT / "contracts/openapi/connector-v1.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    paths = spec.get("paths", {})
    assert "/healthz" in paths
    assert "/v1/scan/attachment" in paths
    assert "/v1/scan/attachment/document_scan_report" in paths


def test_examples_validate_against_snapshots() -> None:
    req_schema = _load_json(ROOT / "contracts/schemas/snapshots/request.schema.json")
    res_schema = _load_json(ROOT / "contracts/schemas/snapshots/response.schema.json")
    err_schema = _load_json(ROOT / "contracts/schemas/snapshots/error.schema.json")

    req_examples = [
        ROOT / "contracts/schemas/examples/request/scan_attachment_extracted_text.json",
        ROOT / "contracts/schemas/examples/request/scan_attachment_file_base64.json",
    ]
    for item in req_examples:
        jsonschema.validate(_load_json(item), req_schema)

    res_examples = [
        ROOT / "contracts/schemas/examples/response/scan_attachment_allow.json",
        ROOT / "contracts/schemas/examples/response/scan_attachment_quarantine.json",
        ROOT / "contracts/schemas/examples/response/scan_attachment_block.json",
    ]
    for item in res_examples:
        jsonschema.validate(_load_json(item), res_schema)

    jsonschema.validate(
        _load_json(ROOT / "contracts/schemas/examples/response/error_invalid_signature.json"),
        err_schema,
    )
