"""Organiza os ZIPs planos em <dst>/persona_*/config_*/<sistema>/*.zip.

Lê a identidade de cada ZIP no próprio `manifest.json` (authoritative):
- persona   <- study.personaId  (ex.: P2-Systematic-Decoupler -> persona_2)
- config    <- study.configLabel (ex.: config_3); fallback study.configId
- sistema   <- run.sourceId (fallback run.instance)

Uso:
  python3 organizar_zip.py \
    --src /home/.../results/session_exports \
    --dst /home/.../results/dados_analise
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
        with zf.open("manifest.json") as fh:
            return json.load(fh)


def _persona_folder(persona_id: str) -> str:
    """P2-Systematic-Decoupler -> persona_2; fallback sanitizado."""
    match = re.match(r"^P(\d+)", persona_id or "")
    if match:
        return f"persona_{match.group(1)}"
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", persona_id or "unknown")
    return f"persona_{safe}"


def organize(src: Path, dst: Path) -> int:
    src, dst = Path(src), Path(dst)
    zips = sorted(src.glob("*.zip"))
    if not zips:
        raise SystemExit(f"nenhum .zip em {src}")

    moved = 0
    for zip_path in zips:
        manifest = _read_manifest(zip_path)
        study = manifest.get("study") or {}
        run = manifest.get("run") or {}

        persona = _persona_folder(study.get("personaId") or "")
        config = study.get("configLabel") or study.get("configId") or "config_unknown"
        system = run.get("sourceId") or run.get("instance") or "unknown_system"

        target_dir = dst / persona / config / system
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / zip_path.name
        shutil.copy2(zip_path, target)
        moved += 1
        print(f"{zip_path.name} -> {target.relative_to(dst)}")

    print(f"\n{moved} ZIP(s) organizados em {dst}")
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="Organiza ZIPs na estrutura exigida pelo pipeline.")
    parser.add_argument("--src", required=True, help="Pasta com os ZIPs planos")
    parser.add_argument("--dst", required=True, help="Raiz de destino (estrutura persona/config/sistema)")
    args = parser.parse_args()
    organize(Path(args.src), Path(args.dst))


if __name__ == "__main__":
    main()
