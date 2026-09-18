# Imagen de produccion minima: solo el interprete de Python necesario y los
# paquetes de runtime listados en requirements.txt (NO requirements-dev.txt:
# pytest/ruff/httpx se quedan fuera de esta imagen, son solo para desarrollo).
FROM python:3.12-slim


WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copiar solo el manifiesto primero para aprovechar la cache de capas de
# Docker: si el codigo cambia pero no las dependencias, este paso no se
# vuelve a ejecutar.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codigo de la aplicacion y migraciones (scripts/migrate.py las necesita
# para poder correr dentro del contenedor si hace falta, p. ej. via
# `az containerapp exec`).
COPY app ./app
COPY db ./db
COPY scripts ./scripts

# Usuario sin privilegios: la app no necesita root para nada.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
