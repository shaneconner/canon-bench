import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from feed.sync import total_amount

expected = 21859
actual = total_amount()
assert actual == expected, f"total_amount(): {actual} != {expected}"
print("orders tests pass")
