#!/usr/bin/env bash
exec /root/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome --no-sandbox --disable-dev-shm-usage --disable-gpu --no-zygote "$@"
