FROM python:3.13-slim

WORKDIR /app

# OpenCV va MediaPipe uchun kerakli tizim kutubxonalarini o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libxrender1 \
    libxext6 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Avval barcha paketlarni o'rnatamiz, keyin headless opencv ni majburan o'rnatamiz
# (mediapipe o'zi opencv-contrib-python ni tortib oladi, biz uni headless bilan almashtiramiz)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y opencv-python opencv-contrib-python 2>/dev/null; \
    pip install --no-cache-dir --force-reinstall opencv-python-headless==4.10.0.84

COPY . .

CMD ["python", "main.py"]
