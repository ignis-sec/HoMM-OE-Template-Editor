"""PyInstaller entry point — imports the installed package and runs it."""

import sys

from templategen.app import main

if __name__ == "__main__":
    sys.exit(main())
