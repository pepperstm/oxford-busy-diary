FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DATA_DIR=/data PORT=8080
VOLUME /data
EXPOSE 8080
CMD ["python", "-m", "app.main"]
