# =============================================================================
# Funções auxiliares da análise estatística dos resultados
# -----------------------------------------------------------------------------
# Só usa base R (sem pacotes externos):
#   - Shapiro-Wilk por configuração
#   - Levene (centrado na mediana) para homogeneidade de variâncias
#   - ANOVA de uma via + Tukey HSD
#   - Kruskal-Wallis + Dunn (com correção de empates)
#   - FDR-BH (Benjamini-Hochberg)
#   - Vargha-Delaney A12 (com direção do indicador e magnitude)
# =============================================================================

# --- Leitura -----------------------------------------------------------------

#' Pergunta o caminho do CSV ao usuário (quando não vier por argumento).
#'
#' Aceita caminho colado ou arrastado para o terminal, removendo aspas e o
#' escape de espaços. Expande `~` e valida a existência.
ler_caminho_csv <- function(tentativas = 3) {
  for (i in seq_len(tentativas)) {
    if (interactive()) {
      resposta <- readline("Informe o caminho do CSV de resultados: ")
    } else {
      cat("Informe o caminho do CSV de resultados: ")
      flush.console()
      linha <- readLines(file("stdin"), n = 1, warn = FALSE)
      resposta <- if (length(linha) > 0) linha[[1]] else ""
    }
    caminho <- trimws(resposta)
    caminho <- gsub("^[\"']+|[\"']+$", "", caminho)  # remove aspas
    caminho <- gsub("\\\\ ", " ", caminho)           # remove escape de espaço
    caminho <- path.expand(caminho)
    if (nzchar(caminho) && file.exists(caminho)) {
      return(normalizePath(caminho, winslash = "/", mustWork = TRUE))
    }
    cat("Arquivo não encontrado. Verifique o caminho e tente novamente.\n")
  }
  stop("Não foi possível localizar o CSV informado.")
}

#' Lê o CSV exportado pelo pipeline Python.
#'
#' O pipeline grava o booleano `completo` como "True"/"False" (Python). O R lê
#' isso como texto, então normalizamos para lógico aqui.
carregar_resultados <- function(caminho_csv) {
  df <- read.csv(caminho_csv, stringsAsFactors = FALSE, check.names = FALSE)
  if ("completo" %in% names(df)) {
    df$completo <- toupper(as.character(df$completo)) %in% c("TRUE", "1", "SIM")
  }
  df
}

#' Prepara um grupo (sistema) para um indicador.
#'
#' Assume que `df` contém apenas UMA persona (validado no script principal).
#' Filtra execuções completas, com fronteira não vazia (n_pontos > 0) e valor
#' numérico. Retorna a lista `dados` (com colunas `config` e `valor`) e a
#' contagem por configuração.
preparar_grupo <- function(df, sistema, indicador, exigir_n = 5) {
  d <- df[df$sistema == sistema, , drop = FALSE]
  if (nrow(d) == 0) {
    stop(sprintf("sem dados para sistema=%s", sistema))
  }
  if ("completo" %in% names(d)) {
    d <- d[d$completo %in% TRUE, , drop = FALSE]
  }
  if ("n_pontos" %in% names(d)) {
    d <- d[!is.na(d$n_pontos) & d$n_pontos > 0, , drop = FALSE]
  }
  d$valor <- suppressWarnings(as.numeric(d[[indicador]]))
  d <- d[!is.na(d$valor), , drop = FALSE]
  if (nrow(d) == 0) {
    stop(sprintf("sem valores válidos para indicador=%s", indicador))
  }

  d$config <- factor(d$config)
  tab <- table(d$config)
  if (length(tab) < 2) {
    stop("menos de 2 configurações com dados para comparar")
  }
  if (any(tab < 3)) {
    warning("alguma configuração tem n < 3: os testes e o A12 são pouco confiáveis")
  }
  if (any(tab != exigir_n)) {
    warning(sprintf(
      "n por configuração diferente de %d: %s",
      exigir_n, paste(names(tab), as.integer(tab), sep = "=", collapse = ", ")
    ))
  }
  list(dados = d, n_por_config = tab)
}

# --- Pressupostos ------------------------------------------------------------

#' Shapiro-Wilk por grupo. Retorna NA quando não é possível aplicar.
shapiro_por_grupo <- function(d) {
  do.call(rbind, lapply(levels(d$config), function(k) {
    x <- d$valor[d$config == k]
    if (length(x) < 3 || length(unique(x)) < 2) {
      return(data.frame(config = k, n = length(x), W = NA_real_, p = NA_real_))
    }
    teste <- tryCatch(shapiro.test(x), error = function(e) NULL)
    if (is.null(teste)) {
      return(data.frame(config = k, n = length(x), W = NA_real_, p = NA_real_))
    }
    data.frame(config = k, n = length(x),
               W = as.numeric(teste$statistic), p = as.numeric(teste$p.value))
  }))
}

#' Levene centrado na mediana (base R, sem `car`).
#'
#' É o ANOVA sobre |x - mediana_do_grupo|. p > 0.05 => variâncias homogêneas.
levene_test <- function(valor, grupo, center = median) {
  grupo <- factor(grupo)
  desvio <- abs(valor - ave(valor, grupo, FUN = center))
  s <- summary(aov(desvio ~ grupo))[[1]]
  list(
    F = as.numeric(s[["F value"]][1]),
    df1 = as.numeric(s[["Df"]][1]),
    df2 = as.numeric(s[["Df"]][2]),
    p = as.numeric(s[["Pr(>F)"]][1])
  )
}

