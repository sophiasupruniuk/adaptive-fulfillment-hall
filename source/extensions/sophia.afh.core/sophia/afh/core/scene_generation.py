import json
import os

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "warehouse_config.json")

def load_config():
    with open(config_path) as f:
        return json.load(f)