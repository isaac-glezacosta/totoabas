# Water Quality API - Endpoints

Esta guia resume los endpoints disponibles en la API.

## Informacion general

- Framework: FastAPI
- Titulo de la API: Water Quality API
- URL base en nube (Vultr): http://216.238.81.22:8000
- Documentacion interactiva (FastAPI):
  - Swagger UI: http://216.238.81.22:8000/docs#/
  - ReDoc: http://216.238.81.22:8000/redoc

## Convenciones de datos

- Identificador de pez: `fishId`
- Compatibilidad legacy: algunos registros pueden traer `robotId`; el servicio lo normaliza a `fishId`.
- Fechas: se entregan en formato ISO 8601 (ejemplo: `2026-04-18T19:10:00+00:00`).

## Endpoints

### 1) Health check

- Metodo: `GET`
- Ruta: `/`
- Descripcion: confirma que la API esta en ejecucion.
- Query params: ninguno
- Body: ninguno
- Respuesta 200:

```json
{
  "message": "API running"
}
```

### 2) Ultimas lecturas de peces

- Metodo: `GET`
- Ruta: `/fish_readings/latest`
- Descripcion: lista lecturas recientes.
- Query params:
  - `hours` (int, opcional, default `24`, min `1`, max `168`)
  - `limit` (int, opcional, default `50`, min `1`, max `500`)
- Body: ninguno
- Respuesta 200:

```json
{
  "count": 2,
  "data": [
    {
      "_id": "6610f8...",
      "fishId": "fish_03",
      "robotId": "fish_03",
      "waterBody": "presa_centro",
      "timestamp": "2026-04-18T18:40:00+00:00",
      "updatedAt": "2026-04-18T18:40:00+00:00",
      "location": {"lat": 20.59, "lng": -100.39},
      "metrics": {
        "temperature": 24.1,
        "ph": 7.2,
        "turbidity": 5.7,
        "oxygen": 6.1
      },
      "alert": false
    }
  ]
}
```

- Errores comunes:
  - `422 Unprocessable Entity` si `hours` o `limit` no cumplen validaciones.

### 3) Resumen de lecturas

- Metodo: `GET`
- Ruta: `/fish_readings/summary`
- Descripcion: genera resumen estadistico de lecturas recientes.
- Query params:
  - `hours` (int, opcional, default `24`, min `1`, max `168`)
- Body: ninguno
- Respuesta 200:

```json
{
  "num_measurements": 25,
  "fishes": ["fish_01", "fish_02"],
  "water_bodies": ["presa_centro"],
  "temperature": {"avg": 23.1, "min": 18.2, "max": 28.4},
  "ph": {"avg": 7.1, "min": 6.4, "max": 8.2},
  "turbidity": {"avg": 6.0, "min": 1.1, "max": 11.9},
  "oxygen": {"avg": 5.4, "min": 3.7, "max": 7.8},
  "alerts_count": 3,
  "sample_records": []
}
```

- Nota: si no hay datos, devuelve `num_measurements: 0` y estadisticas en `null`.

### 4) Estado actual de peces

- Metodo: `GET`
- Ruta: `/fish_status`
- Descripcion: lista el ultimo estado conocido por pez.
- Query params:
  - `limit` (int, opcional, default `100`, min `1`, max `500`)
- Body: ninguno
- Respuesta 200:

```json
{
  "count": 10,
  "data": [
    {
      "_id": "6610f9...",
      "fishId": "fish_07",
      "robotId": "fish_07",
      "waterBody": "presa_centro",
      "timestamp": "2026-04-18T18:39:00+00:00",
      "updatedAt": "2026-04-18T18:39:00+00:00",
      "location": {"lat": 20.59, "lng": -100.39},
      "metrics": {
        "temperature": 26.0,
        "ph": 6.8,
        "turbidity": 4.3,
        "oxygen": 5.0
      },
      "alert": false
    }
  ]
}
```

### 5) Estado actual por pez

