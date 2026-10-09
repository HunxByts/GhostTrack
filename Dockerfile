FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TERM=xterm

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY GhostTR.py ./
COPY ghosttrack/ ./ghosttrack/

# Run this third-party utility without root privileges.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin ghosttrack
USER ghosttrack

ENTRYPOINT ["python", "GhostTR.py"]
