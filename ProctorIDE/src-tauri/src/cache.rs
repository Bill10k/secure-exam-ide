use aes_gcm::aead::{Aead, KeyInit};
use aes_gcm::{Aes256Gcm, Nonce};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::path::PathBuf;
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Manager};

#[derive(Debug, Serialize, Deserialize)]
pub struct SnapshotCacheEntry {
    pub session_id: i64,
    pub question_id: i64,
    pub code: String,
    pub version: i64,
    pub saved_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PendingSubmissionEntry {
    pub id: i64,
    pub session_id: i64,
    pub question_id: i64,
    pub payload: String,
    pub synced: bool,
    pub retry_count: i64,
    pub created_at: String,
}

const ENCRYPTED_PREFIX: &str = "enc:v1:";

fn derive_cache_key(cache_seed: &str) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(cache_seed.as_bytes());
    let digest = hasher.finalize();
    let mut key = [0u8; 32];
    key.copy_from_slice(&digest);
    key
}

fn encrypt_string(cache_seed: &str, plaintext: &str) -> Result<String, String> {
    let key = derive_cache_key(cache_seed);
    let cipher = Aes256Gcm::new_from_slice(&key).map_err(|error| error.to_string())?;
    let mut nonce_bytes = [0u8; 12];
    getrandom::getrandom(&mut nonce_bytes).map_err(|error| error.to_string())?;
    let nonce = Nonce::from_slice(&nonce_bytes);
    let ciphertext = cipher
        .encrypt(nonce, plaintext.as_bytes())
        .map_err(|_| "Failed to encrypt cache payload".to_string())?;

    Ok(format!(
        "{}{}.{}",
        ENCRYPTED_PREFIX,
        URL_SAFE_NO_PAD.encode(nonce_bytes),
        URL_SAFE_NO_PAD.encode(ciphertext)
    ))
}

fn decrypt_string(cache_seed: &str, stored_value: &str) -> Result<String, String> {
    if !stored_value.starts_with(ENCRYPTED_PREFIX) {
        return Ok(stored_value.to_string());
    }

    let payload = &stored_value[ENCRYPTED_PREFIX.len()..];
    let (nonce_b64, ciphertext_b64) = payload
        .split_once('.')
        .ok_or_else(|| "Invalid encrypted cache payload".to_string())?;

    let nonce_bytes = URL_SAFE_NO_PAD
        .decode(nonce_b64)
        .map_err(|_| "Invalid encrypted cache nonce".to_string())?;
    if nonce_bytes.len() != 12 {
        return Err("Invalid encrypted cache nonce length".to_string());
    }

    let ciphertext = URL_SAFE_NO_PAD
        .decode(ciphertext_b64)
        .map_err(|_| "Invalid encrypted cache ciphertext".to_string())?;

    let key = derive_cache_key(cache_seed);
    let cipher = Aes256Gcm::new_from_slice(&key).map_err(|error| error.to_string())?;
    let plaintext = cipher
        .decrypt(Nonce::from_slice(&nonce_bytes), ciphertext.as_ref())
        .map_err(|_| "Corrupted encrypted cache payload".to_string())?;

    String::from_utf8(plaintext).map_err(|_| "Invalid UTF-8 in decrypted cache payload".to_string())
}

fn cache_db_path(app: &AppHandle) -> Result<PathBuf, String> {
    let mut directory = app.path().app_data_dir().map_err(|error| error.to_string())?;
    fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
    directory.push("exam_snapshots.sqlite3");
    Ok(directory)
}

fn open_cache(app: &AppHandle) -> Result<Connection, String> {
    let connection = Connection::open(cache_db_path(app)?).map_err(|error| error.to_string())?;
    connection
        .execute_batch(
            r#"
            CREATE TABLE IF NOT EXISTS snapshot_cache (
                session_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                version INTEGER NOT NULL,
                saved_at TEXT NOT NULL,
                PRIMARY KEY (session_id, question_id)
            );

            CREATE TABLE IF NOT EXISTS hydrate_cache (
                session_id INTEGER PRIMARY KEY,
                payload_json TEXT NOT NULL,
                saved_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pending_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                synced INTEGER NOT NULL DEFAULT 0,
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            "#,
        )
        .map_err(|error| error.to_string())?;

    Ok(connection)
}

fn apply_local_snapshots(
    connection: &Connection,
    session_id: i64,
    cache_seed: &str,
    payload: &mut Value,
) -> Result<(), String> {
    let mut statement = connection
        .prepare(
            r#"
            SELECT question_id, code, version, saved_at
            FROM snapshot_cache
            WHERE session_id = ?1
            "#,
        )
        .map_err(|error| error.to_string())?;

    let rows = statement
        .query_map(params![session_id], |row| {
            Ok(SnapshotCacheEntry {
                session_id,
                question_id: row.get(0)?,
                code: row.get(1)?,
                version: row.get(2)?,
                saved_at: row.get(3)?,
            })
        })
        .map_err(|error| error.to_string())?;

    let snapshots: Vec<SnapshotCacheEntry> = rows
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())?;

    if let Some(questions) = payload.get_mut("questions").and_then(Value::as_array_mut) {
        for question in questions.iter_mut() {
            let Some(question_id) = question.get("question_id").and_then(Value::as_i64) else {
                continue;
            };

            if let Some(snapshot) = snapshots.iter().find(|entry| entry.question_id == question_id) {
                if let Some(object) = question.as_object_mut() {
                    let decrypted_code = decrypt_string(cache_seed, &snapshot.code)?;
                    object.insert(
                        "snapshot".to_string(),
                        serde_json::json!({
                            "code": decrypted_code,
                            "version": snapshot.version,
                            "saved_at": snapshot.saved_at,
                        }),
                    );
                }
            }
        }
    }

    Ok(())
}

