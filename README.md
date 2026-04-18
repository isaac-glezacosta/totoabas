# Totoabas® — Plataforma de Vigilancia Hídrica Inteligente

> Red inteligente de monitoreo de calidad del agua para detectar riesgos, coordinar respuesta en campo y sostener decisiones con datos confiables.

---

## Descripción

**Totoabas** es una plataforma de monitoreo continuo de cuerpos de agua. El sistema recopila lecturas de calidad del agua en tiempo real a través de sensores instalados en peces-robot autónomos, detecta anomalías mediante un modelo de inteligencia artificial (LSTM) y genera reportes automáticos con apoyo de Google Gemini.

### Características principales

- 📡 **Monitoreo en tiempo real** de pH, temperatura, turbidez y oxígeno disuelto
- 🤖 **Detección de ruido y anomalías** con modelo LSTM entrenado sobre datos del río
- 📊 **Reportes automáticos** generados por Gemini AI con análisis ambiental
- 🗺️ **Visualización geoespacial** de tramos del río y estado de los peces-sensor
- 🌐 **Frontend web completo** con panel de monitoreo, historial y cotizador
- 🔌 **API REST** para integración con otros sistemas

---

## Arquitectura

```
totoabas/
├── app/                    # Backend (FastAPI + MongoDB)
│   ├── main.py             # Punto de entrada de la API
│   ├── config.py           # Variables de entorno
│   ├── db.py               # Conexión a MongoDB
│   ├── models.py           # Modelos Pydantic
│   ├── routes/
│   │   ├── fish.py         # Endpoints de lecturas y estado de peces
│   │   └── reports.py      # Endpoints de reportes y preguntas (Gemini)
│   └── services/
│       ├── fish_service.py  # Lógica de negocio y resúmenes
│       └── gemini_service.py # Integración con Google Gemini
├── frontend/               # Interfaz web (HTML/CSS/JS estático)
│   ├── index.html          # Landing page
│   ├── Visualización.html  # Panel de monitoreo en vivo
│   ├── login.html          # Inicio de sesión
│   ├── reportes.html       # Reportes ambientales
│   ├── historial.html      # Historial de lecturas
│   ├── tramos.html         # Vista de tramos del río
│   ├── cotizar.html        # Cotizador del servicio
│   ├── configuracion.html  # Configuración
│   ├── contacto.html       # Contacto
│   ├── ayuda.html          # Ayuda
│   ├── clima.html          # Datos climáticos
│   ├── rio-queretaro.geojson # Geometría del río
│   └── Prueba.glb          # Modelo 3D del pez-sensor
├── models/
│   └── rnn_filtro.py       # Entrenamiento del modelo LSTM para filtro de ruido
└── datasets/
    ├── fish_readings.json   # Datos de lecturas de peces
    ├── fish_status.json     # Estado actual de peces
    └── train_dataset.zip    # Dataset de entrenamiento
```

---

## Requisitos

- Python 3.10+
- MongoDB (Atlas o local)
- Clave de API de [Google Gemini](https://aistudio.google.com/)

---

## Instalación y configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/isaac-glezacosta/totoabas.git
cd totoabas
```

### 2. Instalar dependencias

```bash
pip install fastapi uvicorn pymongo python-dotenv google-genai
```

Para el modelo de IA también se requiere:

```bash
pip install tensorflow pandas numpy scikit-learn
```

### 3. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
MONGO_URI=mongodb+srv://<usuario>:<contraseña>@<cluster>.mongodb.net/
DB_NAME=hackathon_db
FISH_READINGS_COLLECTION=fish_readings
FISH_STATUS_COLLECTION=fish_status
GEMINI_API_KEY=<tu_clave_gemini>
```

### 4. Iniciar el servidor

```bash
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`.

---

## API — Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Estado de la API |
| `GET` | `/fish_readings` | Lecturas recientes (últimas 24 h) |
| `GET` | `/fish_readings/latest` | Últimas lecturas por pez |
| `GET` | `/fish_readings/history/{fish_id}` | Historial de un pez específico |
| `GET` | `/fish_readings/summary` | Resumen estadístico de métricas |
| `GET` | `/fish_status` | Estado actual de todos los peces |
| `GET` | `/fish_status/{fish_id}` | Estado actual de un pez |
| `POST`| `/fish_readings/simulate` | Simula una nueva lectura |
| `GET` | `/reports/report` | Reporte ambiental (Gemini o fallback local) |
| `GET` | `/reports/report/gemini` | Reporte forzando uso de Gemini |
| `POST`| `/reports/ask` | Pregunta libre sobre los datos actuales |

### Parámetros comunes

- `hours` — Ventana temporal en horas (1–168, por defecto 24)
- `limit` — Número máximo de resultados

### Ejemplo de respuesta `/fish_readings/summary`

```json
{
  "num_measurements": 42,
  "fishes": ["fish_01", "fish_02"],
  "water_bodies": ["presa_centro"],
  "temperature": { "avg": 23.4, "min": 19.1, "max": 28.7 },
  "ph": { "avg": 7.2, "min": 6.8, "max": 7.9 },
  "turbidity": { "avg": 4.5, "min": 1.2, "max": 9.8 },
  "oxygen": { "avg": 6.1, "min": 4.3, "max": 7.8 },
  "alerts_count": 3,
  "source": "fish_readings"
}
```

---

## Modelo de IA — Filtro de ruido (LSTM)

El archivo `models/rnn_filtro.py` contiene el pipeline completo para entrenar un modelo LSTM que clasifica lecturas como **normales** (0) o **ruido/anomalía** (1).

**Variables de entrada:**

| Variable | Descripción |
|----------|-------------|
| `ph` | Potencial de hidrógeno |
| `temperatura_c` | Temperatura del agua (°C) |
| `turbidez_ntu` | Turbidez (NTU) |
| `oxigeno_mg_l` | Oxígeno disuelto (mg/L) |
| `conductividad_us_cm` | Conductividad eléctrica (μS/cm) |
| `tds_ppm` | Sólidos disueltos totales (ppm) |
| `nitratos_mg_l` | Nitratos (mg/L) |
| `profundidad_m` | Profundidad (m) |

**Arquitectura del modelo:**

- Ventana temporal de 10 lecturas consecutivas
- Capa LSTM (64 unidades) → Dropout (0.2) → Dense (32, ReLU) → Dense (1, Sigmoid)
- Optimizador Adam, 25 épocas

Para entrenar, coloca el archivo `dataset_agua_queretaro_4000.csv` en el directorio raíz y ejecuta:

```bash
python models/rnn_filtro.py
```

El modelo entrenado se guarda como `modelo_lstm_ruido_agua.h5`.

---

## Frontend

El frontend es una aplicación web estática ubicada en `frontend/`. Para usarlo localmente, sirve los archivos con cualquier servidor HTTP estático:

```bash
# Con Python
cd frontend
python -m http.server 3000
```

Accede en `http://localhost:3000`.

> **Nota:** Los endpoints de la API deben estar disponibles para que el panel de monitoreo muestre datos en tiempo real. Configura la URL base de la API en el frontend si usas un servidor diferente al predeterminado.

---

## Alertas

El sistema genera alertas automáticas cuando se detectan condiciones fuera de rango:

- pH < 6.5 o pH > 8.5
- Oxígeno disuelto < 4 mg/L

---

## Reportes generados con Gemini

Ejemplo [`Reporte_Totoabas.pdf`](./Reporte_Totoabas.pdf).

---

## Licencia

Este proyecto fue desarrollado como parte de un hackathon. Todos los derechos reservados © Totoabas®.
