# Script de análise dos resultados — i-toMicroservices

Calcula, para cada execução do estudo, os indicadores de qualidade da **fronteira
final**: **Hypervolume (HV)**, **IGD+**, **ED ao ideal** (média e mínima) e
**spacing**. As configurações são comparadas **dentro de cada sistema**
(ex.: `spring-petclinic`, `jpetstore`), em um espaço normalizado comum.

O pacote é **autocontido**: não depende de outros projetos; os indicadores são
reimplementados aqui.

## Requisitos

- Python 3.11+
- `numpy` e `scipy` (>= 1.7)

```bash
pip install -r requirements.txt
```

> Não há venv incluído. Se preferir: `python -m venv .venv && source .venv/bin/activate`.

## Entrada esperada

Os dados de cada execução são **ZIPs** contendo, no mínimo:

- **`manifest.json`** — identidade do grupo:
  - `study.personaId` → persona
  - `study.configId` → configuração (id resolvido)
  - `run.sourceId` (ou `run.instance`) → sistema
  - `study.repetition` → número da execução
- **`frontiers.json`** — campo `frontier` (vetores **crus** dos 5 objetivos) e
  `metricNames` (ordem das colunas).

Os demais arquivos do ZIP (ex.: `indicators.json`, `normalizedFrontier`) **não** são
usados — a normalização é refeita aqui.

### Estrutura de pastas exigida

```
<root>/
  persona_1/
    config_1/
      jpetstore/
        execucao1.zip ... execucao5.zip
      spring-petclinic/
        execucao1.zip ... execucao5.zip
    config_2/
    ...
  persona_2/
  persona_3/
```

Se os ZIPs estiverem todos soltos em uma pasta plana, use o utilitário para
organizá-los (ele lê o `manifest.json` de cada ZIP):

```bash
python organizar_zip.py --src /caminho/zips_planos --dst /caminho/dados_organizados
```

## Como rodar

```bash
python -m analise_estudo --root /caminho/dados_organizados --out analise_estudo/resultados
```

Se `--out` for omitido, a saída vai para `analise_estudo/resultados`.

## Saída

```
resultados/
  indicadores_por_execucao.csv   # 1 linha por execução (base para a estatística)
  por_sistema/
    spring-petclinic.json        # limites, Z* e execuções do sistema
    jpetstore.json
  resumo.json                    # configuração usada + contagens
```

Colunas do CSV:

`persona, config, sistema, repeticao, n_pontos, hv, igd_plus, ed_media, ed_min, spacing`

Direção dos indicadores: **HV** maior é melhor; **IGD+**, **ED** e **spacing** menor
é melhor.

## O que o script faz

1. Localiza os ZIPs em `persona_*/config_*/<sistema>/*.zip`.
2. Lê a fronteira final crua e a identidade (manifest) de cada ZIP.
3. Agrupa as execuções por **sistema**.
4. Descarta linhas penalizadas (qualquer objetivo `>= 1e5`).
5. Calcula os **limites conjuntos** (mín/máx pooled) de todas as execuções do
   sistema e **normaliza todas com esses mesmos limites**.
6. Constrói a **fronteira de referência Z\*** = união não-dominada de todos os pontos
   normalizados do sistema.
7. Calcula, por execução: **HV** (referência fixa `1.1` em cada objetivo), **IGD+**
   (contra Z\*), **ED** ao ideal `(0,0,0,0,0)` (média e mínima) e **spacing**.
8. Exporta CSV + JSON.

## Decisões / padronizações

- **Direção dos objetivos:** todos em convenção de **minimização** (como vêm do
  export). Três deles (Coesão, Funcionalidade, Reúso) estão armazenados **invertidos**
  (`1/valor`); mantemos como está, sem reinverter.
- **Normalização e Z\*:** únicos **por sistema** (todas as personas/configs/execuções
  juntas) — é o que torna as configurações **comparáveis entre si**.
- **HV:** ponto de referência fixo `(1.1, 1.1, 1.1, 1.1, 1.1)` no espaço normalizado.
- **Alinhamento por nome:** as colunas são pareadas pelo **nome** do objetivo
  (`metricNames`), nunca pela posição.
- **Sem testes estatísticos:** o script entrega os indicadores por execução; os testes
  (ex.: Kruskal-Wallis, Nemenyi, Vargha-Delaney) ficam a cargo da análise.

Todas as constantes/limiares ficam em `analise_estudo/config.py`.

## Observações

- **Hypervolume**: exato para 2 e 3 objetivos; para **M >= 4** é aproximado por Monte
  Carlo com amostragem **Sobol** e **semente fixa** (determinístico e reprodutível).
- **IGD+** e **HV** só são comparáveis **dentro do mesmo sistema** (mesma normalização
  e mesma Z\*).
- O `frontiers.json` traz apenas a **última geração** de cada execução: a análise mede
  a qualidade da solução final, **não** convergência por geração.
- **ReusePerMS (objetivo 5)** é uma **fração discreta** e pode assumir poucos valores
  (ex.: 1 e 1.25 na forma invertida). Após o min-max, o melhor vira 0 e o pior vira 1;
  se a união não-dominada retiver só o melhor, a coluna 5 do Z\* fica toda 0 — nesse
  caso o objetivo **não diferencia** as soluções (não é erro).

## Estrutura do repositório

| Arquivo | Responsabilidade |
|---|---|
| `analise_estudo/config.py` | Constantes e decisões metodológicas |
| `analise_estudo/models.py` | Dataclasses de entrada/saída |
| `analise_estudo/io_loading.py` | Localizar ZIPs e ler `frontiers.json`/`manifest.json` |
| `analise_estudo/objective_space.py` | Filtro, limites, normalização, não-dominados (Z\*) |
| `analise_estudo/indicators.py` | HV, IGD+, ED, spacing |
| `analise_estudo/pipeline.py` | Orquestração por sistema |
| `analise_estudo/export.py` | Escrita de CSV e JSON |
| `analise_estudo/run.py` | CLI (`python -m analise_estudo`) |
| `organizar_zip.py` | Organiza ZIPs planos na estrutura `persona/config/sistema` |
