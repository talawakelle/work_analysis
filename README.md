# Estate Workforce Intelligence

A rebuild of your estate analytics system with:

- **Backend:** FastAPI + SQLAlchemy
- **Frontend:** React + TypeScript + Vite + Tailwind
- **Database:** SQLite for local run, PostgreSQL-ready later
- **Data source:** Excel workbook with one sheet per estate, or CSV files split by `Plantation`
- **UX logic:** 2 main buttons only

## What this build matches from your project

### Filters
- Estate
- Date range

### Main screens
- Work Analysis
- Employee Detail

### Work Analysis logic
- Top / Bottom toggle
- Clickable boxes:
  - Workers
  - Kilos
  - Days
- 1 value box
- **Auto run**, no run button

### Employee Detail logic
- employee search
- work code + long job name
- work type summary
- daily records
- calendar with color rules

### Color rules included
- Plucker day with **1.0** hour = **green**
- Plucker day with **0.5** hour = **red**
- **Registered** worker result row = **light green**
- **Cash** worker result row = **red**

---

## Data model

### Main tables
- `estates`
- `employees`
- `work_records`
- `job_codes`
- `import_batches`

### Estate rule
The Excel workbook is imported like this:
- **sheet name = Estate**
- `Division` stays inside each work record

That matches your requirement:
- only Estate filter
- Division stays inside data

---

## Folder structure

```text
estate-workforce-platform/
  backend/
  frontend/
  backend/data/job_codes_seed.csv
  .env.example
  README.md
```

---

## Backend setup (Windows PowerShell)

Use **Python 3.12**.

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item ..\.env.example .env
python -m uvicorn app.main:app --reload
```

Backend:
- `http://localhost:8000`
- `http://localhost:8000/docs`

---

## Import your Excel workbook

Open a second PowerShell window:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.utils.import_workbook "C:\path\to\Labour Attendance TTEL February 2026.xlsx" --label 2026-full
```

Or upload from the frontend import panel.

CSV imports supported too. The importer accepts files like `KVPLHG20260201.csv` and creates/separates estates using the `Plantation` column automatically.

---

## Frontend setup

Open a third PowerShell window:

```powershell
cd frontend
npm install
Copy-Item ..\.env.example .env
npm run dev
```

Frontend:
- `http://localhost:5173`

---

## APIs included

### Meta
- `GET /api/v1/meta/filters`

### Dashboard
- `GET /api/v1/analytics/dashboard`

### Work Analysis
- `GET /api/v1/analytics/work-analysis`

Params:
- `estate`
- `start_date`
- `end_date`
- `direction=top|bottom`
- `metric=workers|kilos|days`
- `value`

### Employee Search
- `GET /api/v1/analytics/employees/search`

### Employee Detail
- `GET /api/v1/analytics/employees/{employee_id}/detail`

### Import
- `GET /api/v1/imports`
- `POST /api/v1/imports/upload`

---

## Job code long names

A seed CSV is included:
- `backend/data/job_codes_seed.csv`

It contains:
- mappings extracted from your job list PDF where possible
- safe defaults like `Plucker = Plucking`

If some codes still show only the short code, add them to:
- `backend/data/job_codes_seed.csv`

Then restart backend and re-import data if you want the long names stored on records.

---

## Notes

- This build is designed for **responsive desktop + mobile**
- Local run uses **SQLite**
- Production can move to PostgreSQL later
- The app now includes its own login screen for estate users and one admin upload account
- Admin account: `ADMIN` / `admin123`
- Estate users only see their own estate after login
- Uploads are validated before import and rejected if required columns are missing
- Main UX stays simple: **2 buttons only**



## Upgrade notes applied

This package contained local build artifacts that should **not** be committed:
- `frontend/node_modules`
- `backend/.venv`
- `backend/estate_workforce.db`

These are environment-specific and can break installs on another machine or OS.

### Recommended cleanup before running

```bash
# frontend
cd frontend
rm -rf node_modules package-lock.json
npm install

# backend
cd ../backend
rm -rf .venv
python -m venv .venv
```

### What was upgraded in this pass

- Added a root `.gitignore`
- Modernized FastAPI startup to use `lifespan` instead of deprecated startup events
- Added frontend `typecheck`, `clean`, and `reinstall` scripts
- Made Vite dev server bind to `0.0.0.0`
- Expanded `/health` to return the app version

### Why the frontend build failed from the uploaded zip

The included `node_modules` folder was installed for a different environment. Rollup tried to load a native package that was not present for this Linux runtime:
- `@rollup/rollup-linux-x64-gnu`

Reinstalling dependencies on the target machine fixes that.



## Multi-estate upgrade added

This build now supports **many estates from one workbook** and **user-to-estate dataset locking**.

### What changed

- Excel import now treats **sheet name as Estate**
- `Plantation` stays inside each row as row metadata
- One workbook can import many estates correctly
- Signed-in users can be mapped to a single estate dataset
- Admin users can see all accessible estates and upload files
- Standard users are automatically locked to their estate after login

