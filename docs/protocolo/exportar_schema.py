import json
import sys
from pathlib import Path

from pydantic import TypeAdapter

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src" / "telemetria"))

from telemetria.modelos import Ack, Comando, Frame, FrameV2  # noqa: E402

if __name__ == "__main__":
    for versao, modelo in ((1, Frame | Comando | Ack), (2, FrameV2)):
        schema = TypeAdapter(modelo).json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["title"] = f"Micromouse — contrato v{versao}"
        Path(__file__).with_name(f"v{versao}.schema.json").write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
