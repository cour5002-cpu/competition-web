FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG INSTALL_FONTS=1
ARG UPGRADE_PIP=0

ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=5

WORKDIR /app

RUN set -eux; \
  apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 update; \
  apt-get install -y --no-install-recommends ca-certificates; \
  if [ "${INSTALL_FONTS}" = "1" ]; then \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 install -y --no-install-recommends fonts-noto-cjk; \
  fi; \
  rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN set -eux; \
  if [ "${UPGRADE_PIP}" = "1" ]; then \
    python -m pip install --no-cache-dir --upgrade pip; \
  fi; \
  pip install --no-cache-dir -i ${PIP_INDEX_URL} -r /app/requirements.txt

COPY . /app

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
