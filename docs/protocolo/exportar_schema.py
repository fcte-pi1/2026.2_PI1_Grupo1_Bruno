"""Regenera o schema v1 a partir dos modelos executáveis, usando o ambiente da telemetria."""

import json
import sys
from pathlib import Path

from pydantic import TypeAdapter

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src" / "telemetria"))

from telemetria.modelos import Ack, Comando, Frame  # noqa: E402

if __name__ == "__main__":
    schema = TypeAdapter(Frame | Comando | Ack).json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Micromouse — contrato v1"
    Path(__file__).with_name("v1.schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
