## Application Architecture

**PUCS** is a web-based radio communication management system designed for amateur radio operators to manage pile-up communications during contests and DX operations. The system consists of a distributed architecture with components running on both commercial hosting and local PC infrastructure.

## System Components Overview

### 1. Frontend Layer (Commercial Hosting)
**Location:** `frontend/` directory  
**Purpose:** User-facing web interface accessible via commercial web hosting

#### Main Files:
- **`index.html`** (12,976 bytes) - Main application interface with callsign entry positions
- **`frontend.js`** (11,951 bytes) - Client-side JavaScript handling API communication and real-time updates
- **`style.css`** (13,170 bytes) - CSS styling for the PUCS interface with custom theming
- **`api.php`** (2,013 bytes) - API proxy server forwarding requests to backend

#### API Proxy Function:
```php
$backend_host = '62…..136';
$backend_port = '5000';
$backend_url = "http://{$backend_host}:{$backend_port}";
```
The `api.php` acts as a bridge between the frontend and the backend PC, handling CORS and request forwarding.

### 2. Backend Layer (Local PC)
**Location:** Root directory  
**Purpose:** Main application server running Flask with SQLite database

#### Core Backend:
- **`backend_pc.py`** (94,767 bytes) - Primary Flask application server
  - Flask web framework with SQLAlchemy ORM
  - Flask-SocketIO for real-time communication
  - CORS enabled for frontend communication
  - SQLite database integration
  - Admin authentication system
  - Excel export functionality

#### Backend Components:
- **Database Models:**
  - `Config` - System configuration (operator name, frequency)
  - `CallsignEntry` - Individual callsign entries with position, QTH, and comments
  - `Admin` - Administrator user management

- **API Endpoints:**
  - RESTful API for CRUD operations on callsign entries
  - SocketIO events for real-time updates
  - Admin authentication and session management
  - Data export to Excel format

### 3. Background Service (Local PC)
**Location:** Root directory  
**Purpose:** Automated logbook verification service

- **`qrz_logbook_checker.py`** (20,966 bytes) - QRZ.com integration service
  - Runs as background thread checking every 60 seconds
  - Retrieves QRZ logbook data using API credentials
  - Automatically removes logged callsigns from entry queue
  - Thread-safe database operations

### 4. Database Management (Local PC)
**Location:** `instance/` directory  
**Purpose:** Database operations and maintenance

#### Database Files:
- **`radio_entry.db`** (28,672 bytes) - Main SQLite database file
- **`check_database.py`** (2,118 bytes) - Database structure validation tool
- **`database_migration.py`** (2,807 bytes) - Database schema migration tool

#### Database Schema:
```sql
CREATE TABLE callsign_entry (
    id INTEGER PRIMARY KEY,
    position INTEGER UNIQUE NOT NULL,  -- 1-6 queue positions
    callsign VARCHAR(20) NOT NULL,
    location VARCHAR(100),             -- QTH field
    comment TEXT,                      -- Remarks field
    entered_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Template Layer (Local PC)
**Location:** `templates/` directory  
**Purpose:** HTML templates for server-side rendering
**`admin_dashboard.html`** (32,864 bytes) - Administrative interface template

### 6. Static Assets (Local PC)
**Location:** `static/` directory  
**Purpose:** Static web resources

- **`css/style.css`** (11,825 bytes) - Additional CSS styles
- **`js/main.js`** (10,035 bytes) - Additional JavaScript functionality

## Inter-Component Relationships

### 1. Communication Flow:
```
User Browser → Frontend (Commercial) → api.php → Backend PC (62.131.85.136:5000)
                ↓
         Real-time updates via SocketIO
                ↓
         QRZ Checker Service (Background)
```

### 2. Data Flow:
```
Frontend Form → API Proxy → Flask Backend → SQLite Database
                    ↓
              QRZ Checker → QRZ API → Database Updates
```

### 3. File Dependencies:
```
backend_pc.py
├── Uses: instance/radio_entry.db
├── Loads: static/css/style.css, static/js/main.js
└── Renders: templates/admin_dashboard.html

qrz_logbook_checker.py
├── Reads: instance/radio_entry.db
├── Connects to: QRZ.com API
└── Updates: instance/radio_entry.db

frontend.js
├── Calls: api.php (frontend)
└── Receives: Real-time SocketIO updates
```

## Core Application Functions

### 1. Call Sign Management
- **Entry System:** Operators can add callsigns to 6 available positions (1-6)
- **Position Management:** Each position holds one active callsign
- **Metadata:** Each entry includes QTH (location) and remarks
- **Real-time Updates:** Changes immediately reflected via WebSocket

### 2. QRZ Integration
- **Automatic Verification:** Background service checks QRZ logbook every minute
- **Smart Removal:** Logged callsigns are automatically removed from queue
- **API Integration:** Uses QRZ.com API with stored credentials
- **Error Handling:** Robust error handling for API failures

### 3. Administrative Features
- **Admin Dashboard:** Full administrative interface
- **User Authentication:** Secure admin login system
- **Data Export:** Export functionality to Excel format
- **Database Management:** Built-in migration and validation tools

### 4. Real-time Communication
- **WebSocket Support:** SocketIO for instant updates
- **CORS Handling:** Cross-origin request support
- **Multi-client:** Supports multiple simultaneous users

## System Requirements

### Frontend (Commercial Hosting):
- PHP 7.0+ with cURL extension
- Web server (Apache/Nginx)
- Static file hosting capabilities

### Backend (Local PC):
- Python 3.x with Flask ecosystem
- SQLite database support
- Internet connection for QRZ API access
- Port 5000 accessible from internet

## Deployment Architecture

```
Internet
    ↓
[Commercial Hosting]
├── index.html (Frontend UI)
├── frontend.js (Client Logic)
├── api.php (API Proxy) ←→ 62…..136:5000
    ↓
[Local PC - Home]
├── backend_pc.py (Flask Server)
├── qrz_logbook_checker.py (Background Service)
├── instance/radio_entry.db (SQLite Database)
└── Templates & Static Assets
```

## File Size Analysis

| File | Size | Purpose |
|------|------|---------|
| backend_pc.py | 94.7KB | Main Flask application |
| admin_dashboard.html | 32.9KB | Admin interface template |
| radio_entry.db | 28.7KB | SQLite database |
| qrz_logbook_checker.py | 21.0KB | QRZ integration service |
| frontend/index.html | 13.0KB | Main UI interface |
| frontend/style.css | 13.2KB | Frontend styling |
| frontend/frontend.js | 12.0KB | Client-side JavaScript |

This distributed architecture allows for separation of concerns, with the user interface hosted reliably while the main application logic and data management run on the operator's local infrastructure.
