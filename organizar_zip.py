"""Organiza os ZIPs planos em <dst>/persona_*/config_*/<sistema>/*.zip.

Lê a identidade de cada ZIP no próprio `manifest.json` (authoritative):
- persona   <- study.personaId  (ex.: P2-Systematic-Decoupler -> persona_2)
- config    <- study.configLabel se começar com "config_"; senão "config_" +
               study.configId (fallback configLabel), sanitizado
- sistema   <- run.sourceId (fallback run.instance)

O nome da pasta de configuração SEMPRE começa com "config_" para casar com o
glob exigido pelo pipeline (``config_*``). Os ZIPs são COPIADOS (origem preservada).

Uso:
  python3 organizar_zip.py --src /caminho/zips_planos --dst /caminho/dados_organizados
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path


def _read_manifest(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        if "manifest.json" not in zf.namelist():
            raise ValueError("manifest.json ausente")
        with zf.open("manifest.json") as fh:
            return json.load(fh)


def _sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("_") or "unknown"


def _persona_folder(persona_id: str) -> str:
    """P2-Systematic-Decoupler -> persona_2; fallback sanitizado."""
    match = re.match(r"^P(\d+)", persona_id or "")
    if match:
        return f"persona_{match.group(1)}"
    return f"persona_{_sanitize(persona_id)}"


def _config_folder(study: dict) -> str:
    """Nome de pasta que sempre casa com ``config_*``."""
    label = study.get("configLabel")
    if isinstance(label, str) and label.startswith("config_"):
        return _sanitize(label)
    raw = study.get("configId") or label or "unknown"
    return f"config_{_sanitize(str(raw))}"


def organize(src: Path, dst: Path) -> tuple[int, list[str]]:
    """Copia os ZIPs para a estrutura exigida. Retorna ``(copiados, descartes)``."""
    src, dst = Path(src), Path(dst)
    zips = sorted(src.glob("*.zip"))
    if not zips:
        raise SystemExit(f"nenhum .zip em {src}")

    copied = 0
    skipped: list[str] = []
    for zip_path in zips:
        try:
            manifest = _read_manifest(zip_path)
            study = manifest.get("study") or {}
            run = manifest.get("run") or {}

            persona = _persona_folder(study.get("personaId") or "")
            config = _config_folder(study)
            system = _sanitize(run.get("sourceId") or run.get("instance") or "unknown_system")

            target_dir = dst / persona / config / system
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / zip_path.name
            shutil.copy2(zip_path, target)
            copied += 1
            print(f"{zip_path.name} -> {target.relative_to(dst)}")
        except Exception as exc:  # noqa: BLE001 — um ZIP ruim não interrompe os demais
            message = f"{zip_path.name}: {type(exc).__name__}: {exc}"
            skipped.append(message)
            print(f"[descartado] {message}")

    print(f"\n{copied} ZIP(s) copiados para {dst}"
          + (f"; {len(skipped)} descartado(s)" if skipped else ""))
    return copied, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Organiza ZIPs na estrutura exigida pelo pipeline.")
    parser.add_argument("--src", required=True, help="Pasta com os ZIPs planos")
    parser.add_argument("--dst", required=True, help="Raiz de destino (estrutura persona/config/sistema)")
    args = parser.parse_args()
    organize(Path(args.src), Path(args.dst))


if __name__ == "__main__":
    main()
