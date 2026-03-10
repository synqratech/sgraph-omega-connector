#!/usr/bin/env sh
set -eu

CERT_DIR=/etc/nginx/certs
mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_DIR/local.crt" ] || [ ! -f "$CERT_DIR/local.key" ]; then
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$CERT_DIR/local.key" \
    -out "$CERT_DIR/local.crt" \
    -subj "/CN=localhost"
fi

exec "$@"
