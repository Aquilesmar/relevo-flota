"""Read-only assistant tools and transactional shift assignments."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAPACITY = 3


def bundled(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


class Workshop:
    def __init__(self, database):
        self.database = database
        self.cases = {row["id"]: row for row in bundled("shift.json")}
        self.guides = {row["id"]: row for row in bundled("procedures.json")}
        Path(database).parent.mkdir(exist_ok=True, parents=True)
        with closing(self.connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS assignments (
                case_id TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    def connect(self):
        return sqlite3.connect(self.database, timeout=8)

    def shift(self):
        with closing(self.connect()) as db:
            assigned = [r[0] for r in db.execute("SELECT case_id FROM assignments ORDER BY created_at, case_id")]
        flagged = sorted((r for r in self.cases.values() if r["flagged"]), key=lambda r: -r["score"])
        return dict(total=len(self.cases), capacity=CAPACITY, assigned=assigned,
                    free=CAPACITY-len(assigned), queue=flagged)

    def assign(self, case_id):
        if case_id not in self.cases or not self.cases[case_id]["flagged"]:
            raise ValueError("Elegí un caso de la cola de revisión.")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM assignments WHERE case_id=?", (case_id,)).fetchone():
                return False
            if db.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] >= CAPACITY:
                raise ValueError("Se asignaron todos los cupos del turno.")
            db.execute("INSERT INTO assignments(case_id) VALUES (?)", (case_id,))
            return True

    def consult(self, name, args):
        if name == "cola_turno" and args == {}:
            return self.shift()
        if name == "ficha_caso" and set(args) == {"id"} and isinstance(args["id"], str):
            if args["id"] in self.cases:
                return self.cases[args["id"]]
        if name == "guia_turno" and set(args) == {"id"} and isinstance(args["id"], str):
            if args["id"] in self.guides:
                return self.guides[args["id"]]
        return {"error": "Consulta o identificador desconocido."}

    def handover(self):
        shift = self.shift()
        pending = [c["id"] for c in shift["queue"] if c["id"] not in shift["assigned"]]
        return (f"Parte de taller · turno simulado\n"
                f"Casos evaluados: {shift['total']}. Señalados para revisión: {len(shift['queue'])}.\n"
                f"Revisiones asignadas: {', '.join(shift['assigned']) or 'ninguna'}.\n"
                f"Pendientes por puntaje: {', '.join(pending) or 'ninguno'}.\n"
                f"Cupos disponibles: {shift['free']}. Referencias: TAL-01 y REL-03.")

