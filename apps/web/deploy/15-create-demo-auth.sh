#!/bin/sh
set -eu

: "${BASIC_AUTH_HTPASSWD:?BASIC_AUTH_HTPASSWD is required for the management demo}"
umask 077
printf '%s\n' "$BASIC_AUTH_HTPASSWD" > /tmp/arie-sentinel-demo.htpasswd

resolver="$(awk '$1 == "nameserver" { print $2; exit }' /etc/resolv.conf)"
if [ -z "$resolver" ]; then
  echo "No container DNS resolver is configured" >&2
  exit 1
fi
case "$resolver" in
  *:*) resolver="[$resolver]" ;;
esac
printf 'resolver %s ipv6=off valid=30s;\n' "$resolver" > /tmp/arie-sentinel-resolver.conf
