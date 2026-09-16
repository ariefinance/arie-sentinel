#!/bin/sh
set -eu

: "${BASIC_AUTH_HTPASSWD:?BASIC_AUTH_HTPASSWD is required for the management demo}"
umask 077
printf '%s\n' "$BASIC_AUTH_HTPASSWD" > /tmp/arie-sentinel-demo.htpasswd
