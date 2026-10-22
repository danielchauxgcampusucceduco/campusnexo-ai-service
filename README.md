# CampusNexo AI Service

API FastAPI que el backend Java consulta para estimar cuántas personas hay en un espacio. Es parte del proyecto CampusNexo del curso Patrones de Software (backend: `campusnexo-backend`, dashboard: `campusnexo-frontend`).

## Qué hace cada parte, sin exagerar

| Pieza | Qué es | Dónde corre | Lo usa |
|---|---|---|---|
| Conteo de personas con **YOLO** (+ ByteTrack) | Modelo de visión **preentrenado** (Ultralytics, COCO); no se reentrenó para el campus | En el borde, junto a la cámara (`campusnexo-backend/tools/edge`) y, opcionalmente, en `POST /v1/vision/count` | El gemelo digital del backend recibe sus conteos por MQTT |
| **Estimación de ocupación** `POST /v1/occupancy/estimate` | Fusión **sin estado** de cámara, CO₂ por balance de masa (según el área del salón) y Wi-Fi, ponderada por el inverso de la varianza de cada fuente. **Es el mismo modelo y los mismos parámetros que el filtro de Kalman del gemelo** en Java; parámetros ilustrativos, no un modelo entrenado | Este servicio | La evaluación del backend (`HttpOccupancyEstimatorAdapter`, detrás de reintento con espera exponencial, *circuit breaker* y respaldo local) |
| **Estimación por lotes** `POST /v1/occupancy/estimate/batch` | La misma fusión para hasta 250 lecturas de espacios distintos, en el orden de entrada | Este servicio | Integraciones que actualizan varias salas juntas |
| `confidence_pct` | `(1 − σ / capacidad) · 100`: margen de error relativo al tamaño del salón | — | **No** es probabilidad de acierto; ver `eval/` |

### Un solo modelo de ocupación

El backend estima la ocupación en dos lugares: el gemelo digital (filtro de Kalman con memoria, en Java) y la evaluación bajo demanda, que llama a este servicio y, si falla, a un respaldo local en Java. Los tres usan **la misma fusión con los mismos parámetros**, y los dos repositorios prueban el mismo archivo de casos de referencia (`tests/fusion_golden_cases.csv` aquí, `src/test/resources/fusion_golden_cases.csv` en el backend): si alguien cambia un parámetro en un lado y no en el otro, falla una de las dos suites.

El servicio no guarda estado entre peticiones. Un reintento del backend recibe exactamente la misma respuesta (nunca aplica dos veces la misma medición) y cualquier réplica responde igual. `yolo_people` debe ser el conteo **crudo** de la cámara: el backend nunca envía su estimación ya fusionada, porque contaría dos veces la evidencia de CO₂ y Wi-Fi.

### Clave de servicio

Con `AI_API_KEY` definida (obligatoria en producción, mínimo 24 caracteres) todas las rutas excepto `/health` y `/ready` exigen `X-API-Key` con ese valor; el backend la envía desde su propia `AI_API_KEY`. Sin la variable, solo para desarrollo local, el servicio queda abierto.

Las demás rutas son utilidades académicas: `POST /v1/thermal/recommendation` (proyección exponencial exacta de un modelo 1R1C), `POST /v1/rooms/assignment` (matching rectangular de coste mínimo para ≤ 18 cursos y ≤ 1.000 salones) y `GET /v1/library/desk-state` (regla de mesa). La asignación minimiza la potencia nominal sin enumerar subconjuntos de salones. Ninguna salida acciona equipos. El modelo térmico valida parámetros finitos y acotados, informa `1R1C_exact_exponential` y requiere calibración local antes de usar sus proyecciones.

La regla de mesas limita cada conteo (`people`, `objects`) a 0–1.000 y el tiempo sin atención a 0–86.400 segundos. Las entradas decimales de sensores y parámetros rechazan booleanos JSON; los conteos y duraciones requieren enteros explícitos. Las peticiones de imagen vacías se rechazan antes de cargar el detector.

La asignación también limita asistencia y capacidad a 1.000, potencia nominal a 1.000 kW y catálogo a 18 cursos/1.000 salones. Estos máximos se publican en `/v1/capabilities` junto con los límites de las demás rutas.

Para asignar salones, una pareja curso-salón solo es elegible cuando la capacidad cubre `attendance × safety_margin`; el coste es la potencia nominal del salón. El algoritmo húngaro rectangular obtiene el óptimo en `O(cursos² × salones)`, devuelve un resultado infactible si no existe matching completo y conserva el orden de entrada para resolver empates de forma determinista.

`GET /v1/capabilities` publica los algoritmos y límites vigentes para que una integración pueda descubrir qué ofrece el servicio. La ruta distingue la visión YOLO opcional y explicita que el porcentaje de confianza no representa probabilidad de acierto.

`GET /health` confirma que el proceso HTTP responde. `GET /ready` comprueba que el contador de visión opcional se inicializó; solo devuelve `503` si falta un adaptador requerido. La visión puede seguir deshabilitada sin pesos y el servicio continúa listo para sus demás rutas.

Ejemplo de lote:

```json
{
  "measurements": [
    {"space_id": "421-A", "yolo_people": 18, "co2_ppm": 680, "wifi_devices": 16, "area_sqm": 48, "capacity": 36},
    {"space_id": "422-A", "co2_ppm": 910, "wifi_devices": 24, "area_sqm": 48, "capacity": 36}
  ]
}
```

Cada `space_id` debe aparecer una sola vez por petición. Los lotes vacíos, duplicados y mayores al límite
publicado en `limits.occupancy_batch_items` reciben `422`. Cada respuesta incluye `sigma_people` y el peso
que recibió cada fuente (`sources`), para que se pueda explicar el número.

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

`Dockerfile` (puerto `PORT`, por defecto 8001; health check en `/ready`). En Render se despliega como Web Service desde este repositorio; su URL va en `AI_SERVICE_URL` del backend y la misma `AI_API_KEY` se define en los dos servicios (el Blueprint del backend la genera una vez y la comparte).