### How login mapping works

Authentication is still expected to happen in your **other login page**.

That page should pass the authenticated username to this app using either:

- request header: `X-Auth-User`
- or query string: `?username=logie`

The backend then matches that username to an estate using:

- `backend/data/user_estate_access.json`

### Example mapping file

A demo mapping file is included for the uploaded workbook. Replace it with your real 60+ usernames.

```json
{
  "admins": [
    { "username": "admin", "can_upload": true }
  ],
  "users": [
    { "username": "logie", "estate": "Logie" },
    { "username": "somerset", "estate": "Somerset" }
  ]
}
```

### Important note about your uploaded workbook

The workbook you uploaded contains **16 estate sheets**, not 60.  
The system now supports more than 16 estates, but the bundled sample data only includes the estates present in that file.

### Quick local test

Open the frontend with a username query, for example:

```text
http://localhost:5173?username=logie
```

That user will be locked to the `Logie` estate using the sample mapping file above.


## Estate access mapping included

This package now includes the estate username mapping from the uploaded access list.

Files:
- `backend/data/user_estate_access.json` → used by the API to map **username -> estate**
- `backend/data/estate_credentials_reference.json` → reference copy of the supplied credentials, **not used for login**

### How dataset selection works

The external login page should pass the authenticated username to this app using one of these methods:
- query string: `?username=TTEL@LG`
- request header: `X-Auth-User: TTEL@LG`
- browser storage values such as `authUser`, `currentUser`, `username`, or JSON auth payloads

When a username is matched, the app automatically locks the user to that estate dataset.

### Access mode

- `ACCESS_STRICT_MODE=true` is recommended for production.
- In strict mode, users without a valid mapped username will not see any estate data.

### Current bundled data

- Access mapping file contains **55 estate accounts**
- Bundled SQLite database now contains **55 estate records** so all configured estates can appear in the app
- Imported work records currently exist for **16 estates** from the uploaded TTEL workbook
- The remaining configured estates are ready placeholders and can be loaded later with the same shared headers


## Estate login flow

This build now includes an in-app login screen.

- User enters estate **username** and **password**
- Backend validates the credentials from `backend/data/estate_credentials_reference.json`
- After login, the app resolves the mapped estate from `backend/data/user_estate_access.json`
- Non-admin users are locked to their estate only

## Dataset status

This package now includes TTEL attendance data for:

- `2026-01`
- `2026-02`

The database keeps the month correctly, so when the user selects **January 2026** they see only January data for their estate, and when they select **February 2026** they see only February data.

## Work code and work name

The employee detail screen now shows **Work Code** and **Work Name** separately.

- Work name does not repeat the same work code
- Job code seed data was expanded using `Olax Job List.pdf`


## Included bundled data update

This package now includes additional HPL estate data loaded into the bundled SQLite database with workbook-month normalization enabled for ambiguous row dates.

Added HPL estates/months:
- Neuchatel — 2026-02
- Halwatura — 2026-02
- Fairlawn — 2026-02 and 2026-03
- Gouravilla — 2026-03

Importer updates:
- HPL filename-to-estate matching for single-sheet workbooks like `HPL_Neuchatel.xlsx`
- Header alias support for `Work_-Hour` and misnamed `Employee_Name.1` date columns
- Period detection fallback from workbook row dates when the filename/header does not include the month


## Admin Center added

The latest upgrade adds an **Admin Center** visible only to `ADMIN`.

### Admin Center includes
- data freshness widgets
- plantation coverage table
- dataset validation before import
- validate-only and validate-plus-import actions
- access document upload
- recent import history
- audit trail for logins, validations, uploads, and access-document changes

## Employee month switch added

The employee detail screen now includes **Previous month** and **Next month** buttons for the selected employee, so HR or management can move through months quickly without re-searching the employee.

## PostgreSQL deployment on VPS

The app already supports PostgreSQL through `DATABASE_URL`.

### Example `.env` for VPS

```env
DATABASE_URL=postgresql+psycopg://estate_user:estate_password@localhost:5432/estate_workforce
BACKEND_CORS_ORIGINS=http://your-vps-domain:5173,http://your-vps-domain
VITE_API_BASE_URL=http://your-vps-domain:8000/api/v1
```

### Run with PostgreSQL
1. Start PostgreSQL on the VPS
2. create the database `estate_workforce`
3. set `DATABASE_URL` in `backend/.env`
4. start the backend
5. either re-upload all datasets through `ADMIN`, or migrate the local SQLite DB

### Migration script
A helper script is included:

```powershell
cd backend
python scripts/migrate_sqlite_to_postgres.py --postgres-url "postgresql+psycopg://estate_user:estate_password@localhost:5432/estate_workforce" --truncate-first
```

If you keep SQLite for local work and PostgreSQL for the VPS, the same frontend can continue without changes as long as `VITE_API_BASE_URL` points to the VPS backend.
