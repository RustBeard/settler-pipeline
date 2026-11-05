# Shared paths. Output goes to <repo>/out unless SETTLER_OUT is set.
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("SETTLER_OUT", os.path.join(ROOT, "out"))
RAW = os.path.join(OUT, "raw")
PX = os.path.join(OUT, "px")
HERE = os.path.dirname(os.path.abspath(__file__))
for d in (OUT, RAW, PX): os.makedirs(d, exist_ok=True)
