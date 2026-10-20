"""Etapa 0 — Configurações e constantes da análise.

Aqui ficam TODAS as decisões metodológicas em um único lugar, para facilitar a
revisão: estrutura de pastas, nomes de arquivos, ponto de referência do HV,
limiar de penalização e parâmetros do cálculo de HV em dimensão alta.
"""

from __future__ import annotations

# --- Estrutura de pastas esperada (a partir da raiz de dados) ---------------
#   <raiz>/persona_*/config_*/<sistema>/*.zip
# A estrutura é EXIGIDA para localizar os ZIPs; a identidade (persona, config,
# sistema, repetição) é lida do manifest.json de cada ZIP.
PERSONA_GLOB = "persona_*"
CONFIG_GLOB = "config_*"
ZIP_GLOB = "*.zip"

# --- Nomes dos arquivos lidos de dentro de cada ZIP -------------------------
MANIFEST_FILENAME = "manifest.json"
FRONTIERS_FILENAME = "frontiers.json"

# --- Convenção numérica -----------------------------------------------------
# Número de objetivos (5): Coupling, Cohesion, Overhead, Functionality, Reuse.
# Todos estão em convenção de MINIMIZAÇÃO no export (3 deles invertidos como
# 1/valor). Mantemos a convenção como está, sem reinverter (decisão do estudo).
NUM_OBJECTIVES = 5

# Ponto de referência fixo do Hypervolume, JÁ no espaço normalizado [0,1]^M.
# Mesmo valor usado pelo pipeline Java (InstanceIndicatorReference.HV_REFERENCE).
HV_REFERENCE = 1.1

# Ideal do ED no espaço normalizado: (0, 0, 0, 0, 0).
ED_IDEAL_VALUE = 0.0

# Linha penalizada (qualquer objetivo >= 1e5) é descartada — espelha o Java
# (MicroservicesProblem.evaluate) e o pipeline de indicadores.
PENALTY_THRESHOLD = 1e5

# --- Hypervolume em M >= 4 (Monte Carlo via Sobol/QMC) ----------------------
# A semente fixa garante que o resultado seja reprodutível (determinístico).
HV_SAMPLES = 1 << 16  # 65.536 amostras
HV_SEED = 12345

# --- Saída ------------------------------------------------------------------
DEFAULT_OUT_DIR = "analise_estudo/resultados"
