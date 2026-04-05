import sqlite3
import json
from typing import List, Dict, Any

DB_PATH = "varaha_metrics.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop all on init for rapid iteration
    cursor.execute("DROP TABLE IF EXISTS metrics")
    cursor.execute("DROP TABLE IF EXISTS api_keys")
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS teams") # Legacy
    
    # Users (Acting as the core billing entity)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT,
            name TEXT,
            credits REAL DEFAULT 1000.0
        )
    """)

    # Intelligent API Keys
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            model_id TEXT DEFAULT 'qwen',
            temperature REAL DEFAULT 0.1,
            system_prompt TEXT,
            rag_text TEXT,
            active INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Metrics table now tracks api_key directly
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            job_id TEXT PRIMARY KEY,
            user_id TEXT,
            api_key TEXT,
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
    
    conn.commit()
    conn.close()

def store_metrics(job_id: str, user_id: str, api_key: str, metrics: Dict[str, Any], 
                  input_text: str = "", output_text: str = "", 
                  request_payload: dict = None, response_json: dict = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    model_id = metrics.get("model", "qwen")
    
    cursor.execute("""
        INSERT OR REPLACE INTO metrics 
        (job_id, user_id, api_key, model_id, ttft_ms, total_time_ms, input_tokens, output_tokens, tps, 
         input_text, output_text, request_payload, response_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        user_id,
        api_key,
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
    multiplier = 1.0 if model_id == "qwen" else 0.3
    total_tokens = metrics.get("input_tokens", 0) + metrics.get("output_tokens", 0)
    cost = (total_tokens / 1000.0) * multiplier
    
    cursor.execute("UPDATE users SET credits = credits - ? WHERE id = ?", (cost, user_id))
    
    conn.commit()
    conn.close()

def validate_api_key(key: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT users.id, users.credits, api_keys.model_id, api_keys.temperature, api_keys.system_prompt, api_keys.rag_text
        FROM api_keys 
        JOIN users ON api_keys.user_id = users.id 
        WHERE api_keys.key = ? AND api_keys.active = 1
    """, (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0], 
            "credits": row[1], 
            "model_id": row[2], 
            "temperature": row[3], 
            "system_prompt": row[4], 
            "rag_text": row[5]
        }
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
        "user_id": row[1],
        "api_key": row[2],
        "model_id": row[3],
        "ttft_ms": row[4],
        "total_time_ms": row[5],
        "input_tokens": row[6],
        "output_tokens": row[7],
        "tps": row[8],
        "input_text": row[9],
        "output_text": row[10],
        "request_payload": json.loads(row[11]) if row[11] else {},
        "response_json": json.loads(row[12]) if row[12] else {},
        "created_at": row[13]
    }

def get_all_job_ids() -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT job_id FROM metrics ORDER BY created_at DESC")
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids

def get_metrics_by_key(api_key: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, model_id, ttft_ms, tps, input_tokens, output_tokens, input_text, output_text, request_payload, response_json, created_at FROM metrics WHERE api_key = ? ORDER BY created_at DESC LIMIT 50", (api_key,))
    rows = cursor.fetchall()
    conn.close()
    return [{
        "job_id": r[0],
        "model_id": r[1],
        "ttft_ms": r[2],
        "tps": r[3],
        "input_tokens": r[4],
        "output_tokens": r[5],
        "input_text": r[6],
        "output_text": r[7],
        "request_payload": json.loads(r[8]) if r[8] else {},
        "response_json": json.loads(r[9]) if r[9] else {},
        "created_at": r[10]
    } for r in rows]

def create_api_key(key: str, user_id: str, name: str, model_id: str = "qwen", temperature: float = 0.1, system_prompt: str = "", rag_text: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO api_keys (key, user_id, name, model_id, temperature, system_prompt, rag_text) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (key, user_id, name, model_id, temperature, system_prompt, rag_text))
    conn.commit()
    conn.close()

def deactivate_api_key(key: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE api_keys SET active = 0 WHERE key = ?", (key,))
    conn.commit()
    conn.close()

def get_user_keys(user_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, name, model_id, temperature, active, system_prompt, rag_text FROM api_keys WHERE user_id = ? AND active = 1", (user_id,))
    keys = [{"key": r[0], "name": r[1], "model_id": r[2], "temperature": r[3], "active": bool(r[4]), "system_prompt": r[5] or "", "has_rag": bool(r[6])} for r in cursor.fetchall()]
    conn.close()
    return keys

def create_user(user_id: str, email: str, password_hash: str, name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)", (user_id, email, password_hash, name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_email(email: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password_hash, name, credits FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "email": row[1], "password_hash": row[2], "name": row[3], "credits": row[4]}
    return {}

def update_user_password(user_id: str, password_hash: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    conn.close()
