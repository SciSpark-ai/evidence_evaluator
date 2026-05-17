"""Make `python -m eval.trec_pm2020 <cmd>` work."""
from eval.trec_pm2020.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
