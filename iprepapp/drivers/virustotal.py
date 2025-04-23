import requests
import time
from models import DriverResponse, IPRequest, IPAccessLog, db
from utils.driver_config import get_driver_config
from utils.log_helper import get_logger

logger = get_logger()

def fetch_ip(ip):
    logger.debug(f"[VirusTotal] Fetching IP {ip}")
    config = get_driver_config('VirusTotal')
    if not config.get('enabled', True):
        return {"error": "driver disabled"}

    # check DB cache
    record = IPRequest.query.filter_by(ip=ip).first()
    if record and (time.time() - record.timestamp) < 30 * 86400:
        cached = DriverResponse.query.filter_by(ip=ip, driver='VirusTotal').first()
        if cached:
            logger.debug(f"[VirusTotal] Cache HIT for IP {ip}")
            db.session.add(IPAccessLog(ip=ip, timestamp=time.time(), source='cache'))
            db.session.commit()
            return cached.data

    url = config.get("url", "").format(ip=ip)
    headers = {
        "x-apikey": config.get("api_key"),
        "accept": "application/json"
    }

    logger.debug(f"[VirusTotal] Sending request to {url}")

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        # save to cache
        db.session.add(DriverResponse(driver='VirusTotal', ip=ip, data=data))
        db.session.add(IPRequest(ip=ip, timestamp=time.time()))
        db.session.add(IPAccessLog(ip=ip, timestamp=time.time(), source='driver'))
        db.session.commit()
        return data

    except Exception as e:
        logger.error("[VirusTotal] Request failed: %s", str(e))
        return {"error": str(e)}