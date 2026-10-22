# CampusNexo AI Service

API FastAPI que el backend Java consulta para estimar cuántas personas hay en un espacio. Es parte del proyecto CampusNexo del curso Patrones de Software (backend: `campusnexo-backend`, dashboard: `campusnexo-frontend`).

## Qué hace cada parte, sin exagerar

| Pieza | Qué es | Dónde corre | Lo usa |
|---|---|---|---|
| Conteo de personas con **YOLO** (+ ByteTrack) | Modelo de visión **preentrenado** (Ultralytics, COCO); no se reentrenó para el campus | En el borde, junto a la cámara (`campusnexo-backend/tools/edge`) y, opcionalmente, en `POST /v1/vision/count` | El gemelo digital del backend recibe sus conteos por MQTT |
| **Estimación de ocupación** `POST /v1/occupancy/estimate` | Filtro de Kalman **escalar** con pesos fijos sobre cámara, CO₂ y Wi-Fi. **Heurística no calibrada**, no es un modelo entrenado | Este servicio | El flujo de evaluación del backend (`HttpOccupancyEstimatorAdapter`, con reintento y respaldo local) |
| Filtro de Kalman del gemelo | Otra implementación, con varianza por fuente | Dominio Java del backend | El gemelo digital en vivo |
| `confidence_pct` | Estabilidad interna del filtro, calculada de su varianza | — | **No** es probabilidad de acierto; ver `eval/` |

Las demás rutas son utilidades académicas: `POST /v1/thermal/recommendation` (proyección exponencial exacta de un modelo 1R1C), `POST /v1/rooms/assignment` (asignación exacta para ≤ 18 cursos) y `GET /v1/library/desk-state` (regla de mesa). Ninguna salida acciona equipos. El modelo térmico valida parámetros finitos y acotados, informa `1R1C_exact_exponential` y requiere calibración local antes de usar sus proyecciones.

`GET /v1/capabilities` publica los algoritmos y límites vigentes para que una integración pueda descubrir qué ofrece el servicio. La ruta distingue la visión YOLO opcional y explicita que el porcentaje de confianza no representa probabilidad de acierto.

## Ejecutar

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"          # versiones fijadas en pyproject.toml
uvicorn app.main:app --reload --port 8001     # documentación en /docs
pytest -q
```

Visión (opcional): `pip install -e ".[vision]"`, o la imagen con `docker build --build-arg WITH_VISION=true .`. Sin el extra, `/v1/vision/count` responde `503` a propósito: nunca un conteo inventado. Las imágenes se leen en memoria y se descartan; la respuesta solo trae el conteo.

## Medir antes de afirmar

`eval/evaluate.py` calcula MAE, RMSE, sesgo y una tabla de calibración de `confidence_pct` a partir de un CSV con conteos reales (`eval/plantilla_conteos.csv`, protocolo en `eval/README.md`). El repositorio **no** incluye mediciones: no hay que presentar precisión ni confianza como validadas hasta correrlo con datos del campus.

## Despliegue

`Dockerfile` (puerto `PORT`, por defecto 8001; health check en `/health`). En Render se despliega como Web Service desde este repositorio; su URL va en `AI_SERVICE_URL` del backend.
