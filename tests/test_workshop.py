import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from app import create_app
from assistant_api import ask
from workshop import Workshop, bundled


class ShiftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "shift.db"
        self.store = Workshop(self.db)
        self.web = create_app(self.db).test_client()
        self.ids = [r["id"] for r in self.store.shift()["queue"]]

    def test_page_and_sources(self):
        self.assertEqual(self.web.get("/").status_code, 200)
        self.assertIn(self.ids[0], self.web.get("/api/turno").json["queue"][0].values())
        self.assertEqual(self.web.get("/api/casos/RF-inexistente").status_code, 404)
        self.assertEqual(self.web.get("/api/casos/" + self.ids[0]).json["id"], self.ids[0])
        self.assertEqual(self.store.consult("guia_turno", {"id": "DAT-02"})["id"], "DAT-02")

    def test_idempotent_assignment_and_report(self):
        for status in (201, 200):
            self.assertEqual(self.web.post("/api/ordenes", json={"id": self.ids[0]}).status_code, status)
        self.assertIn(self.ids[0], self.web.get("/api/parte").get_data(as_text=True))
        self.assertEqual(Workshop(self.db).shift()["free"], 2)

    def test_capacity_under_competing_requests(self):
        def attempt(identifier):
            try:
                return self.store.assign(identifier)
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=5) as pool:
            self.assertEqual(sum(pool.map(attempt, self.ids)), 3)
        self.assertEqual(self.store.shift()["free"], 0)

    def test_read_only_tools(self):
        self.assertIn("error", self.store.consult("asignar_cupo", {"id": self.ids[0]}))
        self.assertEqual(self.store.shift()["assigned"], [])
        self.assertEqual(self.web.post("/api/ordenes", json={"id": "XX"}).status_code, 409)
        self.assertEqual(self.web.post("/api/ordenes", json=[]).status_code, 400)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "ANTHROPIC_MODEL": ""})
    def test_no_key(self):
        self.assertEqual(self.web.post("/api/asistente", json={"pregunta":"¿Qué queda?"}).status_code, 503)
        self.assertEqual(self.web.get("/api/parte").status_code, 200)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only", "ANTHROPIC_MODEL": "fixture"})
    def test_assistant_contract(self):
        call = dict(type="tool_use", id="t1", name="guia_turno", input={"id": "DAT-02"})
        responses = [dict(stop_reason="tool_use", content=[call]),
                     dict(stop_reason="end_turn", content=[dict(type="text", text="Consultar DAT-02.")])]
        post = Mock(side_effect=[Mock(json=Mock(return_value=r)) for r in responses])
        answer = ask(self.store, "¿Cómo trato faltantes?", post=post)
        self.assertEqual(answer["evidence"][0]["evidence"]["id"], "DAT-02")
        self.assertIn("DAT-02", post.call_args.kwargs["json"]["messages"][-1]["content"][0]["content"])
        self.assertEqual(self.store.shift()["assigned"], [])

    def test_benchmark_artifact(self):
        data = bundled("evaluation.json")
        model = data["model"]
        self.assertEqual(sum(model[k] for k in ("tn", "fp", "fn", "tp")), data["test"])
        self.assertEqual(10*model["fp"] + 500*model["fn"], model["cost"])
        self.assertEqual(model["tp"] + model["fn"], data["positives"])

