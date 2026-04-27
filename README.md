<div align="center">
  <img src="./icon.svg" width="150" alt="Shreddem Icon" />
  <h1>Shreddem</h1>
</div>

Shreddem is a high-performance Gmail management tool designed for bulk email cleanup. It uses IMAP to fetch headers into a local SQLite cache, allowing you to search, filter, and mass-delete thousands of emails instantly.

![Shreddem Dashboard](https://via.placeholder.com/800x450?text=Placeholder:+Dashboard+View)
*The main dashboard provides a paginated view of all your email headers with real-time fetch progress.*

## Features

- **Blazing Fast**: Uses parallel IMAP workers to fetch headers.
- **Group by Sender**: Instantly see who is filling up your inbox and delete their emails in bulk.
- **Local Cache**: Once fetched, searching and filtering happen locally on a SQLite database.
- **Safe Deletion**: Emails are moved to the Gmail Trash folder rather than being permanently deleted immediately.
- **Modern Stack**: Built with FastAPI (Python), Vue 3, Pinia, and Vite.

![Group by Sender](https://via.placeholder.com/800x450?text=Placeholder:+Group+by+Sender+View)
*The Sender view groups emails by address, showing unread counts and providing bulk delete actions.*

## Quick Start (Fresh Machine)

Shreddem includes a `Makefile` to automate the entire setup.

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Gmail App Password**: You must [generate an App Password](https://myaccount.google.com/apppasswords) from your Google Account settings (requires 2-Step Verification).

### Bootstrap and Run
Simply run the following command in your terminal for a one-step setup:

```bash
make bootstrap
```

Alternatively, you can run the steps individually in this precise order:
1. `make install` (installs dependencies)
2. `make build` (prepares the frontend)
3. `make run` (starts the server)

This will:
1. Verify your Python and Node versions.
2. Create a virtual environment and install dependencies.
3. Build the frontend production assets.
4. Start the server on **http://127.0.0.1:17811**.

## Usage Guide

### Local Development
To run the backend and frontend separately with hot-reloading:
```bash
make dev
```
- **Backend**: http://127.0.0.1:17811
- **Frontend**: http://localhost:18710

### Docker Support
If you prefer running with Docker:
```bash
# Build and start in one go
make docker

# Or separately
make docker-build
make docker-up
```

### Port Overrides
If the default ports are occupied, you can override them easily:
```bash
BACKEND_PORT=9000 make run
FRONTEND_PORT=4000 make dev
```

## Management Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies (venv + npm) |
| `make build` | Build frontend and deploy to backend static folder |
| `make run` | Run the production-ready server |
| `make test` | Run backend (pytest) and frontend (vitest) tests |
| `make clean` | Remove venv, node_modules, and build artifacts |

## Architecture

- **Backend**: FastAPI handles IMAP connections, background tasks, and SQLite persistence.
- **Frontend**: Vue 3 SPA using Pinia for state management and Axios for API communication.
- **Database**: SQLite manages the local email cache (`~/.config/shreddem/emails.db`).

## Security Note
Shreddem never stores your Gmail password. It requires a Google-generated **App Password**. The session is stored locally in your home directory config folder and is cleared when you log out.
