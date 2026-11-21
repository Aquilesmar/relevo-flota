// Standalone demo: no services, credentials, or network calls.
const shift = JSON.parse(document.getElementById("shift").textContent);
const assignments = new Set();
const buttons = [...document.querySelectorAll(".assign")];
let downloadUrl;

function report() {
  const pending = shift.queue.map(row => row.id).filter(id => !assignments.has(id));
  const text = [
    "Parte de taller · turno simulado",
    `Casos evaluados: ${shift.total}. Señalados para revisión: ${shift.queue.length}.`,
    `Revisiones asignadas: ${[...assignments].join(", ") || "ninguna"}.`,
    `Pendientes por puntaje: ${pending.join(", ") || "ninguno"}.`,
    `Cupos disponibles: ${shift.capacity - assignments.size}. Referencias: TAL-01 y REL-03.`
  ].join("\n");
  document.getElementById("answer").textContent = text;
  document.getElementById("result").hidden = false;
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = URL.createObjectURL(new Blob([text], {type:"text/plain;charset=utf-8"}));
  document.getElementById("download").href = downloadUrl;
}

buttons.forEach(button => button.addEventListener("click", () => {
  if (assignments.size >= shift.capacity || assignments.has(button.dataset.id)) return;
  assignments.add(button.dataset.id);
  button.textContent = "Asignada";
  buttons.forEach(item => {item.disabled = assignments.has(item.dataset.id) || assignments.size >= shift.capacity;});
  document.querySelector(".accent").firstChild.textContent = String(shift.capacity - assignments.size) + " ";
  if (!document.getElementById("result").hidden) report();
}));
document.getElementById("report").addEventListener("click", () => {
  report();
  document.getElementById("result").scrollIntoView({block:"nearest"});
});

