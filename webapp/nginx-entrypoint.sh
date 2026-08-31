#!/bin/sh
set -eu

auth_server_url="${AUTH_SERVER_URL:-http://auth-server:3001}"
inference_server_url="${INFERENCE_SERVER_URL:-http://inference:8000}"

case "$auth_server_url" in
    http://*|https://*) ;;
    *)
        echo "AUTH_SERVER_URL must start with http:// or https://" >&2
        exit 1
        ;;
esac

case "$inference_server_url" in
    http://*|https://*) ;;
    *)
        echo "INFERENCE_SERVER_URL must start with http:// or https://" >&2
        exit 1
        ;;
esac

auth_server_url="${auth_server_url%/}"
inference_server_url="${inference_server_url%/}"

sed \
    -e "s|__AUTH_SERVER_URL__|$auth_server_url|g" \
    -e "s|__INFERENCE_SERVER_URL__|$inference_server_url|g" \
    /etc/nginx/nginx.conf.template \
    > /etc/nginx/conf.d/default.conf

exec "$@"