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

## Configuración de `GROQ_API_KEY`

Configura tu clave de API en la variable de entorno `GROQ_API_KEY` (o en un archivo `.env` local):

**PowerShell:**

```powershell
$env:GROQ_API_KEY = "tu_api_key_de_groq"
```

**Bash:**

```bash
export GROQ_API_KEY="tu_api_key_de_groq"
```

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

Ejecuta el contenedor exponiendo el puerto `8501`, pasando `GROQ_API_KEY` y montando la carpeta `tickets/` para conservar los reportes Excel diarios (`tickets/tickets_YYYY-MM-DD.xlsx`) en tu máquina:

**PowerShell:**

```powershell
docker run --rm -e GROQ_API_KEY="tu_api_key_de_groq" -p 8501:8501 -v "${PWD}\tickets:/app/tickets" soporte-ia:latest
```

**Git Bash:**

```bash
MSYS_NO_PATHCONV=1 docker run --rm -e GROQ_API_KEY="tu_api_key_de_groq" -p 8501:8501 -v "$(pwd)/tickets:/app/tickets" soporte-ia:latest
```

Luego accede a la aplicación en `http://localhost:8501`.
