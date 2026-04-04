import sqlite3
import json
from typing import List, Dict, Any

DB_PATH = "varaha_metrics.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We maintain the schema update for the MVP
    cursor.execute("DROP TABLE IF EXISTS metrics")
    
    # New metrics table with model_id for tiered auditing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            job_id TEXT PRIMARY KEY,
            team_id TEXT,
            model_id TEXT,
            ttft_ms REAL,
            total_time_ms REAL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            tps REAL,
            input_text TEXT,
            output_text TEXT,
            request_payload TEXT,
            response_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Teams / Organizations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            name TEXT,
            credits REAL DEFAULT 1000.0
        )
    """)
    
    # API Keys
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key TEXT PRIMARY KEY,
            team_id TEXT,
            name TEXT,
            active INTEGER DEFAULT 1,
            FOREIGN KEY(team_id) REFERENCES teams(id)
        )
    """)
    
    # Default data
    cursor.execute("INSERT OR IGNORE INTO teams (id, name, credits) VALUES ('system', 'System Team', 999999.0)")
    cursor.execute("INSERT OR IGNORE INTO api_keys (key, team_id, name) VALUES ('admin-key', 'system', 'Default Admin')")
    
    conn.commit()
    conn.close()

def store_metrics(job_id: str, team_id: str, metrics: Dict[str, Any], 
                  input_text: str = "", output_text: str = "", 
                  request_payload: dict = None, response_json: dict = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    model_id = metrics.get("model", "qwen")
    
    cursor.execute("""
        INSERT OR REPLACE INTO metrics 
        (job_id, team_id, model_id, ttft_ms, total_time_ms, input_tokens, output_tokens, tps, 
         input_text, output_text, request_payload, response_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        team_id,
        model_id,
        metrics.get("ttft_ms"),
        metrics.get("total_time_ms"),
        metrics.get("input_tokens"),
        metrics.get("output_tokens"),
        metrics.get("tps"),
        input_text,
        output_text,
        json.dumps(request_payload) if request_payload else None,
        json.dumps(response_json) if response_json else None
    ))
    
    # Tiered Billing Logic
    # Qwen (1.5B) = 1.0 multiplier
    # TinyLlama (1.1B) = 0.3 multiplier
    multiplier = 1.0 if model_id == "qwen" else 0.3
    total_tokens = metrics.get("input_tokens", 0) + metrics.get("output_tokens", 0)
    cost = (total_tokens / 1000.0) * multiplier
    
    cursor.execute("UPDATE teams SET credits = credits - ? WHERE id = ?", (cost, team_id))
    
    conn.commit()
    conn.close()

def validate_api_key(key: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT teams.id, teams.name, teams.credits 
        FROM api_keys 
        JOIN teams ON api_keys.team_id = teams.id 
        WHERE api_keys.key = ? AND api_keys.active = 1
    """, (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"team_id": row[0], "team_name": row[1], "credits": row[2]}
    return {}

def get_job_metrics(job_id: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM metrics WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {}
        
    return {
        "job_id": row[0],
        "team_id": row[1],
        "model_id": row[2],
        "ttft_ms": row[3],
        "total_time_ms": row[4],
        "input_tokens": row[5],
        "output_tokens": row[6],
        "tps": row[7],
        "input_text": row[8],
        "output_text": row[9],
        "request_payload": json.loads(row[10]) if row[10] else {},
        "response_json": json.loads(row[11]) if row[11] else {},
        "created_at": row[12]
    }

# Remaining CRUD functions persist...
def get_all_job_ids() -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT job_id FROM metrics ORDER BY created_at DESC")
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids

def create_team(team_id: str, name: str, credits: float = 1000.0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO teams (id, name, credits) VALUES (?, ?, ?)", (team_id, name, credits))
    conn.commit()
    conn.close()

def get_all_teams() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, credits FROM teams")
    teams = [{"id": r[0], "name": r[1], "credits": r[2]} for r in cursor.fetchall()]
    conn.close()
    return teams

def create_api_key(key: str, team_id: str, name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO api_keys (key, team_id, name) VALUES (?, ?, ?)", (key, team_id, name))
    conn.commit()
    conn.close()

def deactivate_api_key(key: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE api_keys SET active = 0 WHERE key = ?", (key,))
    conn.commit()
    conn.close()

def get_team_keys(team_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, name, active FROM api_keys WHERE team_id = ?", (team_id,))
    keys = [{"key": r[0], "name": r[1], "active": bool(r[2])} for r in cursor.fetchall()]
    conn.close()
    return keys
