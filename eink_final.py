#!/usr/bin/env python3
"""Compatibility entry point for existing eink-display.service installations."""

from launcher import main


if __name__ == "__main__":
    raise SystemExit(main())
