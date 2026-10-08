# docs/05-BACKEND-SPEC.md §7. The only network use this image ever has is
# right here, at build time. Build from backend/: docker build -t
# greenline-sandbox:latest greenline/sandbox
FROM python:3.12-slim
RUN pip install --no-cache-dir pytest ruff
WORKDIR /work
