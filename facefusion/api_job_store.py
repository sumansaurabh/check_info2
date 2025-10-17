import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from facefusion import logger

DB_PATH = Path(os.getenv("API_DB_PATH", ".api_jobs.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _get_connection() -> Iterable[sqlite3.Connection]:
	conn = sqlite3.connect(DB_PATH, check_same_thread=False)
	conn.row_factory = sqlite3.Row
	try:
		yield conn
		conn.commit()
	except Exception:
		conn.rollback()
		raise
	finally:
		conn.close()


def init_db() -> None:
	with _get_connection() as conn:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS jobs
			(
				job_id TEXT PRIMARY KEY,
				job_type TEXT,
				status TEXT,
				target_path TEXT,
				source_path TEXT,
				output_path TEXT,
				error TEXT,
				created_at TEXT,
				updated_at TEXT
			)
			"""
		)


def _timestamp() -> str:
	return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def create_job(
	job_id: str,
	job_type: str,
	target_path: str,
	source_path: Optional[str],
	output_path: str
) -> None:
	now = _timestamp()
	try:
		with _get_connection() as conn:
			conn.execute(
				"""
				INSERT INTO jobs (job_id, job_type, status, target_path, source_path, output_path, created_at, updated_at)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?)
				""",
				(job_id, job_type, "submitted", target_path, source_path, output_path, now, now)
			)
	except Exception as exc:
		logger.error(f"Failed to create job {job_id}: {exc}", __name__)
		raise


def update_job_status(
	job_id: str,
	status: str,
	output_path: Optional[str] = None,
	error: Optional[str] = None
) -> None:
	now = _timestamp()
	try:
		with _get_connection() as conn:
			conn.execute(
				"""
				UPDATE jobs
				SET status = ?, output_path = COALESCE(?, output_path), error = ?, updated_at = ?
				WHERE job_id = ?
				""",
				(status, output_path, error, now, job_id)
			)
	except Exception as exc:
		logger.error(f"Failed to update job {job_id}: {exc}", __name__)
		raise


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
	with _get_connection() as conn:
		cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
		row = cursor.fetchone()
		if not row:
			return None
		return dict(row)


def list_jobs(limit: int = 50) -> Iterable[Dict[str, Any]]:
	with _get_connection() as conn:
		cursor = conn.execute(
			"""
			SELECT * FROM jobs
			ORDER BY datetime(created_at) DESC
			LIMIT ?
			""",
			(limit,)
		)
		for row in cursor.fetchall():
			yield dict(row)
