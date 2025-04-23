import requests
import time
from models import DriverResponse, IPRequest, IPAccessLog, db
from utils.driver_config import get_driver_config
from utils.log_helper import get_logger


logger = get_logger()


def fetch_ip(ip):
    logger.debug(f"[DEBUG] Fetching IP {ip} from Greynoise driver")
    config = get_driver_config('greynoise')
    if not config.get('enabled', True):
        return {"error": "driver disabled"}

    # check DB cache
    record = IPRequest.query.filter_by(ip=ip).first()
    if record and (time.time() - record.timestamp) < 30 * 86400:
        cached = DriverResponse.query.filter_by(ip=ip, driver='greynoise').first()
        if cached:
            logger.debug(f"[DEBUG] Cache HIT for IP {ip} — Logging access")
            db.session.add(IPAccessLog(ip=ip, timestamp=time.time(), source='cache'))
            db.session.commit()
            return cached.data
        else:
            logger.debug(f"[DEBUG] Found cached response: {cached is not None}")

    # make API call
    url = config.get("url", "").format(ip=ip)
    headers = {
        "accept": "application/json",
        "key": config.get("api_key", ""),
    }
    logger.debug(f"[DEBUG] Greynoise request URL: {url}")
    logger.debug(f"[DEBUG] Greynoise request headers: {headers}")

    try:
        response = requests.get(url, headers=headers)
        # response.raise_for_status()
        # GreyNoise API returns 404 if the IP is not found
        data = response.json()

        # save to cache
        db.session.add(DriverResponse(driver='greynoise', ip=ip, data=data))
        db.session.add(IPRequest(ip=ip, timestamp=time.time()))
        db.session.add(IPAccessLog(ip=ip, timestamp=time.time(), source='driver'))
        db.session.commit()
        return data

    except Exception as e:
        return {"error": str(e)}
