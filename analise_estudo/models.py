"""Estruturas de dados usadas em toda a análise.

São dataclasses simples para deixar explícito o que entra (uma execução = um ZIP)
e o que sai (os indicadores calculados).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FrontierData:
    """Conteúdo lido de ``frontiers.json``."""

    metric_names: tuple[str, ...]
    frontier: np.ndarray
    embedded_min: np.ndarray | None = None
    embedded_max: np.ndarray | None = None
    generation: int | None = None


@dataclass(frozen=True)
class ManifestData:
    """Identidade lida de ``manifest.json``."""

    persona: str
    config: str
    system: str
    repetition: int
    participant: str = ""
    generations: int | None = None
    stop_reason: str | None = None


@dataclass(frozen=True)
class ExecutionRecord:
    """Uma execução: a fronteira final de um ZIP + sua identidade do manifest.

    Attributes:
        persona: valor de ``study.personaId`` no manifest.
        config: valor de ``study.configId`` (fallback ``study.configLabel``).
        system: valor de ``run.sourceId`` (ou ``run.instance``) no manifest.
        repetition: valor de ``study.repetition`` no manifest.
        participant: valor de ``study.participantCode`` (rastreabilidade).
        metric_names: ordem das colunas da fronteira (``metricNames``).
        frontier: matriz (n, M) com os valores CRUS (minimização), sem normalizar.
        source_zip: caminho do ZIP de origem.
        generation: geração da fronteira (``frontiers.json.generation``).
        generations: orçamento de gerações do run (``manifest.run.generations``).
        stop_reason: motivo de parada (``manifest.timing.stopReason``).
        embedded_min/max: limites da normalização de referência do backend, se houver.
    """

    persona: str
    config: str
    system: str
    repetition: int
    metric_names: tuple[str, ...]
    frontier: np.ndarray
    participant: str = ""
    source_zip: str = ""
    generation: int | None = None
    generations: int | None = None
    stop_reason: str | None = None
    embedded_min: np.ndarray | None = None
    embedded_max: np.ndarray | None = None

    @property
    def completo(self) -> bool:
        """True quando a fronteira é da última geração do orçamento configurado."""
        if self.generations is None or self.generation is None:
            return False
        return self.generation >= self.generations - 1


@dataclass
class ExecutionResult:
    """Indicadores calculados para UMA execução (no espaço normalizado)."""

    record: ExecutionRecord
    n_points: int  # pontos ÚNICOS usados (após deduplicação)
    hv: float
    igd_plus: float
    ed_mean: float
    ed_min: float
    spacing: float
    n_duplicates: int = 0


@dataclass
class SystemResult:
    """Resultado agregado de um grupo (sistema ou persona × sistema).

    A normalização e a fronteira de referência são únicas por grupo, para que as
    configurações sejam comparáveis entre si.
    """

    system: str
    metric_names: tuple[str, ...]
    bounds_min: np.ndarray
    bounds_max: np.ndarray
    reference_size: int
    reference_front: np.ndarray
    executions: list[ExecutionResult]
    group_by: str = "system"
    normalization: str = "pooled"
    zstar: str = "full"
    bounds_source: str = "pooled"
