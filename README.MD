# Zola POS System: User & Deployment Guide

This guide provides a comprehensive walkthrough for setting up, configuring, and operating the Zola POS system. This system is designed for local deployment using the project structure shown in **image_34e2be.png**.

---

## 1. System Prerequisites

Before installation, ensure your environment meets the following requirements:

* **Operating System**: Windows 10 or 11.
* **Python**: Version 3.9 or higher installed and added to your System PATH.
* **Permissions**: Read/Write access to the `pos_system_complete` folder.
* **Hardware**: A standard PC; thermal receipt printer connectivity (optional).

---

## 2. Installation & Environment Setup

To get the application running, you must set up a Python virtual environment to isolate the application's dependencies.

### Step 1: Prepare the Folder

Ensure your root directory matches the structure displayed in **image_34e2be.png**. All commands below should be executed from the `pos_system_complete` folder.

### Step 2: Install Required Packages

The system relies on specific libraries. Create or open the `requirements.txt` file (shown in **image_34e2be.png**) and add the following lines:

```text
PySide6
SQLAlchemy
bcrypt
alembic

```

Run the following command in your terminal/command prompt to install these packages:

```bash
pip install -r requirements.txt

```

---

## 3. Database & Admin Initialization

The system requires an initialized database and an initial administrator account. The file `seed_admin.py` (located in the root folder per **image_34e2be.png**) handles this automatically.

### Executing the Seed Script

This script performs three critical tasks:

1. Creates the SQLite database tables (if they do not exist).
2. Populates default system roles (ADMIN, MANAGE_STOCK, CASHIER).
3. Creates the default "System Administrator" account.

**Run this command:**

```bash
python seed_admin.py

```

**Default Credentials:**

* **Username**: `admin`
* **Default PIN**: `1234`
*(Note: It is highly recommended to change this PIN immediately after your first login.)*

---

## 4. User Guide: Operating the System

Once the database is initialized, you can launch the application by running `main.py`.

### A. The POS Terminal (Sales Tab)

This is the primary interface for daily operations.

* **Search for Products**: Use the "Search / Add Item" input. The system uses a type-ahead search to match names or barcodes.
* **Quick Scan**: If you have a barcode scanner, click the "Barcode Quick Scan" input, scan the item, and it will be added to the cart automatically.
* **Modifying Cart**: Double-click the "Selling Price" or "Quantity" cells in the active cart table to make manual adjustments (e.g., applying a discount or changing quantity).
* **Checkout**: Once the items are listed, click **"Finalize Terminal Receipt"**. This will open the Payment Processing Dialog where you can split payments across cash, mobile money, or bank transfer.

### B. Receipt Registry

Use this tab to review past transactions.

* **Filtering**: Type in the search box to filter by invoice number or customer name.
* **Inspection**: Double-click any receipt row to open the `ReceiptDetailsDialog`.
* **Printing**: In the details dialog, click **"Print Thermal Receipt"** to trigger a print job.

### C. Sales & Payments History

* **Sales List**: A granular view of every item sold across all receipts. Useful for auditing specific item movement.
* **Payments List**: A ledger showing all payment transactions, including payment methods used and change returned.

---

## 5. Troubleshooting Common Issues

| Issue | Resolution |
| --- | --- |
| **"Module Not Found" Error** | Ensure you ran `pip install -r requirements.txt` within your active virtual environment. |
| **Database is Empty** | Ensure you ran `python seed_admin.py` before launching the app. |
| **Printer Not Responding** | Verify the printer is connected to your Windows system and set as the default printer. |
| **Permission Denied** | Ensure the `pos_system_complete` folder is not set to "Read-only" mode. |

---

Would you like me to create a specific `requirements.txt` file content based on the project modules identified in your directory tree?