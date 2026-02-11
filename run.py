#!/usr/bin/env python3
"""Launch the Claude Instance Manager bot.

Usage:
    python run.py [config.yaml] [--debug] [--trace] [--verbose]
"""
import asyncio

from src.main import main

if __name__ == "__main__":
    asyncio.run(main())
