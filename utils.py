import json
from pathlib import Path


def load_secret():
    with open(Path(__file__).parent / "secrets.json", "r") as f:
        secrets = json.load(f)
        return secrets["cookies"], secrets["headers"]
