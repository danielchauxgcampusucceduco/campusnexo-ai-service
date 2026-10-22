# CampusNexo AI Service

API FastAPI que el backend Java consulta para estimar cuántas personas hay en un espacio. Es parte del proyecto CampusNexo del curso Patrones de Software (backend: `campusnexo-backend`, dashboard: `campusnexo-frontend`).

## Qué hace cada parte, sin exagerar

| Pieza | Qué es | Dónde corre | Lo usa |
|---|---|---|---|
| Conteo de personas con **YOLO** (+ ByteTrack) | Modelo de visión **preentrenado** (Ultralytics, COCO); no se reentrenó para el campus | En el borde, junto a la cámara (`campusnexo-backend/tools/edge`) y, opcionalmente, en `POST /v1/vision/count` | El gemelo digital del backend recibe sus conteos por MQTT |
| **Estimación de ocupación** `POST /v1/occupancy/estimate` | Filtro de Kalman **escalar** con pesos fijos sobre cámara, CO₂ y Wi-Fi. **Heurística no calibrada**, no es un modelo entrenado | Este servicio | El flujo de evaluación del backend (`HttpOccupancyEstimatorAdapter`, con reintento y respaldo local) |
| **Estimación por lotes** `POST /v1/occupancy/estimate/batch` | El mismo filtro, aislado por `space_id`; una petición procesa hasta 250 espacios únicos y conserva el orden de entrada | Este servicio | Integraciones que actualizan varias salas juntas |
| Filtro de Kalman del gemelo | Otra implementación, con varianza por fuente | Dominio Java del backend | El gemelo digital en vivo |
| `confidence_pct` | Estabilidad interna del filtro, calculada de su varianza | — | **No** es probabilidad de acierto; ver `eval/` |

Las demás rutas son utilidades académicas: `POST /v1/thermal/recommendation` (proyección exponencial exacta de un modelo 1R1C), `POST /v1/rooms/assignment` (matching rectangular de coste mínimo para ≤ 18 cursos y ≤ 1.000 salones) y `GET /v1/library/desk-state` (regla de mesa). La asignación minimiza la potencia nominal sin enumerar subconjuntos de salones. Ninguna salida acciona equipos. El modelo térmico valida parámetros finitos y acotados, informa `1R1C_exact_exponential` y requiere calibración local antes de usar sus proyecciones.

La regla de mesas limita cada conteo (`people`, `objects`) a 0–1.000 y el tiempo sin atención a 0–86.400 segundos. Las entradas decimales de sensores y parámetros rechazan booleanos JSON; los conteos y duraciones requieren enteros explícitos. Las peticiones de imagen vacías se rechazan antes de cargar el detector.

La asignación también limita asistencia y capacidad a 1.000, potencia nominal a 1.000 kW y catálogo a 18 cursos/1.000 salones. Estos máximos se publican en `/v1/capabilities` junto con los límites de las demás rutas.

Para asignar salones, una pareja curso-salón solo es elegible cuando la capacidad cubre `attendance × safety_margin`; el coste es la potencia nominal del salón. El algoritmo húngaro rectangular obtiene el óptimo en `O(cursos² × salones)`, devuelve un resultado infactible si no existe matching completo y conserva el orden de entrada para resolver empates de forma determinista.

`GET /v1/capabilities` publica los algoritmos y límites vigentes para que una integración pueda descubrir qué ofrece el servicio. La ruta distingue la visión YOLO opcional y explicita que el porcentaje de confianza no representa probabilidad de acierto.

`GET /health` confirma que el proceso HTTP responde. `GET /ready` comprueba que el registro de ocupación y el contador de visión opcional se inicializaron; solo devuelve `503` si falta un adaptador requerido. La visión puede seguir deshabilitada sin pesos y el servicio continúa listo para sus demás rutas.

Ejemplo de lote:

```json
{
  "measurements": [
    {"space_id": "421-A", "yolo_people": 18, "co2_ppm": 680, "wifi_devices": 16},
    {"space_id": "422-A", "co2_ppm": 910, "wifi_devices": 24}
  ]
}
```

Cada `space_id` debe aparecer una sola vez por petición. Los lotes vacíos, duplicados y mayores al límite
publicado en `limits.occupancy_batch_items` reciben `422`; el estado del filtro sigue siendo independiente
para cada espacio y se reinicia junto al proceso.

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

`Dockerfile` (puerto `PORT`, por defecto 8001; health check en `/ready`). En Render se despliega como Web Service desde este repositorio; su URL va en `AI_SERVICE_URL` del backend.
