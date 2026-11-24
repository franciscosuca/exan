"""Entry point used by PyInstaller to freeze the Exan engine into a single executable."""

import sys

from exan_sidecar.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
