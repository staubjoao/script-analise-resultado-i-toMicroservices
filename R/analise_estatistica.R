# =============================================================================
# BASE para a análise estatística dos resultados (HV, IGD+, ED)
# -----------------------------------------------------------------------------
# Este script é um PONTO DE PARTIDA: ele mostra, passo a passo, como aplicar
#   Shapiro-Wilk -> Levene -> ANOVA/Kruskal -> Tukey/Dunn -> FDR-BH -> A12
# e imprime os resultados no console. Ele NÃO gera um relatório pronto.
#
# Premissa: o CSV tem UMA persona e UM sistema (o pipeline gera um CSV por
# sistema), com 8 configurações e n = 5 execuções por configuração.
#
# Como usar:
#   1. Rode `Rscript R/analise_estatistica.R` (ele pergunta o CSV) ou passe o
#      caminho como argumento.
#   2. Escolha o indicador na seção 0 (ex.: `indicador <- "hv"`).
#   3. Rode o script e leia os resultados no console; adapte os passos à vontade.
#
# Uso:
#   Rscript R/analise_estatistica.R
#   Rscript R/analise_estatistica.R <csv> [indicador]
# =============================================================================

# --- Localiza e carrega as funções auxiliares -------------------------------
args_full <- commandArgs(trailingOnly = FALSE)
arquivo_arg <- grep("^--file=", args_full, value = TRUE)
script_dir <- if (length(arquivo_arg) > 0) {
  dirname(normalizePath(sub("^--file=", "", arquivo_arg[1])))
} else {
  "R"
}
source(file.path(script_dir, "funcoes.R"))

# =============================================================================
# 0. CONFIGURAÇÃO — edite aqui
# =============================================================================
args <- commandArgs(trailingOnly = TRUE)
caminho_csv <- if (length(args) >= 1 && nzchar(args[1])) {
  path.expand(trimws(gsub("^[\"']+|[\"']+$", "", args[1])))
} else {
  ler_caminho_csv()
}

# Indicador a analisar: "hv", "igd_plus", "ed_media" ou "ed_min".
indicador <- if (length(args) >= 2 && nzchar(args[2])) args[2] else "hv"

alfa <- 0.05
# Use TRUE para adotar Kruskal-Wallis como escolha conservadora (n = 5).
forcar_kruskal <- FALSE

# =============================================================================
# 1. LEITURA E INSPEÇÃO DOS DADOS
# =============================================================================
if (!file.exists(caminho_csv)) {
  stop(sprintf("CSV não encontrado: %s", caminho_csv))
}
df <- carregar_resultados(caminho_csv)

# O CSV deve ter exatamente uma persona e um sistema.
personas <- unique(df$persona)
sistemas <- unique(df$sistema)
if (length(personas) != 1) {
  stop(sprintf("o CSV deve conter 1 persona; encontradas: %s", paste(personas, collapse = ", ")))
}
if (length(sistemas) != 1) {
  stop(sprintf("o CSV deve conter 1 sistema; encontrados: %s", paste(sistemas, collapse = ", ")))
}
persona <- personas[[1]]
sistema <- sistemas[[1]]

# Uma linha por execução: (config, repeticao) não pode repetir.
if (any(duplicated(df[, c("config", "repeticao")]))) {
  stop("há (config, repeticao) duplicado; o CSV deve ter 1 linha por execução.")
}

# Se houver mais de uma geração, manter a final (maior).
if ("geracao" %in% names(df) && any(!is.na(df$geracao))) {
  geracoes <- sort(unique(df$geracao[!is.na(df$geracao)]))
  if (length(geracoes) > 1) {
    cat(sprintf("[aviso] múltiplas gerações %s; mantendo a maior (final).\n",
                paste(geracoes, collapse = ", ")))
    df <- df[df$geracao == max(geracoes), , drop = FALSE]
  }
}

cat("=============================================================\n")
cat(sprintf("Persona: %s\n", persona))
cat(sprintf("Sistema: %s\n", sistema))
cat(sprintf("Indicador: %s\n\n", indicador))

cat("Primeiras linhas do CSV (colunas de interesse):\n")
cols_head <- intersect(c("config", "repeticao", "geracao", "completo", indicador), names(df))
print(utils::head(df[, cols_head, drop = FALSE], 10))
cat("\nExecuções por configuração:\n")
print(table(df$config))

# Prepara o grupo: filtra completos, n_pontos > 0 e valores ausentes.
preparado <- preparar_grupo(df, sistema, indicador, exigir_n = 5)
d <- preparado$dados

# Quadro de linhas brutas x válidas por configuração (evita exclusão silenciosa).
brutas <- table(df$config)
validas <- table(d$config)
quadro <- data.frame(
  config = names(brutas),
  linhas_brutas = as.integer(brutas),
  linhas_validas = as.integer(validas[names(brutas)]),
  row.names = NULL
)
quadro$linhas_validas[is.na(quadro$linhas_validas)] <- 0L
quadro$excluidas <- quadro$linhas_brutas - quadro$linhas_validas
print(quadro)

