"""Etapa 1 — Localizar os ZIPs e ler ``frontiers.json`` / ``manifest.json``.

Responsabilidades:
- percorrer a estrutura de pastas exigida (persona_*/config_*/<sistema>/*.zip);
- abrir cada ZIP e extrair, de dentro dele, a fronteira final e a identidade;
- montar a lista de ``ExecutionRecord``.

Robustez: um ZIP inválido (corrompido, JSON malformado, manifest incompleto,
``metricNames`` inconsistente) é **ignorado com aviso** — nunca derruba a análise.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np

from . import config
from .models import ExecutionRecord, FrontierData, ManifestData


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


def read_frontiers(zip_path: Path) -> FrontierData | None:
    """Extrai a fronteira final de ``frontiers.json``.

    Retorna ``None`` quando o arquivo não existe ou está indisponível
    (``available: false``). Levanta ``ValueError`` quando o formato é inválido
    (nomes ausentes/inconsistentes com as colunas ou com ``NUM_OBJECTIVES``).
    """
    data = _read_json_from_zip(zip_path, config.FRONTIERS_FILENAME)
    if not data or not data.get("available", False):
        return None

    names = tuple(data.get("metricNames") or ())
    if len(names) != config.NUM_OBJECTIVES:
        raise ValueError(
            f"metricNames inválido: esperados {config.NUM_OBJECTIVES}, obtidos {len(names)}"
        )

    rows = data.get("frontier") or []
    if rows:
        frontier = np.asarray(rows, dtype=float)
        if frontier.ndim != 2 or frontier.shape[1] != len(names):
            raise ValueError(
                f"fronteira com {frontier.shape[1] if frontier.ndim == 2 else '?'} colunas, "
                f"esperadas {len(names)}"
            )
    else:
        frontier = np.empty((0, len(names)))

    embedded_min = embedded_max = None
    normalization = data.get("normalization") or {}
    bounds = normalization.get("bounds") or {}
    raw_min, raw_max = bounds.get("min"), bounds.get("max")
    if raw_min is not None and raw_max is not None:
        if len(raw_min) != len(names) or len(raw_max) != len(names):
            raise ValueError("bounds de normalização com dimensão diferente de metricNames")
        embedded_min = np.asarray(raw_min, dtype=float)
        embedded_max = np.asarray(raw_max, dtype=float)

    generation = data.get("generation")
    return FrontierData(
        metric_names=names,
        frontier=frontier,
        embedded_min=embedded_min,
        embedded_max=embedded_max,
        generation=int(generation) if generation is not None else None,
    )


def read_manifest(zip_path: Path) -> ManifestData:
    """Lê a identidade do grupo a partir do ``manifest.json``.

    - persona      <- study.personaId
    - config       <- study.configId (fallback: study.configLabel)
    - system       <- run.sourceId (fallback: run.instance)
    - repetition   <- study.repetition
    - participant  <- study.participantCode
    - generations  <- run.generations
    - stop_reason  <- manifest.timing.stopReason
    """
    data = _read_json_from_zip(zip_path, config.MANIFEST_FILENAME) or {}
    study = data.get("study") or {}
    run = data.get("run") or {}
    timing = data.get("timing") or {}

    return ManifestData(
        persona=study.get("personaId"),
        config=study.get("configId") or study.get("configLabel"),
        system=run.get("sourceId") or run.get("instance"),
        repetition=study.get("repetition"),
        participant=study.get("participantCode") or "",
        generations=run.get("generations"),
        stop_reason=timing.get("stopReason"),
    )


def build_records(zips: list[Path]) -> tuple[list[ExecutionRecord], list[str]]:
    """Transforma ZIPs em ``ExecutionRecord``.

    Retorna ``(records, descartes)``. Cada ZIP é tratado isoladamente: falhas
    viram uma mensagem em ``descartes`` e não interrompem o processamento.
    """
    records: list[ExecutionRecord] = []
    skipped: list[str] = []

    for zip_path in zips:
        try:
            frontiers = read_frontiers(zip_path)
            if frontiers is None:
                skipped.append(f"{zip_path.name}: frontiers.json indisponível")
                continue

            manifest = read_manifest(zip_path)
            missing = [name for name, value in (
                ("study.personaId", manifest.persona),
                ("study.configId/configLabel", manifest.config),
                ("run.sourceId", manifest.system),
                ("study.repetition", manifest.repetition),
            ) if value is None or value == ""]
            if missing:
                skipped.append(f"{zip_path.name}: manifest incompleto ({', '.join(missing)})")
                continue

            records.append(ExecutionRecord(
                persona=str(manifest.persona),
                config=str(manifest.config),
                system=str(manifest.system),
                repetition=int(manifest.repetition),
                metric_names=frontiers.metric_names,
                frontier=frontiers.frontier,
                participant=str(manifest.participant or ""),
                source_zip=str(zip_path),
                generation=frontiers.generation,
                generations=int(manifest.generations) if manifest.generations is not None else None,
                stop_reason=manifest.stop_reason,
                embedded_min=frontiers.embedded_min,
                embedded_max=frontiers.embedded_max,
            ))
        except Exception as exc:  # noqa: BLE001 — um ZIP ruim não pode derrubar a análise
            skipped.append(f"{zip_path.name}: {type(exc).__name__}: {exc}")

    return records, skipped
