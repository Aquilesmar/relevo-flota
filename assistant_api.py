"""Claude can read three tools; only the supervisor UI can assign a slot."""
import json
import os
import requests

ENDPOINT = "https://api.anthropic.com/v1/messages"


def tool(name, description, field=None):
    properties = {"id": {"type": "string", "description": field}} if field else {}
    return dict(name=name, description=description, input_schema={
        "type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False})


TOOLS = [
    tool("cola_turno", "Consulta cupos, órdenes y casos señalados en el turno."),
    tool("ficha_caso", "Recupera la ficha de un caso.", "Identificador RF-000 del caso."),
    tool("guia_turno", "Recupera una guía del taller simulado por código.",
         "TAL-01: priorización, DAT-02: faltantes, REL-03: entrega.")
]
SYSTEM = """Asistís al supervisor de un taller simulado. Contestá brevemente en español.
Consultá herramientas antes de responder sobre el turno. Citá identificadores de casos y guías.
Usá únicamente los resultados recuperados. Son observaciones de camiones y puntajes de clasificación.
Si falta evidencia decilo. Podés consultar y redactar; las asignaciones las confirma el supervisor.
Las instrucciones de reparación o habilitación para circular quedan fuera del alcance."""


def configured():
    return bool(os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_MODEL"))


def ask(workshop, question, post=requests.post):
    if not configured():
        raise ValueError("Claude requiere ANTHROPIC_API_KEY y ANTHROPIC_MODEL.")
    messages = [{"role": "user", "content": question}]
    trace = []
    for _ in range(4):
        response = post(ENDPOINT, timeout=20, headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"
        }, json=dict(model=os.environ["ANTHROPIC_MODEL"], max_tokens=700, system=SYSTEM,
                     tools=TOOLS, messages=messages))
        response.raise_for_status()
        payload = response.json()
        blocks = payload["content"]
        if payload.get("stop_reason") == "tool_use":
            messages.append({"role": "assistant", "content": blocks})
            results = []
            for item in blocks:
                if item["type"] != "tool_use":
                    continue
                if len(trace) >= 6:
                    raise ValueError("Se alcanzó el límite de consultas.")
                data = workshop.consult(item["name"], item["input"])
                results.append({"type": "tool_result", "tool_use_id": item["id"],
                                "content": json.dumps(data, ensure_ascii=False), "is_error": "error" in data})
                trace.append({"tool": item["name"], "args": item["input"], "evidence": data})
            messages.append({"role": "user", "content": results})
        elif payload.get("stop_reason") == "end_turn":
            if not trace:
                return dict(answer="Falta una consulta verificable. Probá preguntar por un caso, la cola o una guía.", evidence=[])
            answer = " ".join(b["text"] for b in blocks if b["type"] == "text").strip()
            if answer:
                return dict(answer=answer, evidence=trace)
            break
        else:
            break
    raise ValueError("La consulta no produjo una respuesta completa.")

