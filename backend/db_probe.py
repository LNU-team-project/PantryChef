import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def ensure_project_venv_python() -> None:
    """Re-run this script with backend/.venv python when launched from global Python."""
    if os.getenv("PANTRYCHEF_SKIP_VENV_REEXEC") == "1":
        return

    script_path = Path(__file__).resolve()
    backend_dir = script_path.parent
    if os.name == "nt":
        venv_python = backend_dir / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = backend_dir / ".venv" / "bin" / "python"

    if not venv_python.exists():
        return

    current_python = Path(sys.executable).resolve()
    target_python = venv_python.resolve()
    if current_python == target_python:
        return

    env = os.environ.copy()
    env["PANTRYCHEF_SKIP_VENV_REEXEC"] = "1"
    cmd = [str(target_python), str(script_path), *sys.argv[1:]]
    print(f"Switching interpreter to project venv: {target_python}")
    result = subprocess.run(cmd, env=env)
    raise SystemExit(result.returncode)


ensure_project_venv_python()

import psycopg
from dotenv import load_dotenv


def load_db_config() -> dict:
    load_dotenv()
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "pantry_chef"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "postgres"),
    }


def main() -> None:
    config = load_db_config()
    print(
        f"Connecting to PostgreSQL {config['host']}:{config['port']} "
        f"db={config['dbname']} user={config['user']}"
    )

    try:
        with psycopg.connect(**config) as conn:
            with conn.cursor() as cursor:
                # Dedicated probe table keeps test writes away from your business data.
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.connection_probe (
                        id SERIAL PRIMARY KEY,
                        note TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )

                note = f"probe_insert_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                cursor.execute(
                    """
                    INSERT INTO public.connection_probe (note)
                    VALUES (%s)
                    RETURNING id, note, created_at
                    """,
                    (note,),
                )
                row = cursor.fetchone()

        print("SUCCESS: DB connection and INSERT worked.")
        print(f"Inserted row => id={row[0]}, note={row[1]}, created_at={row[2]}")
    except Exception as exc:
        print("ERROR: DB probe failed.")
        print(f"Details: {exc}")
        print("Check backend/.env values and PostgreSQL status, then run again.")
        raise


if __name__ == "__main__":
    main()

