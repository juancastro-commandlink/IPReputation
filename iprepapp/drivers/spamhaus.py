import requests
import time
from models import DriverResponse, IPRequest, IPAccessLog, db
from utils.driver_config import get_driver_config
from utils.log_helper import get_logger

logger = get_logger()

auth_token_cache = {
    "token": None,
    "expires": 0
}

def fetch_auth_token(config):
    logger.debug("[Spamhaus] Fetching auth token...")
    payload = {
        "username": config.get("username"),
        "password": config.get("api_key"),
        "realm": "intel"
    }
    logger.debug("[Spamhaus] Auth payload: %s", payload)
    try:
        response = requests.post(config.get("authurl"), json=payload)
        logger.debug("[Spamhaus] URL for auth: %s", config.get("authurl"))
        logger.debug("[Spamhaus] Auth response: %s", response.text)
        data = response.json()
        token = data.get("token")
        expires = data.get("expires", 0)
        if token:
            auth_token_cache["token"] = token
            auth_token_cache["expires"] = expires
            return token
        else:
            logger.error("[Spamhaus] Failed to retrieve token: %s", data)
            return None
    except Exception as e:
        logger.error("[Spamhaus] Auth request failed: %s", str(e))
        return None

def get_valid_token(config):
    now = int(time.time())
    if auth_token_cache["token"] and auth_token_cache["expires"] > now:
        return auth_token_cache["token"]
    return fetch_auth_token(config)

def fetch_ip(ip):
    logger.debug(f"[Spamhaus] Fetching IP {ip}")
    config = get_driver_config('spamhaus')
    if not config.get('enabled', True):
        return {"error": "driver disabled"}

    # check DB cache
    record = IPRequest.query.filter_by(ip=ip).first()
    if record and (time.time() - record.timestamp) < 30 * 86400:
        cached = DriverResponse.query.filter_by(ip=ip, driver='spamhaus').first()
        if cached:
            logger.debug(f"[Spamhaus] Cache HIT for IP {ip}")
            db.session.add(IPAccessLog(ip=ip, timestamp=time.time(), source='cache'))
            db.session.commit()
            return cached.data

    # fetch new token if needed
    token = get_valid_token(config)
    if not token:
        return {"error": "failed to authenticate with Spamhaus"}

    url = config.get("url", "").format(ip=ip)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    logger.debug(f"[Spamhaus] Querying {url} with token")

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        # save to cache
        db.session.add(DriverResponse(driver='spamhaus', ip=ip, data=data))
        db.session.add(IPRequest(ip=ip, timestamp=time.time()))
        db.session.add(IPAccessLog(ip=ip, timestamp=time.time(), source='driver'))
        db.session.commit()
        return data

    except Exception as e:
        logger.error("[Spamhaus] Request failed: %s", str(e))
        return {"error": str(e)}
