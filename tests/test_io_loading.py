"""Testes de leitura/robustez dos ZIPs (manifest + frontiers)."""

from __future__ import annotations

import json
import zipfile

import numpy as np

from analise_estudo import io_loading

METRICS = ["Coupling", "Cohesion", "Overhead", "Functionality", "ReusePerMS"]


def _manifest(**overrides):
    manifest = {
        "study": {
            "personaId": "P1-Reflective-Architect",
            "configId": "cfg_real",
            "repetition": 1,
            "participantCode": "RA1",
        },
        "run": {"sourceId": "spring-petclinic", "generations": 1000},
        "timing": {"stopReason": "GENERATIONS"},
    }
    manifest.update(overrides)
    return manifest


def _frontiers(**overrides):
    data = {
        "available": True,
        "metricNames": METRICS,
        "frontier": [[0.1, 0.2, 0.3, 0.4, 0.5]],
        "generation": 999,
        "normalization": {"bounds": {"min": [0] * 5, "max": [10] * 5}},
    }
    data.update(overrides)
    return data


def _write_zip(path, manifest, frontiers):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("frontiers.json", json.dumps(frontiers))


def test_build_records_reads_identity_and_completeness(tmp_path):
    zip_path = tmp_path / "run.zip"
    _write_zip(zip_path, _manifest(), _frontiers())

    records, skipped = io_loading.build_records([zip_path])

    assert skipped == []
    assert len(records) == 1
    record = records[0]
    assert record.persona == "P1-Reflective-Architect"
    assert record.config == "cfg_real"
    assert record.system == "spring-petclinic"
    assert record.participant == "RA1"
    assert record.generation == 999
    assert record.generations == 1000
    assert record.completo is True
    assert record.embedded_min is not None


def test_build_records_falls_back_to_config_label(tmp_path):
    manifest = _manifest()
    del manifest["study"]["configId"]
    manifest["study"]["configLabel"] = "config_3"
    zip_path = tmp_path / "run.zip"
    _write_zip(zip_path, manifest, _frontiers())

    records, _ = io_loading.build_records([zip_path])
    assert records[0].config == "config_3"


def test_corrupt_zip_is_skipped_without_raising(tmp_path):
    zip_path = tmp_path / "corrupt.zip"
    zip_path.write_bytes(b"not a zip file")

    records, skipped = io_loading.build_records([zip_path])
    assert records == []
    assert len(skipped) == 1


def test_invalid_metric_names_is_skipped(tmp_path):
    zip_path = tmp_path / "badmetrics.zip"
    _write_zip(zip_path, _manifest(), _frontiers(metricNames=["Coupling"]))

    records, skipped = io_loading.build_records([zip_path])
    assert records == []
    assert len(skipped) == 1


def test_unavailable_frontiers_is_skipped(tmp_path):
    zip_path = tmp_path / "unavailable.zip"
    _write_zip(zip_path, _manifest(), {"available": False, "reason": "no candidates"})

    records, skipped = io_loading.build_records([zip_path])
    assert records == []
    assert len(skipped) == 1


def test_manifest_missing_identity_is_skipped(tmp_path):
    manifest = {"study": {}, "run": {}}
    zip_path = tmp_path / "noident.zip"
    _write_zip(zip_path, manifest, _frontiers())

    records, skipped = io_loading.build_records([zip_path])
    assert records == []
    assert len(skipped) == 1


def test_empty_frontier_is_kept_with_zero_rows(tmp_path):
    zip_path = tmp_path / "empty.zip"
    _write_zip(zip_path, _manifest(), _frontiers(frontier=[]))

    records, skipped = io_loading.build_records([zip_path])
    assert skipped == []
    assert records[0].frontier.shape == (0, len(METRICS))
    assert np.isnan(records[0].frontier).sum() == 0
