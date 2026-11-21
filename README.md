# Relevo · Mesa de taller para flotas

**Hay cinco casos señalados y tres cupos de revisión. ¿Cuáles atenderías primero y qué le dejarías al siguiente turno?** Relevo combina un clasificador de fallas, una mesa de trabajo y un asistente con acceso de lectura a las fichas del turno. Cada asignación requiere la decisión del supervisor.

**[Descargar la demo interactiva](https://github.com/Aquilesmar/relevo-flota/raw/refs/heads/main/docs/index.html)** · Abrí el HTML en tu navegador. Asigná un cupo a RF-043, consultá la guía DAT-02 y generá el parte. Funciona sin instalar Python ni ingresar claves. La demo usa puntajes calculados por el modelo. Las asignaciones se reinician al recargar.

## Resultado medido

En la prueba oficial de **16.000 casos**, ordenar por puntaje y revisar los primeros **800 (5 %)** concentra **361 de las 375 fallas APS (96,3 %)**. Quedan 14 fuera de esos cupos. El conjunto contiene registros de camiones pesados Scania. Los identificadores, los procedimientos de entrega y los cupos del taller son ficticios.

| Política evaluada | Revisiones | Fallas omitidas | Falsas alarmas | Costo del desafío |
|---|---:|---:|---:|---:|
| Revisar todos los casos | 16.000 | 0 | 15.625 | 156.250 |
| Omitir todas las revisiones | 0 | 375 | 0 | 187.500 |
| Revisar al superar el umbral elegido en validación | 663 | 20 | 308 | 13.080 |

El criterio del desafío asigna 10 unidades a una falsa alarma y 500 a una falla omitida. La tabla usa ese criterio; el resultado de 800 cupos responde a una pregunta distinta de capacidad. Las unidades de costo son las del benchmark. [Métricas reproducibles](data/evaluation.json) · [Scania CV AB, APS Failure at Scania Trucks, UCI, 2016](https://doi.org/10.24432/C51S51)

## Cómo funciona

1. **Machine learning.** Un clasificador de gradient boosting usa 170 canales anónimos y admite lecturas faltantes. De los 60.000 registros oficiales de desarrollo, 48.000 se destinan al ajuste y 12.000 a elegir el umbral por costo. La prueba se usa después de fijar el modelo y el umbral. El puntaje sirve para ordenar casos. Las etiquetas distinguen falla del componente APS y falla en otros componentes. Los datos carecen de una fecha de falla futura.
2. **Operaciones.** El turno usa las primeras 160 observaciones de prueba, en el orden del archivo, con identificadores de demo y sin etiquetas visibles. Flask expone fichas, cola y parte por API. SQLite registra las revisiones y respeta el límite aunque dos supervisores intenten tomar el último cupo al mismo tiempo.
3. **Asistente.** Con Claude habilitado, preguntá *«¿Qué casos quedan pendientes y qué guía explica cómo interpretar lecturas faltantes?»*. El modelo puede consultar la cola, una ficha y las guías. La interfaz muestra las consultas y sus resultados junto al texto generado. Solo la acción **Asignar cupo** modifica el turno. Sin credenciales siguen disponibles las guías y la generación del parte mediante plantilla.

## Ejecutar

Desde la raíz del repositorio, con Python 3.12:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Abrí `http://127.0.0.1:5050`. Para activar las preguntas abiertas, definí `ANTHROPIC_API_KEY` y `ANTHROPIC_MODEL` en la misma terminal antes de iniciar la aplicación. Usá un identificador de modelo habilitado en tu cuenta. Las consultas abiertas consumen la API de Anthropic. [Referencia de Messages](https://platform.claude.com/docs/en/api/messages/create)

### Reproducir el modelo y las pruebas

```bash
python -m pip install -r requirements-ml.txt
python -m ml.train
python -m unittest discover -s tests -v
python preview.py
```

El entrenamiento descarga el ZIP oficial a `.cache/aps.zip`, comprueba su SHA-256, entrena el estimador y regenera los puntajes y las métricas. También acepta `--archive RUTA`. La aplicación arranca con los resultados incluidos. La prueba del asistente usa respuestas simuladas del proveedor para comprobar el intercambio de herramientas. La calidad de las respuestas abiertas requiere evaluación con un modelo conectado.

| Ubicación | Contenido |
|---|---|
| [ml/train.py](ml/train.py) | Datos, particiones, ajuste, umbral y evaluación |
| [workshop.py](workshop.py) | Cola, herramientas y transacción de asignación |
| [assistant_api.py](assistant_api.py) | Cliente de Claude y trazabilidad de consultas |
| [app.py](app.py), [templates](templates), [static](static) | API HTTP e interfaz |
| [data](data), [docs/index.html](docs/index.html), [tests](tests) | Resultados, demo portátil y pruebas |
| `.cache/`, `instance/` | Datos originales, modelo entrenado y base local del turno, excluidos de Git |

**Límite de aplicación.** El experimento evalúa clasificación sobre datos de camiones. Para estimar utilidad en una operadora de colectivos harían falta registros de taller locales, validación por vehículo y por período y una prueba con supervisores. El sistema registra prioridades de revisión. La aptitud de circulación corresponde al proceso técnico de la operadora.

