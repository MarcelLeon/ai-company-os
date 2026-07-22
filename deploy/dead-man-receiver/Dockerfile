FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.11-slim

RUN useradd --create-home --uid 10001 aico \
    && mkdir --parents /data \
    && chown aico:aico /data
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

USER aico
VOLUME ["/data"]
EXPOSE 8080
ENTRYPOINT ["aico-dead-man-receiver"]
