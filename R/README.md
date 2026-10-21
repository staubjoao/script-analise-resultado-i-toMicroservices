# Base de análise estatística em R (HV, IGD+, ED)

Este diretório é um **ponto de partida** para a análise estatística dos
resultados. A ideia é que o participante **rode os passos** e leia/adapte o
código — não que receba um relatório pronto.

- `funcoes.R` — funções auxiliares (Levene, Dunn, A12 etc.).
- `analise_estatistica.R` — script guiado, com os passos numerados e comentados.

## Premissa: 1 CSV = 1 persona × 1 sistema

O pipeline Python gera **um CSV por sistema** em
`analise_estudo/resultados/por_sistema/<sistema>.csv`. Cada grupo analisa **uma
persona**, então cada arquivo tem **uma persona e um sistema**.

- **Unidade de análise:** **indicador** (`hv`, `igd_plus`, `ed_media`, `ed_min`).
- O sistema já está fixado pelo CSV.
- Em cada indicador há **8 configurações**, com **n = 5 execuções
  independentes** cada.

## O CSV (como os dados são apresentados)

Uma linha por execução, 40 linhas (8 configurações × 5). Colunas:

`persona, participante, config, sistema, repeticao, geracao, completo, n_pontos,
n_duplicados, hv, igd_plus, ed_media, ed_min, spacing, source_zip`

Exemplo de linhas:

```
persona,config,sistema,repeticao,completo,hv,igd_plus,ed_media,...
P2-Systematic-Decoupler,nsgaiii__elit_on__penalty,spring-petclinic,1,True,0.771,0.181,...
P2-Systematic-Decoupler,nsgaiii__elit_on__penalty,spring-petclinic,2,True,0.824,0.161,...
...
```

O script lê esse CSV, seleciona o indicador e a configuração, e monta os
vetores de valores para cada teste.

## Requisitos

- R >= 4.x
- **Apenas base R** (sem pacotes externos). Levene e Dunn estão implementados em
  `funcoes.R`.

## Como rodar

1. Tenha o CSV de **um sistema** (ex.:
   `analise_estudo/resultados/por_sistema/spring-petclinic.csv`).

2. Rode:

```bash
Rscript R/analise_estatistica.R
```

Quando solicitado, **cole o caminho** do CSV (aceita aspas, espaços e `~`).

Ou passe o caminho e o indicador como argumentos:

```bash
Rscript R/analise_estatistica.R "/caminho/spring-petclinic.csv" "hv"
```

3. Escolha o indicador: passe como **segundo argumento** (recomendado) ou edite o
   valor padrão na seção 0 (`indicador <- if (...) args[2] else "hv"`).
   Indicadores: `hv`, `igd_plus`, `ed_media`, `ed_min` (e, opcionalmente, `spacing`).

```bash
Rscript R/analise_estatistica.R "/caminho/spring-petclinic.csv" "igd_plus"
```

## O que o script faz (seções)

0. **Configuração** — caminho do CSV, indicador, `alfa`, `forcar_kruskal`.
1. **Leitura e inspeção** — valida persona/sistema, unicidade de
   `(config, repeticao)`, geração final, e mostra linhas brutas x válidas por
   configuração (deve ser 5).
2. **Descritiva** — resumo por configuração, boxplot e Q-Q plots.
3. **Shapiro-Wilk** por configuração (normalidade).
4. **Levene** (homogeneidade das variâncias).
5. **Teste global** — ANOVA se os dois pressupostos valem; senão Kruskal-Wallis.
6. **Pós-hoc + FDR-BH** — Tukey (ANOVA) ou Dunn (Kruskal), só se o global for
   significativo. Em `p_teste`, o Tukey já vem ajustado; o BH é uma camada extra.
7. **Vargha-Delaney A12** para todos os 28 pares, com direção e magnitude.
8. **Opcional** — bloco comentado para salvar os resultados, se o participante
   quiser.

## Interpretação

- **Shapiro**: `p > 0,05` → normalidade plausível. Com n = 5, o teste tem baixo
  poder; interprete com cautela.
- **Levene**: `p > 0,05` → variâncias homogêneas.
- **Global**: `p > 0,05` → sem diferença e o pós-hoc se encerra (o A12 continua);
  `p ≤ 0,05` → ao menos uma configuração difere (o global não diz qual).
- **Pós-hoc**: significância sobre o **p ajustado (FDR-BH)**. No Tukey, `p_teste`
  já é ajustado; no Dunn, é o p bruto.
- **A12**: `A12 > 0,5` → A tende a superar B; `A12 < 0,5` → B tende a superar A.
  - Direção: **HV** maior melhor; **IGD+ / ED** menor melhor.
  - Magnitude: Desprezível (|A12−0,5| ≤ 0,06), Pequena (≤ 0,14), Média (≤ 0,21),
    Grande (> 0,21).
  - Com n = 5, o A12 é discreto (múltiplos de 0,04) e aproximado.

## Limitações (registrar no texto)

- Com n = 5, Shapiro-Wilk tem baixo poder e Q-Q/histogramas são pouco conclusivos.
- Com 28 comparações e n = 5, espera-se que poucos pares sobrevivam ao FDR-BH.
- O tamanho de efeito não depende do p-valor: destaque efeitos grandes mesmo sem
  p ajustado ≤ 0,05.
