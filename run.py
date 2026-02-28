#!/usr/bin/env python3
"""Run the DeDupify Streamlit app. Execute from project root."""
import subprocess
import sys
from pathlib import Path

# Ensure we run from project root
root = Path(__file__).resolve().parent
subprocess.run(
    [sys.executable, "-m", "streamlit", "run", "src/app.py", "--server.headless", "true"],
    cwd=root,
)
