# RQ3 — absorção da primeira intervenção do DM

> Atualizado em 2026-11-25. Substitui o desenho anterior (todas as interações, valor final/+100,
> 239 runs), que está preservado em `resultados_rq3/` apenas como legado.

## Desenho

- **Coorte:** intenções estruturais criadas na **primeira interação** de cada execução.
- **Execuções:** 240 no total; **231** com intenção estrutural na primeira interação.
  - 9 excluídas: 7 sem intenção estrutural na primeira (primeira intenção em interação
    posterior), 1 só com congelamento na primeira (estrutural em 300) e 1 sem nenhuma intenção
    estrutural.
- **Intenções:** 16.447 (16.123 `SEPARATE`, 324 `CO_LOCATE`); mediana de 65 por run (9–229).
- **Freeze:** 34 intenções de congelamento do primeiro evento ficam fora; a análise é
  `STRUCTURAL`.
- **Configuração:** 3–5 runs por configuração (sete células com menos de 5); 17–20 runs por
  nível nos testes.
- **Desfechos por run** (média das intenções da primeira interação):
  - **A** = parcial em +25 (absorção);
  - **C** = parcial em +100 (consolidação; **primário**);
  - **N** = parcial em `g2−1` (persistência até a segunda interação; janela de 219 gerações em P1,
    249 em P2 e 149 em P3);
  - **S_C** = estrita em +100 (secundária).
- O valor em `g2` **não** é usado: a amostragem da geração da interação é pós-decisão.

## Resultados

Medianas dos runs:

| Grupo | A (+25) | C (+100) | N (g2−1) | S_C |
|---|---:|---:|---:|---:|
| P1 · JPetStore | 0,760 | 0,874 | 0,927 | 0,746 |
| P1 · Spring PetClinic | 0,763 | 0,806 | 0,833 | 0,629 |
| P2 · JPetStore | 0,899 | 0,983 | 0,991 | 0,956 |
| P2 · Spring PetClinic | 0,868 | 0,923 | 0,948 | 0,856 |
| P3 · JPetStore | 0,773 | 0,927 | 0,975 | 0,830 |
| P3 · Spring PetClinic | 0,694 | 0,785 | 0,818 | 0,547 |

- **Consolidação crescente** em todos os grupos (0,79–0,98 em +100; 0,82–0,99 em N).
- **98% das intenções são `SEPARATE`**; o agregado é dominado por esse tipo. Em P3 · Spring, o
  ganho do R-NSGA-III é de `SEPARATE` (0,712 → 0,895) e a parcial de `CO_LOCATE` cai
  (0,581 → 0,501); em P3 · JPetStore, a estrita de `CO_LOCATE` cai (0,359 → 0,193) e a de
  `SEPARATE` sobe (0,711 → 0,915).
- **Restrição** é o fator mais consistente: PENALTY > KILL em 6/6 grupos no +100, com 5/6
  significativos (P3 · Spring fica em p_adj = 0,200).
- **Algoritmo:** R-NSGA-III acima em P3, mas no desfecho primário +100 o contraste é +0,089 e
  +0,160 (p_adj = 0,057, não significativo a 5%); em N, +0,060 e +0,187 (p_adj = 0,028), com
  horizontes desiguais. A12 em +100: 0,274 e 0,269 (abaixo de 0,5 favorece o R-NSGA-III).
- **Elitismo:** sem direção consistente (menor p_adj = 0,240).
- **Confundimento:** em P2 · Spring, o único participante com os dois níveis tem NSGA-III acima
  do R-NSGA-III (0,970 vs 0,782); o agregado é inflado pelo participante que só executou
  R-NSGA-III (0,981). Os p não são ajustados para o agrupamento de runs por participante.
  Com 3–5 runs por configuração, o desenho não permite ranking causal.

## Arquivos

Scripts (em `analise_estudo/`):

- `extrair_rq3_primeira_interacao.py` — ZIPs → `resultados_rq3/primeira_interacao/intents.csv`.
  Aceita `--zips` (default `$ITOMICROSERVICES_V5`) e `--out`; lê `decisions.json` para as
  gerações e `seriesColumns` do JSON.
- `analise_rq3_primeira_interacao.py` — lê `intents.csv` e gera `runs.csv`, `descritivas.csv`,
  `fatores_algoritmo.csv`, `fatores_elitismo.csv`, `fatores_restricao.csv`, `configs.csv`,
  `2x2.csv`, `tipos.csv` e as figuras.

Saídas em `resultados_rq3/primeira_interacao/` (o `intents.csv` é 2 MB e está versionado).