sem_linhas <- quadro$config[quadro$linhas_validas == 0]
if (length(sem_linhas) > 0) {
  cat(sprintf("\n[ATENÇÃO] configurações sem linhas válidas: %s\n",
              paste(sem_linhas, collapse = ", ")))
}
if (nrow(d) == 0) {
  stop("nenhuma linha válida após os filtros")
}
if (length(unique(d$config)) < 2) {
  stop("menos de 2 configurações com dados; não há comparação possível")
}
if (any(table(d$config) < 3)) {
  cat("\n[ATENÇÃO] alguma configuração tem n < 3: os testes e o A12 são pouco confiáveis.\n")
}

cat("\nValores válidos por configuração (esperado: 5):\n")
print(table(d$config))

# =============================================================================
# 2. ANÁLISE DESCRITIVA
# =============================================================================
cat("\n--- Resumo do indicador por configuração ---\n")
print(tapply(d$valor, d$config, summary))

if (interactive()) {
  boxplot(valor ~ config, data = d, las = 2,
          main = sprintf("%s — %s — %s", persona, sistema, indicador),
          ylab = indicador, xlab = "")

  # Q-Q plots por configuração (com n = 5 são apenas indicativos).
  niveis <- levels(d$config)
  par(mfrow = c(2, ceiling(length(niveis) / 2)), mar = c(4, 4, 2, 1))
  for (k in niveis) {
    x <- d$valor[d$config == k]
    qqnorm(x, main = paste0("Q-Q: ", k))
    qqline(x, col = "red")
  }
  par(mfrow = c(1, 1))
} else {
  cat("\n[gráficos] Execute no R/RStudio para ver boxplot e Q-Q.\n")
  cat("           Em Rscript, descomente as linhas de plot para salvar um PDF.\n")
}

# =============================================================================
# 3. PRESSUPOSTO DE NORMALIDADE (Shapiro-Wilk por configuração)
# =============================================================================
cat("\n--- Shapiro-Wilk (H0: normalidade; p > 0.05 = plausível) ---\n")
shapiro <- shapiro_por_grupo(d)
print(shapiro)

normalidade_ok <- all(!is.na(shapiro$p) & shapiro$p > alfa)
cat(sprintf("\nNormalidade plausível em todas as configurações? %s\n", normalidade_ok))

# =============================================================================
# 4. PRESSUPOSTO DE HOMOGENEIDADE DAS VARIÂNCIAS (Levene)
# =============================================================================
cat("\n--- Levene (H0: variâncias homogêneas; p > 0.05 = homogêneas) ---\n")
levene <- levene_test(d$valor, d$config)
print(levene)

levene_ok <- !is.na(levene$p) && levene$p > alfa
cat(sprintf("\nVariâncias homogêneas? %s\n", levene_ok))

# =============================================================================
# 5. TESTE GLOBAL
# =============================================================================
if (length(unique(d$valor)) < 2) {
  cat("\n[aviso] indicador constante: teste global indefinido (p = 1); A12 continua.\n")
  usar_anova <- FALSE
  global <- NULL
  p_global <- 1
  significativo <- FALSE
} else {
  usar_anova <- normalidade_ok && levene_ok && !forcar_kruskal
  cat(sprintf("\nDecisão do teste global: %s\n",
              if (usar_anova) "ANOVA de uma via" else "Kruskal-Wallis"))

  global <- teste_global(d, usar_anova)
  print(global)

  p_global <- global$p
  significativo <- !is.na(p_global) && p_global <= alfa
  cat(sprintf("\nDiferença significativa entre configurações? %s (p = %.4g)\n",
              significativo, p_global))
}

# =============================================================================
# 6. PÓS-HOC + CORREÇÃO FDR-BH (somente se o global for significativo)
# =============================================================================
post <- NULL
if (significativo) {
  cat("\n--- Pós-hoc (Tukey após ANOVA; Dunn após Kruskal) + FDR-BH ---\n")
  post <- posthoc(d, usar_anova, alfa)
  print(post)
  cat("\nPares significativos (p ajustado por BH <= alfa):\n")
  print(post[post$significativo, c("comparacao", "p_teste", "p_ajustado")])
} else {
  cat("\nGlobal não significativo: o pós-hoc se encerra (o A12 continua).\n")
}

# =============================================================================
# 7. TAMANHO DE EFEITO — Vargha-Delaney A12 (todos os pares)
# =============================================================================
cat("\n--- Vargha-Delaney A12 (todos os pares; independe do p-valor) ---\n")
cat("Direção: HV maior melhor; IGD+/ED menor melhor (já tratada no cálculo).\n")
efeito <- tamanhos_efeito(d, indicador)
print(efeito)

cat("\nEfeitos grandes (>= 0.71 em favor de A, ou <= 0.29 em favor de B):\n")
print(efeito[efeito$magnitude == "Grande", c("config_A", "config_B", "A12", "direcao")])

# =============================================================================
# 8. (OPCIONAL) SALVAR ALGO
# -----------------------------------------------------------------------------
# O script não gera relatórios automaticamente. Se quiser guardar, descomente:
# dir.create("resultados_R", showWarnings = FALSE)
# write.csv(shapiro, "resultados_R/shapiro.csv", row.names = FALSE)
# write.csv(efeito,  "resultados_R/a12.csv", row.names = FALSE)
# if (!is.null(post)) write.csv(post, "resultados_R/posthoc.csv", row.names = FALSE)
# =============================================================================
