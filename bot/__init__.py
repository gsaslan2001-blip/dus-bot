# DUS Mentoru — Telegram Bot Package

import sys
import os

# CRITICAL: Add scripts/ to path BEFORE any other imports
# scripts/search_engine.py does `from embedding_utils import ...` (local import)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "scripts"))
