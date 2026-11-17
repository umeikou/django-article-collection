#!/bin/bash
# 周报定时任务入口：source .env 后执行 Django 管理命令
# 用法：weekly_digest_cron.sh create | send

set -a
# shellcheck source=../.env
source "$(dirname "$0")/../.env"
set +a

export DB_FILE=production.db
export DJANGO_SETTINGS_MODULE=article_collection_django.settings_production

cd "$(dirname "$0")/.." || exit 1

case "$1" in
  create)
    exec /usr/bin/python3 manage.py create_weekly_digest
    ;;
  send)
    exec /usr/bin/python3 manage.py send_weekly_digest
    ;;
  *)
    echo "Usage: $0 create|send" >&2
    exit 1
    ;;
esac
