FROM python:3.14-slim-trixie

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Install Node.js (for mcp-proxy), ca-certificates, curl, git, and git-lfs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    git-lfs \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g mcp-proxy@6.4.3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv from official binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files
COPY . /app

# Fail-fast guard: the OET corpus DB is a 191 MB Git-LFS file. A checkout
# without `git lfs pull` ships only a ~130-byte LFS pointer, so every data
# tool errors at runtime. Verify the DB is a real, queryable SQLite database
# here so such an image fails the build instead of deploying broken.
RUN python3 scripts/verify_db.py

# Install project dependencies
RUN uv sync

# Expose default port if proxy runs over HTTP/SSE
EXPOSE 8080

# Runtime healthcheck: corpus DB queryable + mcp-proxy accepting connections
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD /app/.venv/bin/python /app/scripts/healthcheck.py

CMD ["mcp-proxy", "--", "uv", "run", "oet-mcp-server"]
