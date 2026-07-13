FROM python:3.13-slim

WORKDIR /app

# Sistem bağımlılıklarını kur (eğer gerekliyse)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Requirements dosyasını kopyala ve bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

# FastAPI portunu dışa aç
EXPOSE 8000

# Uygulamayı başlat
CMD ["python", "main.py"]
