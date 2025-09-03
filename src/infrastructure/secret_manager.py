import base64
import json
from ds_security_validation.utils import Utils
from domain.constants import SERVICE_NAME, REGION_NAME

def get_secret(path: str, key: str, key2: str):
    utils = Utils(SERVICE_NAME, REGION_NAME)
    content = utils.get_secret(path)
    key_64 = json.loads(content).get(key)
    iv_64 = json.loads(content).get(key2)
    return (base64.b64decode(key_64), base64.b64decode(iv_64))

def get_key_jwt(path):
    utils = Utils(SERVICE_NAME, REGION_NAME)
    content = utils.get_secret(path)
    key = json.loads(content)
    return key
