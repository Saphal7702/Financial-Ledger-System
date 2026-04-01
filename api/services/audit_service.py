import json
from .helpers import generate_id, utc_now

def log_event(conn, entity_type, entity_id, action, actor_type="system", actor_id=None, metadata=None):
    conn.execute(
        """
        INSERT INTO audit_logs (
            id, entity_type, entity_id, action, actor_type, actor_id, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            generate_id(),
            entity_type,
            entity_id,
            action,
            actor_type,
            actor_id,
            json.dumps(metadata) if metadata else None,
            utc_now()
        )
    )