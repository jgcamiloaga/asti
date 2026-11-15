# Soporte IA

Asistente Automatizado de Soporte TI y Ciberseguridad - Nivel 1.

## Modelo utilizado

- **Modelo final:** `openai/gpt-oss-120b` (seleccionado como el modelo de chat disponible más similar tras verificar en la API de Groq que `llama-3.3-70b-versatile` no estaba disponible para esta cuenta).

## Requisitos e instalación

- Python 3.12+
- Cuenta y clave API de [Groq](https://console.groq.com/)

Instala las dependencias desde la raíz del proyecto:

```bash
pip install -r requirements.txt
```

## Configuración de variables de entorno

Copia `.env.example` a `.env` y completa tu clave de API en `GROQ_API_KEY`:

**PowerShell:**

```powershell
$env:GROQ_API_KEY = "tu_api_key_de_groq"
```

**Bash:**

```bash
export GROQ_API_KEY="tu_api_key_de_groq"
```

### Webhook opcional de alertas

Cuando se escala un ticket, la aplicación puede enviar una notificación `POST` en JSON si configuras:

- `WEBHOOK_ALERTA_URL`: URL del receptor (ej. Slack, Teams o un endpoint propio).
- `WEBHOOK_SECRET`: secreto opcional para firmar el cuerpo JSON con HMAC-SHA256 en la cabecera `X-Webhook-Signature: sha256=<firma>`.

## Ejecución local

Inicia la aplicación web con Streamlit:

```bash
streamlit run app.py
```

## Ejecución de pruebas

Ejecuta la suite de pruebas unitarias con `pytest`:

```bash
pytest
```

## Ejecución de evaluación

Ejecuta el script de evaluación del asistente:

```bash
python evaluacion.py
```

## Construcción y ejecución con Docker

Construye la imagen Docker:

```bash
docker build -t soporte-ia:latest .
```

Ejecuta el contenedor exponiendo el puerto `8501`, pasando tus variables de entorno y montando la carpeta `tickets/` para ver los reportes Excel diarios (`tickets/tickets_YYYY-MM-DD.xlsx`) directamente en la ruta del proyecto:

**PowerShell:**

```powershell
docker run --rm --env-file .env -p 8501:8501 -v "${PWD}\tickets:/app/tickets" soporte-ia:latest
```

**Git Bash:**

```bash
MSYS_NO_PATHCONV=1 docker run --rm --env-file .env -p 8501:8501 -v "$(pwd)/tickets:/app/tickets" soporte-ia:latest
```

*(Si no usas archivo `.env`, reemplaza `--env-file .env` por `-e GROQ_API_KEY="tu_api_key_de_groq"`.)*

Luego accede a la aplicación en `http://localhost:8501`.
