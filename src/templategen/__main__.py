"""Allow `python -m templategen`."""

import sys

from templategen.app import main

if __name__ == "__main__":
    sys.exit(main())
