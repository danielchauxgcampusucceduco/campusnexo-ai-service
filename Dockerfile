FROM python:3.12-slim
WORKDIR /app
# WITH_VISION=true installs YOLO + OpenCV for /v1/vision/count; the weights (YOLO_MODEL) are downloaded
# on first use or mounted. Without it the image is small and that route answers 503 by design.
ARG WITH_VISION=false
COPY pyproject.toml ./
COPY app ./app
RUN if [ "$WITH_VISION" = "true" ]; then pip install --no-cache-dir ".[vision]"; else pip install --no-cache-dir .; fi
ENV PORT=8001
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8001'))"
# PORT is injected by hosting platforms such as Render.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
