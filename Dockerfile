FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e ".[mcp]"

ENV PBME_CONTEXT_SECRET=replace-this-in-production
EXPOSE 8000

CMD ["pbme-mcp"]
