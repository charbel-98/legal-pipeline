#!/usr/bin/env python
"""CLI: transform landing zone data into the processed zone.

Run via the Makefile (which sources .env and sets PYTHONPATH):
    make transform START_MONTH=2024-01 END_MONTH=2024-03
"""

from app.services.transformation_service import main

if __name__ == "__main__":
    main()
