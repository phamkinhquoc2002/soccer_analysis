FROM python:3.13-slim

# Copy uv from image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy app source code
COPY . /app
WORKDIR /app

# Install system dependencies (optional, e.g., for wheels)
RUN apt update && apt install -y build-essential curl && \
    uv venv && \
    uv add -r requirements.txt && \
    apt purge -y curl && apt autoremove -y && apt clean

# Make sure etl.sh is executable
RUN chmod +x etl.sh && \ 
    . .venv/bin/activate && \ 
    ./etl.sh

EXPOSE 8000

CMD ["/app/.venv/bin/python", "app.py"]