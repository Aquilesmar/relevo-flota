const byId = (id) => document.getElementById(id);
function message(value) { byId("status").textContent = value; }

async function post(path, body) {
  const response = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "No se pudo completar la operación.");
  return data;
}

document.querySelectorAll(".assign").forEach((button) => button.addEventListener("click", async () => {
  button.disabled = true;
  try {
    await post("/api/ordenes", {id:button.dataset.id});
    location.reload();
  } catch (error) { button.disabled = false; message(error.message); }
}));

function showResult(title, answer, evidence) {
  byId("result").hidden = false;
  byId("result-title").textContent = title;
  byId("answer").textContent = answer;
  byId("trace").hidden = !evidence?.length;
  byId("download").hidden = title !== "Parte de turno";
  byId("evidence").textContent = evidence ? JSON.stringify(evidence, null, 2) : "";
  byId("result").scrollIntoView({block:"nearest"});
}
byId("report").addEventListener("click", async () => {
  try {
    const result = await fetch("/api/parte");
    if (!result.ok) throw new Error("No se pudo obtener el parte.");
    showResult("Parte de turno", await result.text());
  } catch (error) { message(error.message); }
});
byId("ask")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.target.querySelector("button");
  button.disabled = true; message("Consultando fuentes del turno…");
  try {
    const result = await post("/api/asistente", {pregunta:byId("question").value});
    showResult("Respuesta de Claude", result.answer, result.evidence); message("");
  } catch (error) { message(error.message); }
  finally { button.disabled = false; }
});
