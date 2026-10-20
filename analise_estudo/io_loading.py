"""Etapa 1 — Localizar os ZIPs e ler ``frontiers.json`` / ``manifest.json``.

Responsabilidades:
- percorrer a estrutura de pastas exigida (persona_*/config_*/<sistema>/*.zip);
- abrir cada ZIP e extrair, de dentro dele, a fronteira final e a identidade;
- montar a lista de ``ExecutionRecord``.

Nenhuma decisão de cálculo acontece aqui: só leitura e extração de dados.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np

from . import config
from .models import ExecutionRecord


def discover_zips(root: Path) -> list[Path]:
    """Percorre ``<raiz>/persona_*/config_*/<sistema>/*.zip``.

    Exige a estrutura de pastas (decisão do estudo). Retorna a lista de ZIPs
    encontrados, em ordem estável.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"Diretório raiz não encontrado: {root}")

    zips: list[Path] = []
    for persona_dir in sorted(root.glob(config.PERSONA_GLOB)):
        if not persona_dir.is_dir():
            continue
        for config_dir in sorted(persona_dir.glob(config.CONFIG_GLOB)):
            if not config_dir.is_dir():
                continue
            # Qualquer subpasta (jpetstore, spring-petclinic, ...) é um "sistema".
            for system_dir in sorted(p for p in config_dir.iterdir() if p.is_dir()):
                zips.extend(sorted(system_dir.glob(config.ZIP_GLOB)))
    return zips


def _read_json_from_zip(zip_path: Path, filename: str) -> dict | None:
    """Lê um JSON de dentro do ZIP; retorna ``None`` se o arquivo não existir."""
    with zipfile.ZipFile(zip_path) as zf:
        if filename not in zf.namelist():
            return None
        with zf.open(filename) as fh:
            return json.load(fh)


def read_frontiers(zip_path: Path) -> tuple[tuple[str, ...], np.ndarray] | None:
    """Extrai ``(metric_names, frontier)`` do ``frontiers.json``.

    Retorna ``None`` quando o arquivo não existe ou está marcado como
    indisponível (``available: false``).
    """
    data = _read_json_from_zip(zip_path, config.FRONTIERS_FILENAME)
    if not data or not data.get("available", False):
        return None

    names = tuple(data.get("metricNames") or ())
    rows = data.get("frontier") or []
    frontier = np.asarray(rows, dtype=float) if rows else np.empty((0, len(names)))
    return names, frontier


def read_manifest_group(zip_path: Path) -> tuple[str, str, str, int | None]:
    """Lê a identidade do grupo a partir do ``manifest.json``.

    Retorna ``(persona, config, system, repetition)``, onde:
      - persona     <- study.personaId
      - config      <- study.configId
      - system      <- run.sourceId (fallback: run.instance)
      - repetition  <- study.repetition
    """
    data = _read_json_from_zip(zip_path, config.MANIFEST_FILENAME) or {}
    study = data.get("study") or {}
    run = data.get("run") or {}

    persona = study.get("personaId")
    config_id = study.get("configId")
    system = run.get("sourceId") or run.get("instance")
    repetition = study.get("repetition")
    return persona, config_id, system, repetition


def build_records(zips: list[Path]) -> list[ExecutionRecord]:
    """Transforma uma lista de ZIPs na lista de ``ExecutionRecord``.

    ZIPs sem ``frontiers.json`` disponível, ou sem os campos de identidade no
    manifest, são ignorados com um aviso (não quebram a execução).
    """
    records: list[ExecutionRecord] = []
    for zip_path in zips:
        frontiers = read_frontiers(zip_path)
        if frontiers is None:
            print(f"[aviso] frontiers.json indisponível — ignorando: {zip_path}")
            continue

        metric_names, frontier = frontiers
        persona, config_id, system, repetition = read_manifest_group(zip_path)

        missing = [name for name, value in (
            ("study.personaId", persona),
            ("study.configId", config_id),
            ("run.sourceId", system),
            ("study.repetition", repetition),
        ) if value is None]
        if missing:
            print(f"[aviso] manifest incompleto ({', '.join(missing)}) — ignorando: {zip_path}")
            continue

        records.append(ExecutionRecord(
            persona=str(persona),
            config=str(config_id),
            system=str(system),
            repetition=int(repetition),
            metric_names=metric_names,
            frontier=frontier,
            source_zip=str(zip_path),
        ))
    return records