- Metodo: `GET`
- Ruta: `/fish_status/{fish_id}`
- Descripcion: devuelve el estado actual de un pez especifico.
- Path params:
  - `fish_id` (string, requerido)
- Query params: ninguno
- Body: ninguno
- Respuesta 200:

```json
{
  "_id": "6610f9...",
  "fishId": "fish_03",
  "robotId": "fish_03",
  "waterBody": "presa_centro",
  "timestamp": "2026-04-18T18:39:00+00:00",
  "updatedAt": "2026-04-18T18:39:00+00:00",
  "location": {"lat": 20.59, "lng": -100.39},
  "metrics": {
    "temperature": 24.9,
    "ph": 7.0,
    "turbidity": 4.9,
    "oxygen": 5.8
  },
  "alert": false
}
```

- Posibles errores:
  - `404 Not Found` si no existe estado para ese pez.

### 6) Simular lectura

- Metodo: `POST`
- Ruta: `/fish_readings/simulate`
- Descripcion: genera una lectura aleatoria, la guarda en historial y actualiza estado actual.
- Query params: ninguno
- Body: ninguno
- Respuesta 200:

```json
{
  "doc": {
    "_id": "6610fa...",
    "fishId": "fish_04",
    "robotId": "fish_04",
    "waterBody": "presa_centro",
    "timestamp": "2026-04-18T18:45:00+00:00",
    "location": {"lat": 20.59, "lng": -100.39},
    "metrics": {
      "temperature": 22.7,
      "ph": 8.6,
      "turbidity": 9.3,
      "oxygen": 3.8
    },
    "alert": true
  }
}
```

### 7) Reporte en lenguaje natural

- Metodo: `GET`
- Ruta: `/reports/report`
- Descripcion: genera reporte textual con Gemini usando resumen de lecturas recientes.
- Query params:
  - `hours` (int, opcional, default `24`, min `1`, max `168`)
- Body: ninguno
- Respuesta 200:

```json
{
  "report": "Resumen ejecutivo...",
  "summary": {
    "num_measurements": 25,
    "fishes": ["fish_01", "fish_02"],
    "water_bodies": ["presa_centro"],
    "temperature": {"avg": 23.1, "min": 18.2, "max": 28.4},
    "ph": {"avg": 7.1, "min": 6.4, "max": 8.2},
    "turbidity": {"avg": 6.0, "min": 1.1, "max": 11.9},
    "oxygen": {"avg": 5.4, "min": 3.7, "max": 7.8},
    "alerts_count": 3,
    "sample_records": []
  }
}
```

- Posibles errores:
  - `404 Not Found` si no hay datos recientes.
  - `500 Internal Server Error` si falla servicio externo (Gemini) o no esta configurada `GEMINI_API_KEY`.

### 8) Pregunta sobre los datos

- Metodo: `POST`
- Ruta: `/reports/ask`
- Descripcion: responde una pregunta en lenguaje natural basada en resumen de mediciones.
- Query params: ninguno
- Body JSON:

```json
{
  "question": "Que riesgo ves en las ultimas 24 horas?",
  "hours": 24
}
```

- Reglas del body:
  - `question` (string, requerido)
  - `hours` (int, opcional, default `24`)
- Respuesta 200:

```json
{
  "answer": "La principal anomalia es..."
}
```

- Posibles errores:
  - `404 Not Found` si no hay datos para analizar.
  - `422 Unprocessable Entity` si falta `question` o body invalido.
  - `500 Internal Server Error` si falla Gemini.

## cURL rapido

```bash
curl http://216.238.81.22:8000/fish_readings/latest?hours=12&limit=20
curl http://216.238.81.22:8000/fish_readings/summary?hours=24
curl http://216.238.81.22:8000/fish_status/fish_03
curl -X POST http://216.238.81.22:8000/fish_readings/simulate
curl http://216.238.81.22:8000/reports/report?hours=24
curl -X POST http://216.238.81.22:8000/reports/ask -H "Content-Type: application/json" -d "{\"question\":\"Hay alertas?\",\"hours\":24}"
```
