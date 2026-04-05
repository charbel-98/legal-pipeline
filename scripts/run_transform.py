#!/usr/bin/env python
"""CLI: transform landing zone data into the processed zone.

Usage:
    python scripts/run_transform.py --start-date 2024-01 --end-date 2024-03
"""

import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.transformation_service import main  # noqa: E402

if __name__ == "__main__":
    main()
