import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'driver_configs.json')

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] Config file not found at {CONFIG_PATH}.")
        return {}
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[ERROR] Config file {CONFIG_PATH} is invalid JSON.")
        return {}

def save_config(config_dict):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config_dict, f, indent=2)

def get_driver_config(name):
    config = load_config()
    return config.get(name, {})

def update_driver_config(name, changes):
    config = load_config()
    config.setdefault(name, {})
    config[name].update(changes)
    save_config(config)