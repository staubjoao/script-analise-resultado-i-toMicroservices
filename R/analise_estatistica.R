# =============================================================================
# Análise estatística dos resultados (HV, IGD+, ED)
# -----------------------------------------------------------------------------
# PREMISSA: cada CSV corresponde a UMA persona e UM sistema (o pipeline gera um
# CSV por sistema). O script valida isso e interrompe se houver mais de uma
# persona ou mais de um sistema no arquivo.
#
# Unidade de análise: INDICADOR, com 8 configurações e n = 5 execuções
# independentes por configuração (o sistema já está fixado pelo CSV).
#
# Fluxo (aplicado separadamente a cada indicador):
#   1. Shapiro-Wilk por configuração (normalidade)
#   2. Levene (homogeneidade das variâncias)
#   3. ANOVA de uma via se ambos os pressupostos valem; senão Kruskal-Wallis
#   4. Se o teste global for significativo (p <= 0.05):
#        - ANOVA -> Tukey HSD
#        - Kruskal-Wallis -> Dunn
#      e os p-valores do pós-hoc são corrigidos por FDR-BH.
#   5. Vargha-Delaney A12 para TODOS os pares (independente do p-valor),
#      respeitando a direção do indicador (HV maior melhor; IGD+/ED menor melhor).
#
# Uso:
#   Rscript R/analise_estatistica.R                      # pergunta o caminho do CSV
#   Rscript R/analise_estatistica.R <csv> [saida] [indicador]
# =============================================================================

# --- Localiza e carrega as funções ------------------------------------------
args_full <- commandArgs(trailingOnly = FALSE)
arquivo_arg <- grep("^--file=", args_full, value = TRUE)
script_dir <- if (length(arquivo_arg) > 0) {
  dirname(normalizePath(sub("^--file=", "", arquivo_arg[1])))
} else {
  "R"
}
source(file.path(script_dir, "funcoes.R"))

# --- Parâmetros --------------------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
caminho_csv <- if (length(args) >= 1 && nzchar(args[1])) {
  path.expand(trimws(gsub("^[\"']+|[\"']+$", "", args[1])))
} else {
  ler_caminho_csv()
}
dir_saida <- if (length(args) >= 2 && nzchar(args[2])) {
  args[2]
} else {
  "resultados_R"
}
filtro_indicador <- if (length(args) >= 3 && nzchar(args[3])) strsplit(args[3], ",")[[1]] else NULL

# Indicadores avaliados por padrão: HV, IGD+ e ED (média e mínima).
indicadores <- if (is.null(filtro_indicador)) {
  c("hv", "igd_plus", "ed_media", "ed_min")
} else {
  filtro_indicador
}

# Kruskal é a escolha conservadora quando a normalidade é duvidosa (n = 5).
# Deixe FALSE para seguir estritamente o critério dos pressupostos.
forcar_kruskal <- FALSE
exigir_n <- 5

sanitizar <- function(x) gsub("[^A-Za-z0-9._-]+", "_", x)

# --- Carrega dados -----------------------------------------------------------
if (!file.exists(caminho_csv)) {
  stop(sprintf("CSV não encontrado: %s", caminho_csv))
}
df <- carregar_resultados(caminho_csv)

# Premissa: um CSV por persona e por sistema.
personas <- unique(df$persona)
if (length(personas) != 1) {
  stop(sprintf(
    "o CSV deve conter exatamente 1 persona; encontradas: %s. Gere/filtre um CSV por persona.",
    paste(personas, collapse = ", ")
  ))
}
persona <- personas[[1]]

sistemas <- unique(df$sistema)
if (length(sistemas) != 1) {
  stop(sprintf(
    "o CSV deve conter exatamente 1 sistema; encontrados: %s. Use os CSVs por sistema gerados pelo pipeline.",
    paste(sistemas, collapse = ", ")
  ))
}
sistema <- sistemas[[1]]

cat(sprintf("CSV: %s\n", caminho_csv))
cat(sprintf("Persona: %s\n", persona))
cat(sprintf("Sistema: %s\n", sistema))
cat(sprintf("Indicadores: %s\n\n", paste(indicadores, collapse = ", ")))

