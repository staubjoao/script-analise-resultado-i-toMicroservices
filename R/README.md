# Análise estatística em R (HV, IGD+, ED)

Scripts para avaliar os resultados exportados pelo pipeline Python, seguindo o
fluxo: **pressupostos → teste global → pós-hoc + FDR-BH → tamanho de efeito**.

## Premissa: 1 CSV = 1 persona × 1 sistema

O pipeline Python gera **um CSV por sistema** (em `por_sistema/`). Cada grupo
analisa **uma persona**, então cada arquivo corresponde a **uma persona e um
sistema**.

- **Unidade de análise:** **indicador** (`hv`, `igd_plus`, `ed_media`, `ed_min`).
- O sistema já está fixado pelo CSV.
- Em cada indicador há **8 configurações**, com **n = 5 execuções independentes**
  cada.

O script valida que o CSV tem **exatamente uma persona e um sistema**; se não
tiver, interrompe com mensagem clara.

## Requisitos

- R >= 4.x
- **Apenas base R** (sem pacotes externos). Levene e Dunn estão implementados no
  próprio script.

## Entrada

O CSV por sistema gerado por `python -m analise_estudo`:

```
analise_estudo/resultados/
  por_sistema/
    spring-petclinic.csv
    jpetstore.csv
    spring-petclinic.json
    jpetstore.json
```

Colunas:

`persona, participante, config, sistema, repeticao, geracao, completo, n_pontos,
n_duplicados, hv, igd_plus, ed_media, ed_min, spacing, source_zip`

O script:

- normaliza `completo` (o Python grava `True`/`False` como texto);
- usa apenas execuções `completo = TRUE` e `n_pontos > 0`;
- descarta valores ausentes (`NA`) do indicador;
- avisa quando alguma configuração não tem exatamente `n = 5`.

## Passo a passo para rodar a partir do CSV

1. **Gere os CSVs com o pipeline Python** (ou receba os arquivos):

```bash
python -m analise_estudo --root /caminho/dados --out analise_estudo/resultados
```

Isso produz um CSV por sistema em `analise_estudo/resultados/por_sistema/`.

2. **Tenha o CSV do sistema** que será analisado. Se vier pelo Drive, baixe-o
   para uma pasta local (ex.: `Downloads/spring-petclinic.csv`).

3. **Confirme o R instalado:**

```bash
Rscript --version
```

4. **Rode o script** (da raiz do repositório). Sem argumentos, ele **pergunta o
   caminho do CSV**:

```bash
Rscript R/analise_estatistica.R
```

Quando solicitado, **cole o caminho** do arquivo (ou arraste o arquivo para o
terminal). O script aceita caminhos com aspas, espaços e `~` e, se o caminho não
existir, pergunta novamente (até 3 vezes). A saída vai para `resultados_R/`.

Também é possível informar o caminho direto como argumento:

```bash
# <csv> [saida] [indicador]
Rscript R/analise_estatistica.R "/caminho/spring-petclinic.csv" "resultados_R"

# só alguns indicadores
Rscript R/analise_estatistica.R "/caminho/spring-petclinic.csv" "resultados_R" "hv,igd_plus"
```

5. **Veja o resumo consolidado**:

```bash
column -s, -t resultados_R/resumo_estatistico.csv
```

6. **Abra as saídas por indicador** em `resultados_R/<sistema>/<indicador>/`:
   - `pressuposto_shapiro.csv`;
   - `pressuposto_levene.csv`;
   - `teste_global.csv`;
   - `posthoc_fdr_bh.csv` (só se o global for significativo);
   - `tamanho_efeito_a12.csv`;
   - `graficos.pdf` (boxplot + Q-Q + histogramas).

7. **Interprete** na ordem:
   - Pressupostos: normalidade (Shapiro) e variâncias (Levene);
   - Teste global: se `p > 0,05`, para; se `p ≤ 0,05`, veja o pós-hoc;
   - Pós-hoc: significância sobre o **p ajustado (FDR-BH)**, não o bruto;
   - A12: magnitude e direção, para **todos** os pares.

## Saída

```
resultados_R/
  resumo_estatistico.csv                    # 1 linha por indicador
  <sistema>/<indicador>/
    pressuposto_shapiro.csv
    pressuposto_levene.csv
    teste_global.csv
    posthoc_fdr_bh.csv                      # só se o global for significativo
    tamanho_efeito_a12.csv                  # todos os 28 pares
    graficos.pdf                            # boxplot + Q-Q + histogramas
```

## Fluxo estatístico

1. **Shapiro-Wilk** por configuração (H0: normalidade). `p > 0,05` → normalidade
   plausível.
2. **Levene** (centrado na mediana) para homogeneidade das variâncias.
3. **Teste global**:
   - ambos os pressupostos atendidos → **ANOVA de uma via**;
   - caso contrário (ou `forcar_kruskal = TRUE`) → **Kruskal-Wallis**;
   - `p > 0,05` → sem diferença significativa; **não** há pós-hoc.
4. **Pós-hoc** (se global significativo):
   - após ANOVA → **Tukey HSD**;
   - após Kruskal → **Dunn** (com correção de empates);
   - p-valores corrigidos por **FDR-BH** (`p.adjust(..., "BH")`); significância
     sobre o p ajustado (`≤ 0,05`).
5. **Vargha-Delaney A12** para **todos** os 28 pares (independente do p):
   `A12 = P(A melhor que B) + 0,5 · P(A = B)`, respeitando a direção:
   - **HV**: maior é melhor (A melhor = A > B);
   - **IGD+ / ED**: menor é melhor (A melhor = A < B; o script inverte o sinal
     internamente).
   - Magnitude: Desprezível (|A12−0,5| ≤ 0,06), Pequena (≤ 0,14), Média (≤ 0,21),
     Grande (> 0,21).

Parâmetros no topo do script: `forcar_kruskal` (use `TRUE` para adotar
Kruskal-Wallis como escolha conservadora) e `exigir_n` (padrão 5).

## Observações sobre o formato exportado

- **`completo`** sai como `True`/`False` (booleano do Python). O R normaliza isso,
  mas para interoperabilidade seria melhor exportar `1/0` (ou `TRUE/FALSE`).
  Se quiser, ajustamos o `export.py`.
- **Valores ausentes**: IGD+/ED podem vir vazios quando não há fronteira válida;
  o R lê como `NA` e remove a linha. Se sobrar menos de 5 execuções em alguma
  configuração, o script emite aviso (n < 5 enfraquece ainda mais os testes).
- **`config`** usa o `configId` real. Se a análise precisar ser cega, adicione
  `configLabel` ao CSV.
- **ED**: o CSV traz `ed_media` e `ed_min`; por padrão o script roda ambos.

## Limitações (registrar no texto)

- Com n = 5, Shapiro-Wilk tem baixo poder e Q-Q/histogramas são pouco conclusivos.
- Com 28 comparações e n = 5, espera-se que poucos pares sobrevivam ao FDR-BH.
- O A12 assume valores discretos (múltiplos de 0,04) e é uma estimativa aproximada.
- O tamanho de efeito não depende do p-valor: destaque efeitos grandes mesmo sem
  p ajustado ≤ 0,05.