#' Roda todos os pressupostos e decide o teste global.
#' (Não é usada pela base guiada; mantida como utilitário.)
verificar_pressupostos <- function(d, alfa = 0.05, forcar_kruskal = FALSE) {
  shapiro <- shapiro_por_grupo(d)
  levene <- levene_test(d$valor, d$config)

  normalidade_ok <- all(!is.na(shapiro$p) & shapiro$p > alfa)
  levene_ok <- !is.na(levene$p) && levene$p > alfa
  usar_anova <- normalidade_ok && levene_ok && !forcar_kruskal

  list(
    shapiro = shapiro,
    levene = levene,
    normalidade_ok = normalidade_ok,
    levene_ok = levene_ok,
    usar_anova = usar_anova
  )
}

# --- Teste global ------------------------------------------------------------

teste_global <- function(d, usar_anova) {
  if (usar_anova) {
    s <- summary(aov(valor ~ config, data = d))[[1]]
    return(list(
      teste = "ANOVA",
      estatistica = as.numeric(s[["F value"]][1]),
      gl = as.numeric(s[["Df"]][1]),
      p = as.numeric(s[["Pr(>F)"]][1])
    ))
  }
  kt <- kruskal.test(valor ~ config, data = d)
  list(
    teste = "Kruskal-Wallis",
    estatistica = as.numeric(kt$statistic),
    gl = as.numeric(kt$parameter),
    p = as.numeric(kt$p.value)
  )
}

# --- Pós-hoc -----------------------------------------------------------------

#' Dunn (1964) com correção de empates, implementado em base R.
#'
#' z_ij = (Rbar_i - Rbar_j) / sqrt( sigma2 * (1/n_i + 1/n_j) )
#' sigma2 = N(N+1)/12 - T/(12(N-1)),  T = sum(t^3 - t) sobre os grupos de empate.
dunn_pairwise <- function(valor, grupo) {
  grupo <- factor(grupo)
  N <- length(valor)
  ranks <- rank(valor)
  empates <- table(valor)
  Tt <- sum(empates^3 - empates)
  sigma2 <- N * (N + 1) / 12 - Tt / (12 * (N - 1))

  niveis <- levels(grupo)
  k <- length(niveis)
  linhas <- list()
  for (i in seq_len(k - 1)) {
    for (j in (i + 1):k) {
      a <- niveis[i]
      b <- niveis[j]
      ra <- ranks[grupo == a]
      rb <- ranks[grupo == b]
      na <- length(ra)
      nb <- length(rb)
      denom <- sqrt(sigma2 * (1 / na + 1 / nb))
      z <- if (denom > 0) (mean(ra) - mean(rb)) / denom else NA_real_
      p <- if (is.na(z)) NA_real_ else 2 * pnorm(-abs(z))
      linhas[[length(linhas) + 1]] <- data.frame(
        comparacao = paste(a, "-", b), z = z, p_teste = p
      )
    }
  }
  do.call(rbind, linhas)
}

#' Pós-hoc com FDR-BH. Após ANOVA usa Tukey HSD (p já ajustado pelo Tukey);
#' após Kruskal usa Dunn (p bruto). Em ambos, aplica-se BH como camada extra.
posthoc <- function(d, usar_anova, alfa = 0.05) {
  if (usar_anova) {
    tuk <- TukeyHSD(aov(valor ~ config, data = d))$config
    post <- data.frame(
      comparacao = rownames(tuk),
      diferenca = tuk[, "diff"],
      p_teste = tuk[, "p adj"],
      stringsAsFactors = FALSE
    )
  } else {
    post <- dunn_pairwise(d$valor, d$config)
  }
  post$p_ajustado <- p.adjust(post$p_teste, method = "BH")
  post$significativo <- !is.na(post$p_ajustado) & post$p_ajustado <= alfa
  post
}

# --- Vargha-Delaney A12 ------------------------------------------------------

#' A12 = P(A melhor que B) + 0.5 * P(A igual a B).
#'
#' `a` e `b` devem estar ORIENTADOS para "maior é melhor" (ver `orientar`).
a12 <- function(a, b) {
  if (length(a) == 0 || length(b) == 0) return(NA_real_)
  cmp <- outer(a, b, "-")
  (sum(cmp > 0) + 0.5 * sum(cmp == 0)) / (length(a) * length(b))
}

#' Orienta o indicador para "maior é melhor".
#' HV: maior é melhor. IGD+ e ED: menor é melhor (inverte o sinal).
orientar <- function(x, indicador) {
  if (identical(indicador, "hv")) x else -x
}

#' Magnitude do A12 (tabela do enunciado), simétrica em torno de 0.5.
classificar_a12 <- function(valor) {
  d <- abs(valor - 0.5)
  if (is.na(d)) return(NA_character_)
  if (d <= 0.06) "Desprezível"
  else if (d <= 0.14) "Pequena"
  else if (d <= 0.21) "Média"
  else "Grande"
}

#' Calcula A12 para TODOS os pares de configurações (não só os significativos).
tamanhos_efeito <- function(d, indicador) {
  niveis <- levels(d$config)
  pares <- combn(niveis, 2, simplify = FALSE)
  do.call(rbind, lapply(pares, function(par) {
    a <- orientar(d$valor[d$config == par[1]], indicador)
    b <- orientar(d$valor[d$config == par[2]], indicador)
    valor <- a12(a, b)
    data.frame(
      config_A = par[1],
      config_B = par[2],
      A12 = valor,
      direcao = if (is.na(valor)) NA_character_
                else if (valor > 0.5) "A melhor que B"
                else if (valor < 0.5) "B melhor que A"
                else "Equivalentes",
      magnitude = classificar_a12(valor),
      n_A = length(a),
      n_B = length(b),
      stringsAsFactors = FALSE
    )
  }))
}
