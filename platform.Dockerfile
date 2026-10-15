FROM node:22-alpine AS frontend
WORKDIR /ui
COPY projects/agent-operations-control-center/frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY projects/agent-operations-control-center/frontend/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /portfolio
COPY projects ./projects
COPY platform-requirements.lock ./
RUN pip install --no-cache-dir -r platform-requirements.lock && pip install --no-cache-dir --no-deps ./projects/*/ && useradd --create-home portfolio
COPY portfolio_platform ./portfolio_platform
COPY scripts ./scripts
COPY site ./site
COPY --from=frontend /ui/dist ./projects/agent-operations-control-center/frontend/dist
ENV OPS_STATIC=/portfolio/projects/agent-operations-control-center/frontend/dist OPS_SHOWCASE=/portfolio/site PORTFOLIO_ROOT=/portfolio PYTHONUNBUFFERED=1
RUN mkdir -p /portfolio/.platform/reports /portfolio/.platform/gateway && chown -R portfolio:portfolio /portfolio/.platform
USER portfolio
CMD ["python", "-m", "uvicorn", "ops_center.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
