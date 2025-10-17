# Dockerfile
# 1. Usar una imagen base oficial de Python
FROM python:3.11-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar e instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar el script principal
COPY main.py .

# 5. Comando para ejecutar el script cuando el contenedor se inicie (Cloud Run Job)
# El Cloud Run Job se ejecuta hasta que este comando termina
CMD ["python", "main.py"]