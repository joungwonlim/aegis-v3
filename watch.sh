#!/bin/bash
# AEGIS v3.0 Watch Dashboard (Rich UI)
# Real-time monitoring with auto-refresh

cd "$(dirname "$0")"
source venv/bin/activate
watch -n 3 python monitoring/watch_dashboard_rich.py