resumo <- list()

# --- Loop principal: indicador ----------------------------------------------
for (indicador in indicadores) {
  rotulo <- sprintf("%s | %s", sistema, indicador)
  cat("====", rotulo, "====\n")

  resultado <- tryCatch({
    preparado <- preparar_grupo(df, sistema, indicador, exigir_n = exigir_n)
    d <- preparado$dados

    pressupostos <- verificar_pressupostos(d, forcar_kruskal = forcar_kruskal)
    global <- teste_global(d, pressupostos$usar_anova)
    significativo <- !is.na(global$p) && global$p <= 0.05

    post <- NULL
    if (significativo) {
      post <- posthoc(d, pressupostos$usar_anova)
    }

    efeito <- tamanhos_efeito(d, indicador)

    # --- Saída por (sistema, indicador) -----------------------------------
    pasta <- file.path(dir_saida, sanitizar(sistema), indicador)
    dir.create(pasta, recursive = TRUE, showWarnings = FALSE)

    write.csv(pressupostos$shapiro,
              file.path(pasta, "pressuposto_shapiro.csv"), row.names = FALSE)
    write.csv(data.frame(
      F = pressupostos$levene$F, gl1 = pressupostos$levene$df1,
      gl2 = pressupostos$levene$df2, p = pressupostos$levene$p,
      homogeneo = pressupostos$levene_ok
    ), file.path(pasta, "pressuposto_levene.csv"), row.names = FALSE)

    write.csv(data.frame(
      teste = global$teste, estatistica = global$estatistica, gl = global$gl,
      p = global$p, significativo = significativo,
      normalidade_ok = pressupostos$normalidade_ok,
      levene_ok = pressupostos$levene_ok
    ), file.path(pasta, "teste_global.csv"), row.names = FALSE)

    if (!is.null(post)) {
      write.csv(post, file.path(pasta, "posthoc_fdr_bh.csv"), row.names = FALSE)
    }
    write.csv(efeito, file.path(pasta, "tamanho_efeito_a12.csv"), row.names = FALSE)

    gerar_graficos(d, indicador, file.path(pasta, "graficos.pdf"), rotulo)

    # --- Linha de resumo ---------------------------------------------------
    n_por_config <- as.integer(preparado$n_por_config)
    data.frame(
      persona = persona,
      sistema = sistema,
      indicador = indicador,
      n_min = min(n_por_config),
      n_max = max(n_por_config),
      normalidade_ok = pressupostos$normalidade_ok,
      shapiro_p_min = suppressWarnings(min(pressupostos$shapiro$p, na.rm = TRUE)),
      levene_p = pressupostos$levene$p,
      levene_ok = pressupostos$levene_ok,
      teste = global$teste,
      p_global = global$p,
      significativo = significativo,
      n_pares_significativos = if (is.null(post)) 0L else sum(post$significativo, na.rm = TRUE),
      n_efeito_grande = sum(efeito$magnitude == "Grande", na.rm = TRUE),
      n_efeito_medio = sum(efeito$magnitude == "Média", na.rm = TRUE),
      stringsAsFactors = FALSE
    )
  }, error = function(e) {
    message(sprintf("  [erro] %s: %s", rotulo, conditionMessage(e)))
    NULL
  })

  if (!is.null(resultado)) {
    resumo[[length(resumo) + 1]] <- resultado
    cat(sprintf("  n=%d..%d | %s p=%.4g | significativo=%s\n",
                resultado$n_min, resultado$n_max, resultado$teste,
                resultado$p_global, resultado$significativo))
  }
}

# --- Resumo consolidado ------------------------------------------------------
if (length(resumo) > 0) {
  resumo_df <- do.call(rbind, resumo)
  write.csv(resumo_df, file.path(dir_saida, "resumo_estatistico.csv"), row.names = FALSE)
  cat(sprintf("\nResumo consolidado: %s\n", file.path(dir_saida, "resumo_estatistico.csv")))
} else {
  cat("\nNenhuma análise concluída.\n")
}
