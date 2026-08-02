FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY main.py ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Create workspace directory
RUN mkdir -p workspace

EXPOSE 8765

CMD ["uv", "run", "litepaw", "--host", "0.0.0.0", "--port", "8765"]
