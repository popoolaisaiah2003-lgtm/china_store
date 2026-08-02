# 🔬 Yan Zhen Peptide — B2B Wholesale Quotation & Research Portal

A high-performance, international B2B wholesale quotation system and administrative portal engineered for precision research peptides, HPLC-certified compounds, and analytical standards.

---

## 🌟 Key Features

- **📊 Unpaginated B2B Wholesale Catalog**: Displays all 170 laboratory research peptides in a high-density, real-time searchable matrix with dynamic sorting and keyword filtering.
- **⚡ Asynchronous Quotation Cart (AJAX)**: Zero-reload, scroll-locked cart management with stackable, queued toast notifications and instant navbar count updates.
- **📲 Consolidated WhatsApp Checkout**: Automatically formats and builds consolidated bulk quotation orders directed straight to the wholesale desk via WhatsApp.
- **🔬 Certificate of Analysis (COA) Repository**: Batch-specific HPLC & Mass Spectrometry analytical report search and PDF download system.
- **📰 Research Journal (Blog CMS)**: Full administrative lifecycle management with Quill.js rich text editor, emoji/utf8mb4 support, preview image handling, and featured placement.
- **🔒 Production-Ready Admin Console**: Secure portal located at `/admin/login` featuring brute-force rate-limiting, session protection, and self-service password updates.
- **🌐 Strict LTR Internationalization**: Supports English, Chinese (中文), Spanish (Español), Arabic (العربية), and French (Français) with guaranteed LTR structural consistency across all locales.
- **🚀 Fully Offline Local Bootstrap 5 Assets**: Zero CDN dependencies for offline reliability and speed.

---

## 🛠️ Tech Stack

- **Backend Framework**: Python 3.14 / Flask
- **Database Layer**: MySQL (MariaDB / XAMPP) with SQLAlchemy ORM & Flask-Migrate
- **Authentication**: Flask-Login with dedicated `Admin` model
- **Form Validation & Security**: Flask-WTF with CSRF Protection
- **Frontend & Aesthetics**: Modern Vanilla CSS Design Tokens & Local Bootstrap 5.3
- **Editor Integration**: Quill.js Rich Text Editor

---

## 🚀 Local Setup Instructions

### Prerequisites
- Python 3.10+
- MySQL / MariaDB (via XAMPP or standalone server)
- Git

### 1. Clone & Setup Virtual Environment
```bash
git clone <your-github-repo-url>
cd antigravity_peptides

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
.venv\Scripts\activate     # On Windows PowerShell
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Configuration (MySQL / XAMPP)
1. Start MySQL from XAMPP Control Panel.
2. Create the database `yan_zhen_peptide` in phpMyAdmin or via MySQL CLI:
   ```sql
   CREATE DATABASE yan_zhen_peptide CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Run database migrations:
   ```bash
   flask db upgrade
   ```

### 4. Run Application
```bash
python starter.py
```
The application will launch locally at:
- **Public Portal**: `http://localhost:8080`
- **Admin Console**: `http://localhost:8080/admin/login`

---

## 🔑 Initial Admin Credentials

| Parameter | Value |
| :--- | :--- |
| **Admin Login URL** | `http://localhost:8080/admin/login` |
| **Default Username** | `isaiah` |
| **Default Email** | `admin@yanzhen.com` |
| **Default Password** | `ChangeMe123!` |

---

## 🖼️ Application Screenshots & Demos

### 1. Wholesale Catalog Matrix
![Wholesale Catalog Matrix](docs/screenshots/catalog.png)
*170 unpaginated products with instant AJAX quotation cart additions.*

### 2. Asynchronous Cart Notifications
![Quotation Toast](docs/screenshots/cart-toast.png)
*Stackable bottom-right toast notifications preserving user scroll position.*

### 3. Secure Admin Management Console
![Admin Panel](docs/screenshots/admin-dashboard.png)
*Full administrative control for products, COAs, blog articles, and settings.*

---

## 📄 License
Commercial License — Proprietary software created for **Yan Zhen Peptide**.