#[tauri::command]
pub fn cache_snapshot(
    app: AppHandle,
    cache_seed: String,
    session_id: i64,
    question_id: i64,
    code: String,
    version: i64,
    saved_at: String,
) -> Result<(), String> {
    let connection = open_cache(&app)?;
    let encrypted_code = encrypt_string(&cache_seed, &code)?;
    connection
        .execute(
            r#"
            INSERT INTO snapshot_cache (session_id, question_id, code, version, saved_at)
            VALUES (?1, ?2, ?3, ?4, ?5)
            ON CONFLICT(session_id, question_id) DO UPDATE SET
                code = excluded.code,
                version = excluded.version,
                saved_at = excluded.saved_at
            "#,
            params![session_id, question_id, encrypted_code, version, saved_at],
        )
        .map_err(|error| error.to_string())?;

    Ok(())
}

#[tauri::command]
pub fn cache_hydrate_payload(
    app: AppHandle,
    cache_seed: String,
    session_id: i64,
    payload_json: String,
) -> Result<(), String> {
    let connection = open_cache(&app)?;
    let encrypted_payload = encrypt_string(&cache_seed, &payload_json)?;
    connection
        .execute(
            r#"
            INSERT INTO hydrate_cache (session_id, payload_json, saved_at)
            VALUES (?1, ?2, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                payload_json = excluded.payload_json,
                saved_at = excluded.saved_at
            "#,
            params![session_id, encrypted_payload],
        )
        .map_err(|error| error.to_string())?;

    Ok(())
}

#[tauri::command]
pub fn load_cached_hydrate_payload(
    app: AppHandle,
    cache_seed: String,
    session_id: i64,
) -> Result<Option<String>, String> {
    let connection = open_cache(&app)?;
    let payload_json = connection
        .query_row(
            r#"
            SELECT payload_json
            FROM hydrate_cache
            WHERE session_id = ?1
            "#,
            params![session_id],
            |row| row.get::<_, String>(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;

    let Some(payload_json) = payload_json else {
        return Ok(None);
    };

    let decrypted_payload_json = decrypt_string(&cache_seed, &payload_json)?;
    let mut payload: Value = serde_json::from_str(&decrypted_payload_json).map_err(|error| error.to_string())?;
    apply_local_snapshots(&connection, session_id, &cache_seed, &mut payload)?;

    serde_json::to_string(&payload)
        .map(Some)
        .map_err(|error| error.to_string())
}

#[tauri::command]
pub fn queue_pending_submission(
    app: AppHandle,
    cache_seed: String,
    session_id: i64,
    question_id: i64,
    payload_json: String,
) -> Result<i64, String> {
    let connection = open_cache(&app)?;
    let encrypted_payload = encrypt_string(&cache_seed, &payload_json)?;
    connection
        .execute(
            r#"
            INSERT INTO pending_submissions (session_id, question_id, payload, synced, retry_count, created_at)
            VALUES (?1, ?2, ?3, 0, 0, datetime('now'))
            "#,
            params![session_id, question_id, encrypted_payload],
        )
        .map_err(|error| error.to_string())?;

    Ok(connection.last_insert_rowid())
}

#[tauri::command]
pub fn list_pending_submissions(app: AppHandle, cache_seed: String) -> Result<Vec<PendingSubmissionEntry>, String> {
    let connection = open_cache(&app)?;
    let mut statement = connection
        .prepare(
            r#"
            SELECT id, session_id, question_id, payload, synced, retry_count, created_at
            FROM pending_submissions
            WHERE synced = 0
            ORDER BY created_at ASC, id ASC
            "#,
        )
        .map_err(|error| error.to_string())?;

    let rows = statement
        .query_map([], |row| {
            Ok(PendingSubmissionEntry {
                id: row.get(0)?,
                session_id: row.get(1)?,
                question_id: row.get(2)?,
                payload: row.get(3)?,
                synced: row.get::<_, i64>(4)? != 0,
                retry_count: row.get(5)?,
                created_at: row.get(6)?,
            })
        })
        .map_err(|error| error.to_string())?;

    let entries = rows
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())?;

    entries
        .into_iter()
        .map(|entry| {
            let payload = decrypt_string(&cache_seed, &entry.payload)?;
            Ok(PendingSubmissionEntry { payload, ..entry })
        })
        .collect::<Result<Vec<_>, String>>()
}

#[tauri::command]
pub fn increment_pending_submission_retry(app: AppHandle, id: i64) -> Result<(), String> {
    let connection = open_cache(&app)?;
    connection
        .execute(
            r#"
            UPDATE pending_submissions
            SET retry_count = retry_count + 1
            WHERE id = ?1
            "#,
            params![id],
        )
        .map_err(|error| error.to_string())?;

    Ok(())
}

#[tauri::command]
pub fn mark_pending_submission_synced(app: AppHandle, id: i64) -> Result<(), String> {
    let connection = open_cache(&app)?;
    connection
        .execute(
            r#"
            UPDATE pending_submissions
            SET synced = 1
            WHERE id = ?1
            "#,
            params![id],
        )
        .map_err(|error| error.to_string())?;

    Ok(())
}