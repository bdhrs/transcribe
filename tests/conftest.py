import os

# Importing dictate loads pynput, which needs an X display unless the dummy backend is chosen.
os.environ.setdefault("PYNPUT_BACKEND", "dummy")
