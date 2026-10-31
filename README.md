# Drone Forensics & Digital Incident Investigation System

Phase 1 provides the React/Vite investigation workspace and isolated demo mode. Phase 2 uses Flask, SQLAlchemy, and MySQL for persistent case management. It shares the configured `drone_forensics.cases` table with the existing Flask application in `backend/app.py`. A MySQL-backed login protects the Phase 2 case API; passwords are stored as hashes.

## Prepare MySQL

Open the MySQL command line from PowerShell, then load the setup script (it creates the database and creates the table only if it is missing):

```powershell
mysql -u root -p
```

At the `mysql>` prompt run:

```sql
SOURCE C:/Users/rango/OneDrive/Desktop/MD-DRONE/MD-DRONE/MD-DRONE/backend/sql/mysql_setup.sql;
```

Enter your MySQL password when prompted. In the MySQL prompt you can inspect and edit the same case records the website uses:

```sql
USE drone_forensics;
SHOW TABLES;
DESCRIBE cases;
SELECT * FROM cases ORDER BY created_at DESC;
```

To add the optional restricted app account, set a strong password in `backend/sql/mysql_setup.sql`, uncomment the account statements, and run the setup script. Otherwise, configure the MySQL account you already use.

## Run on Windows

Use Python 3.10+ and Node.js 20.19+ or 22.12+. In the first PowerShell terminal, from the project root:

```powershell
Set-Location "C:\Users\rango\OneDrive\Desktop\MD-DRONE\MD-DRONE\MD-DRONE"
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
$env:DB_HOST = "localhost"
$env:DB_PORT = "3306"
$env:DB_USER = "root"
$mysqlSecurePassword = Read-Host "MySQL password" -AsSecureString
$env:DB_PASSWORD = (New-Object System.Net.NetworkCredential("", $mysqlSecurePassword)).Password
$env:DB_NAME = "drone_forensics"
if (-not $env:FLASK_SECRET_KEY) { $env:FLASK_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))" }
python -m backend.mysql_app
```

The API runs on `http://127.0.0.1:5001`. In a second PowerShell terminal:

```powershell
Set-Location "C:\Users\rango\OneDrive\Desktop\MD-DRONE\MD-DRONE\MD-DRONE\frontend"
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`. Vite forwards `/api` requests to the MySQL-backed API. The legacy Flask application continues to use port 5000.

Use **Register an investigator account** on the website to create the first account; registration requires a username and a password of at least 12 characters, then signs you in. Passwords are stored as hashes. The optional `python -m backend.create_user` command can also create accounts from the configured backend terminal. Keep `FLASK_SECRET_KEY` unchanged while the backend is running so browser sessions remain valid. The API session lasts up to eight hours; use the Sign out control in the sidebar to end it.

On startup, the API creates the `cases` table if it is missing. When the existing table is present, it adds the Phase 2 `investigation_date` and `updated_at` columns if needed and fills them for existing rows; it does not drop or replace case records.

## Phase 2 case API

- `GET /api/health`
- `GET /api/auth/session`
- `POST /api/auth/login`
- `POST /api/auth/register`
- `POST /api/auth/logout`
- `GET /api/cases?q=...&status=...`
- `POST /api/cases`
- `GET /api/cases/<case_id>`
- `PUT /api/cases/<case_id>`
- `DELETE /api/cases/<case_id>`
- `POST /api/flight-logs/convert-bin` (authenticated multipart upload, field name `file`)

Case fields: `case_number`, `case_title`, `examiner_name`, `investigation_date` (`YYYY-MM-DD`), `description`, and `status` (`Open`, `In Progress`, `Review`, or `Closed`). Demo records are synthetic and are never copied into MySQL. The previous generated SQLite file, if present, is left untouched and is no longer used by the application.

## BIN flight-log conversion

The Evidence Acquisition page accepts ArduPilot `.BIN` logs up to 1 GB and uses the existing `bin_file_converter.py` / pymavlink parser. It generates the per-message CSV files, `all_flight_logs.txt`, `all_flight_logs.jsonl`, and `forensic_summary.json` as separate files. The original upload is processed from a temporary server folder and is not modified. The API response also reports the source SHA-256 and decoded record counts.

On supported browsers such as current Microsoft Edge, **Convert and save beside BIN** asks you to choose the folder containing the original BIN and writes the converted files directly into a timestamped subfolder there. The browser does not expose the original file's absolute folder to the website, so you must select that folder in the picker. Other browsers provide individual download links for the converted files. Temporary server outputs expire after one hour and are removed earlier when direct saving completes.

The rest of evidence acquisition, AutopsyBridge import, hash verification, and remaining forensic modules are planned for later phases. No `demo2.mp4`, `server.py`, or `AutopsyBridge.py` was present when the workspace was inspected.
