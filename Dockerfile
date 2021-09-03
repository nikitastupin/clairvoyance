# Image: python:3.9.6-slim-buster
FROM python@sha256:ab2e6f2a33c44bd0cda2138a8308ca45145edd21ba80a125c9df57c46a255839 as build

RUN apt update \
    && apt upgrade -y \
    && apt install -y python3-dev build-essential

ENV VIRTUAL_ENV=/tmp/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt


# Image: python:3.9.6-alpine3.14
FROM python@sha256:3e7e8a57a959c393797f0c90fa7b0fdbf7a40c4a274028e3f28a4f33d4783866

WORKDIR /home/clairvoyance

RUN adduser \
    --home "$(pwd)" \
    --gecos "" \
    --disabled-password \
    clairvoyance

COPY --from=build /tmp/venv .venv/
COPY clairvoyance clairvoyance/

USER clairvoyance
ENV PYTHONPATH=/home/clairvoyance
ENTRYPOINT [".venv/bin/python3", "clairvoyance/__main__.py"]
