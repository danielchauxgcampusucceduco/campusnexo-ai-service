"""Escribe el contrato OpenAPI del servicio para el equipo del backend y para la CI.

    python -m scripts.exportar_openapi --salida openapi.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.api.app_factory import create_app


def contrato() -> dict:
    """El esquema que FastAPI genera de las rutas y los modelos; no carga YOLO ni pide clave."""
    return create_app(api_key="").openapi()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--salida", type=Path, default=Path("openapi.json"))
    args = parser.parse_args(argv)
    args.salida.write_text(json.dumps(contrato(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Contrato escrito en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
