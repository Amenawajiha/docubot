"""Pytest configuration for chatbot-rag project."""

import os
import sys

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print(f"Added to sys.path: {PROJECT_ROOT}")