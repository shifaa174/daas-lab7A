FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py seed_db.py ./
# build the database at image-build time so the container is self-contained
RUN python seed_db.py
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 app:app"]
