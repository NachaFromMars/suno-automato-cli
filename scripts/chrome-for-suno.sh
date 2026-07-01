#!/usr/bin/env bash
exec /root/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome --no-sandbox --disable-dev-shm-usage --disable-gpu --no-zygote "$@"
