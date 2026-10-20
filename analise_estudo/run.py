"""Ponto de entrada (CLI) do pacote ``analise_estudo``.

Passo a passo do que o script faz:
  1. localiza os ZIPs em ``<root>/persona_*/config_*/<sistema>/*.zip``;
  2. lê ``frontiers.json`` (fronteira final crua) e ``manifest.json`` (identidade);
  3. agrupa por sistema;
  4. normaliza tudo do sistema com limites conjuntos;
  5. monta a fronteira de referência Z* (união não-dominada);
  6. calcula HV / IGD+ / ED / spacing de cada execução;
  7. exporta CSV + JSON em ``--out``.

Uso:
    python -m analise_estudo --root /caminho/dados --out analise_estudo/resultados
    # ou
    python analise_estudo/run.py --root /caminho/dados

Dependências: ``numpy`` e ``scipy`` (>= 1.7, para o Sobol do HV em M >= 4).
Nenhuma importação de ``experiments/``.
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    root = Path(args.root)

    zips = discover_zips(root)
    print(f"ZIPs encontrados: {len(zips)}")

    records = build_records(zips)
    print(f"Execuções válidas: {len(records)}")

    results = run_analysis(records)

    out_dir = Path(args.out)
    export.write_csv(results, out_dir / "indicadores_por_execucao.csv")
    export.write_json(results, out_dir)

    for system, system_result in sorted(results.items()):
        print(f"  {system}: {len(system_result.executions)} execuções, "
              f"|Z*| = {system_result.reference_size}")
    print(f"Resultados exportados em: {out_dir}")


if __name__ == "__main__":
    main()
