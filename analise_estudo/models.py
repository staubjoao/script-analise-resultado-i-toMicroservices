"""Estruturas de dados usadas em toda a análise.

São dataclasses simples para deixar explícito o que entra (uma execução = um ZIP)
e o que sai (os indicadores calculados).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ExecutionRecord:
    """Uma execução: a fronteira final de um ZIP + sua identidade do manifest.

    Attributes:
        persona: valor de ``study.personaId`` no manifest.
        config: valor de ``study.configId`` no manifest (configuração resolvida).
        system: valor de ``run.sourceId`` (ou ``run.instance``) no manifest.
        repetition: valor de ``study.repetition`` no manifest.
        metric_names: ordem das colunas da fronteira (``metricNames``).
        frontier: matriz (n, M) com os valores CRUS (minimização), sem normalizar.
        source_zip: caminho do ZIP de origem (rastreabilidade).
    """

    persona: str
    config: str
    system: str
    repetition: int
    metric_names: tuple[str, ...]
    frontier: np.ndarray
    source_zip: str = ""


@dataclass
class ExecutionResult:
    """Indicadores calculados para UMA execução (no espaço normalizado)."""

    record: ExecutionRecord
    n_points: int  # tamanho da fronteira efetivamente usada (pós-filtro)
    hv: float
    igd_plus: float
    ed_mean: float
    ed_min: float
    spacing: float


@dataclass
class SystemResult:
    """Resultado agregado de um sistema (todos os personas/configs/execuções).

    A normalização e a fronteira de referência são únicas por SISTEMA, para que
    as configurações sejam comparáveis entre si.
    """

    system: str
    metric_names: tuple[str, ...]
    bounds_min: np.ndarray  # (M,) mínimos conjuntos (pooled, valores crus)
    bounds_max: np.ndarray  # (M,) máximos conjuntos (pooled, valores crus)
    reference_size: int  # |Z*|
    reference_front: np.ndarray  # (|Z*|, M) no espaço normalizado
    executions: list[ExecutionResult]
