FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.lock . && useradd --create-home lab
USER lab
WORKDIR /home/lab
ENTRYPOINT ["recovery-lab"]
CMD ["backend", "--db", "/home/lab/backend.sqlite", "--host", "0.0.0.0", "--port", "8080"]
