FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md requirements.lock ./
COPY src ./src
COPY examples ./examples
COPY scripts ./scripts
RUN pip install --no-cache-dir -r requirements.lock . && useradd --create-home engine \
    && mkdir -p /data && chown engine:engine /data
USER engine
ENTRYPOINT ["task-engine"]
CMD ["submit", "examples/demo-request.json", "--data-dir", "/data"]
