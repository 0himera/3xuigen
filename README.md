# 3x-ui API Wrapper

A FastAPI application acting as a wrapper around the 3x-ui panel API, primarily designed for managing inbounds and clients, often via an SSH tunnel. It also includes functionality for managing UFW firewall rules on a remote server via SSH.

## Features

- **3x-ui Management:**
    - Get server status and connection diagnostics.
    - List, create, and delete inbounds.
    - Add and remove clients within inbounds.
    - Generate X25519 keypairs for Reality.
- **Remote Firewall Management (UFW via SSH):**
    - Get UFW status and rules.
    - Add and delete UFW rules (by port or rule number).
    - Open and close specific ports.
    - Check the status of a specific port.
- **Reality Key Generation:**
    - Utility endpoint to generate Reality keys.

## Prerequisites

- Python 3.8+
- [Poetry](https://python-poetry.org/) for dependency management.
- Access to a running 3x-ui panel instance.
- SSH access to a remote server (if using the firewall management features).
- `xray` binary available in the system path (optional, used for generating Reality keys via the API, though the client can generate them locally).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd 3xuigen # Or your project directory name
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```
    This will create a virtual environment if one doesn't exist and install all required packages specified in `pyproject.toml`.

## Configuration

1.  **Create a `.env` file:**
    Copy the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Fill in the necessary details for your 3x-ui panel and SSH connection:
    ```dotenv
    # API Server Configuration
    PORT=8000
    ENV=development # Set to "production" for deployment
    # Allowed origins for CORS (comma-separated)
    CORS_ORIGINS=http://localhost:3000,http://localhost:5173

    # 3x-ui Panel API Configuration
    XUI_BASE_URL=http://your-3xui-panel-url:port # e.g., http://localhost:8080 or tunnel URL
    XUI_USERNAME=your_3xui_username
    XUI_PASSWORD=your_3xui_password
    XUI_TIMEOUT=30

    # SSH Configuration (for Firewall Management)
    SSH_HOST=your_remote_server_ip
    SSH_PORT=22
    SSH_USERNAME=your_ssh_username
    SSH_PASSWORD=your_ssh_password
    SSH_TIMEOUT=10
    ```

## Running the API

1.  **Activate the virtual environment (if not already active):**
    ```bash
    poetry shell
    ```

2.  **Start the FastAPI server using the `run.py` script:**
    ```bash
    python run.py
    ```
    Or directly with Uvicorn (auto-reload enabled if `ENV=development`):
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port $(grep PORT .env | cut -d '=' -f2) --reload=$( [[ $(grep ENV .env | cut -d '=' -f2) == "development" ]] && echo "true" || echo "false" )
    ```

    The API will be available at `http://localhost:8000` (or the port specified in `.env`).

## API Documentation

Once the server is running, interactive API documentation is available at:

-   **Swagger UI:** `http://localhost:8000/docs`
-   **ReDoc:** `http://localhost:8000/redoc`

## API Endpoints

### Root

-   `GET /` - Welcome message.

### 3x-ui (`/api/xui`)

-   `GET /status` - Get 3x-ui server status and diagnostics.
-   `GET /connection-test` - Test connection and authentication to the 3x-ui panel.
-   `GET /inbounds` - List all inbounds.
-   `POST /inbounds` - Create a new inbound.
-   `DELETE /inbounds/{inbound_id}` - Delete an inbound by ID.
-   `POST /clients` - Add a client to an existing inbound. Allows setting email, UUID, flow, traffic limit (GB), IP limit, expiration time (ms timestamp), Telegram ID, subscription ID, and enable status.
-   `POST /inbounds/{inbound_id}/clients/{client_uuid}` - Remove a client from an inbound by UUID.
-   `GET /generate-keypair` - Generate a new X25519 keypair (requires `xray` locally or uses fallback).
-   `GET /login-form` - Display an HTML form for manual login testing.
-   `POST /manual-login` - Perform a manual login test using form data.

### Firewall (`/api/firewall`)

*Requires SSH credentials in `.env`*

-   `GET /status` - Get remote UFW firewall status.
-   `GET /rules` - Get a structured list of remote UFW rules.
-   `POST /rules` - Add a firewall rule (allow/deny port/protocol).
-   `DELETE /rules/{rule_number}` - Delete a firewall rule by its number.
-   `POST /ports` - Open a specific port/protocol (uses `add_ufw_rule` internally).
-   `DELETE /ports/{port}` - Close a specific port/protocol (finds and deletes the rule).
-   `GET /ports/{port}` - Check if a specific port/protocol is open in the rules.

### Reality (`/api/reality`)

-   `GET /generate-keys` - Generate Reality key pair and short ID (uses local `xray` or fallback).

## License

MIT 