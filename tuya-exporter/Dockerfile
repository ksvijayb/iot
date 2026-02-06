FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    tuya-iot-py-sdk \
    prometheus-client \
    flask

COPY exporter.py .

EXPOSE 9109

CMD ["python", "exporter.py"]
