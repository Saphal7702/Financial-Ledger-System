import uuid
import hashlib
import json
from datetime import datetime, timezone

def generate_id():
    return uuid.uuid4().hex

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def make_request_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()