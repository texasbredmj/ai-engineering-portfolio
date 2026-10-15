FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.lock . && useradd --create-home evaluator
COPY benchmarks ./benchmarks
USER evaluator
WORKDIR /home/evaluator
ENTRYPOINT ["agent-eval"]
CMD ["run", "--suite", "/app/benchmarks/baseline-v1.jsonl", "--output", "/home/evaluator/results", "--version", "baseline-v1"]
