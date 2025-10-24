"""
Deprecated wrapper.

Use: python scripts/verify_matchup.py --deck-a "Azorius Blink" --deck-b "Esper Goryo's" --event-dir "<path>"
"""

import runpy
import sys
from pathlib import Path


def main():
	scripts_path = Path(__file__).resolve().parent / 'scripts' / 'verify_matchup.py'
	if not scripts_path.exists():
		print('scripts/verify_matchup.py not found. Please run the new CLI directly from scripts/.')
		return 2
	# Forward args to the new CLI
	sys.argv[0] = str(scripts_path)
	runpy.run_path(str(scripts_path), run_name='__main__')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
