import os
import importlib
import ipaddress

DRIVER_FOLDER = os.path.dirname(__file__)

def is_private_ip(ip):
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private
    except ValueError:
        return False

def load_drivers():
    drivers = {}
    for fname in os.listdir(DRIVER_FOLDER):
        if fname.endswith(".py") and fname != "__init__.py":
            name = fname[:-3]
            try:
                module = importlib.import_module(f"drivers.{name}")
                if hasattr(module, "fetch_ip"):
                    drivers[name] = module
            except Exception as e:
                print(f"[Error] Failed to load driver {name}: {e}")
    return drivers

def run_driver(driver_module, ip):
    if is_private_ip(ip):
        return {
            "ip": ip,
            "status": "private",
            "message": "This IP is in a reserved/private range and was not sent to external services."
        }
    try:
        return driver_module.fetch_ip(ip)
    except Exception as e:
        return {"error": str(e)}