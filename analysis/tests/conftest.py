import sys
from pathlib import Path

A = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A))
sys.path.insert(0, str(A / "mock"))
