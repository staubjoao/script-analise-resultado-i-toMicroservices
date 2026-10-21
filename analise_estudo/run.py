"""Ponto de entrada (CLI) do pacote ``analise_estudo``.

Passo a passo do que o script faz:
  1. localiza os ZIPs em ``<root>/persona_*/config_*/<sistema>/*.zip``;
  2. lê ``frontiers.json`` (fronteira final crua) e ``manifest.json`` (identidade);
  3. agrupa por sistema (ou persona × sistema);
  4. descarta penalizadas, deduplica e normaliza com limites comuns;
  5. monta a fronteira de referência Z* (união não-dominada);
  6. calcula HV / IGD+ / ED / spacing de cada execução;
  7. exporta CSV + JSON em ``--out``.

Uso:
    python -m analise_estudo --root /caminho/dados --out analise_estudo/resultados
    python -m analise_estudo --root ... --zstar loo --normalization embedded
    python -m analise_estudo --root ... --group-by persona

Dependências: ``numpy`` e ``scipy`` (>= 1.7, para o Sobol do HV em M >= 4).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config, export
from .io_loading import build_records, discover_zips
from .pipeline import run_analysis


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Análise externa das fronteiras finais do estudo (HV/IGD+/ED/spacing)."
    )
    parser.add_argument(
        "--root", required=True,
        help="Raiz dos dados: <root>/persona_*/config_*/<sistema>/*.zip",
    )
    parser.add_argument(
        "--out", default=config.DEFAULT_OUT_DIR,
        help=f"Diretório de saída (padrão: {config.DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--normalization", choices=("pooled", "embedded"), default="pooled",
        help="Limites de normalização: 'pooled' (mín/máx das execuções) ou "
             "'embedded' (bounds de referência do frontiers.json).",
    )
    parser.add_argument(
        "--zstar", choices=("full", "loo"), default="full",
        help="Z* para o IGD+: 'full' (união de todas as execuções) ou 'loo' "
             "(leave-one-out: sem a execução avaliada).",
    )
    parser.add_argument(
        "--group-by", choices=("system", "persona"), default="system",
        help="Agrupamento: 'system' ou 'persona' (persona × sistema).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    root = Path(args.root)

    zips = discover_zips(root)
    print(f"ZIPs encontrados: {len(zips)}")

    records, skipped_zips = build_records(zips)
    print(f"Execuções válidas: {len(records)}")
    if skipped_zips:
        print(f"ZIPs descartados: {len(skipped_zips)}")
        for message in skipped_zips:
            print(f"  [descartado] {message}")

    results, skipped_groups = run_analysis(
        records,
        normalization=args.normalization,
        zstar=args.zstar,
        group_by=args.group_by,
    )

    out_dir = Path(args.out)
    export.write_csv(results, out_dir / "indicadores_por_execucao.csv")
    export.write_json(
        results, out_dir,
        skipped=skipped_groups,
        meta={
            "group_by": args.group_by,
            "normalization": args.normalization,
            "zstar": args.zstar,
            "skipped_zips": skipped_zips,
        },
    )

    for key in sorted(results):
        group = results[key]
        incomplete = sum(1 for e in group.executions if not e.record.completo)
        print(f"  {key}: {len(group.executions)} execuções, |Z*| = {group.reference_size}, "
              f"incompletos = {incomplete}")
    for key, reason in sorted(skipped_groups.items()):
        print(f"  [ignorado] {key}: {reason}")
    print(f"Resultados exportados em: {out_dir}")


if __name__ == "__main__":
    main()
