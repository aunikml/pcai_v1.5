# BRAC AI Guide - Deployment Instructions (Ubuntu Server with PostgreSQL)

These instructions will guide you through deploying the BRAC AI Guide application to an Ubuntu server using PostgreSQL for the database.

## Prerequisites

Before you begin, ensure you have the following:

1.  **An Ubuntu Server:** You need access to a running Ubuntu server (version 22.04 LTS recommended). This can be a virtual machine from a cloud provider like Google Cloud, AWS, DigitalOcean, or a physical server.
2.  **SSH Access:** You must be able to connect to the server via SSH.
3.  **Basic Linux Knowledge:** Familiarity with basic Linux commands (e.g., `cd`, `mkdir`, `nano`, `sudo`) is helpful.

## Step 1: Install PostgreSQL

1.  **Connect to your Ubuntu server via SSH:**

    ```bash
    ssh your_user@your_server_ip
    ```

2.  **Update the system's package list and install PostgreSQL:**

    ```bash
    sudo apt update
    sudo apt upgrade -y
    sudo apt install postgresql postgresql-contrib -y
    ```

3.  **Create a database and user for the application:**

    ```bash
    sudo -u postgres psql
    ```

    Inside the `psql` shell, run these commands:

    ```sql
    CREATE DATABASE brac_db;
    CREATE USER brac_user WITH PASSWORD 'your_strong_password';
    GRANT ALL PRIVILEGES ON DATABASE brac_db TO brac_user;
    \q
    ```

    *   Remember to replace `your_strong_password` with a secure password.

## Step 2: Install Dependencies and Configure the Application

1.  **Install essential tools:**

    ```bash
    sudo apt install git python3-pip python3-venv nginx -y
    ```

2.  **Clone the application repository from GitHub:**

    ```bash
    cd ~
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

    *   Replace `https://github.com/your-username/your-repo-name.git` with the actual URL of your GitHub repository.

3.  **Create a Python virtual environment:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

4.  **Install the required Python packages:**

    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure the application by creating a `.env` file:**

    ```bash
    nano .env
    ```

    Add the following lines to the `.env` file, replacing the placeholders with your actual values:

    ```
    DATABASE_URL="postgresql://brac_user:your_strong_password@localhost:5432/brac_db"
    GOOGLE_API_KEY="AIzaSy...your...actual...key...here"
    ```

    Save and exit the file (in `nano`, press `Ctrl+X`, then `Y`, then `Enter`).

6.  **Run the initial database setup:**

    ```bash
    python setup_pg_db.py
    ```

    If you don't have `setup_pg_db.py`, create the file and put the following:

        ```python
        # setup_pg_db.py
        from dotenv import load_dotenv
        from database import setup_database

        load_dotenv()
        print("Setting up the PostgreSQL database...")
        setup_database()
        print("Database setup complete.")
        ```

## Step 3: Configure the Application to Run as a System Service

1.  **Create a systemd service file:**

    ```bash
    sudo nano /etc/systemd/system/brac-app.service
    ```

2.  **Paste the following configuration into the file (replace `your_user` and `your-repo-name`):**

    ```ini
    [Unit]
    Description=BRAC AI Guide Streamlit App
    After=network.target

    [Service]
    User=your_user
    Group=your_user
    WorkingDirectory=/home/your_user/your-repo-name
    ExecStart=/home/your_user/your-repo-name/.venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

    Save and exit the file.

3.  **Enable and start the service:**

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable brac-app.service
    sudo systemctl start brac-app.service
    ```

4.  **Check the service status to ensure it's running:**

    ```bash
    sudo systemctl status brac-app.service
    ```

## Step 4: Configure Nginx as a Reverse Proxy

1.  **Create an Nginx configuration file:**

    ```bash
    sudo nano /etc/nginx/sites-available/brac-app
    ```

2.  **Paste the following configuration into the file (replace `your_domain_or_vm_ip`):**

    ```nginx
    server {
        listen 80;
        server_name your_domain_or_vm_ip;

        location / {
            proxy_pass http://localhost:8501;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
    ```

    Save and exit the file.

3.  **Enable the site and restart Nginx:**

    ```bash
    sudo ln -s /etc/nginx/sites-available/brac-app /etc/nginx/sites-enabled/
    sudo nginx -t # Test the configuration
    sudo systemctl restart nginx
    ```

## Step 5: Secure the Application with HTTPS (Optional but Recommended)

1.  **Install Certbot:**

    ```bash
    sudo apt install certbot python3-certbot-nginx -y
    ```

2.  **Obtain and install an SSL certificate:**

    ```bash
    sudo certbot --nginx -d your_domain_name
    ```

    *   Follow the prompts from Certbot to configure your SSL certificate. Choose to redirect HTTP traffic to HTTPS for better security.

## Accessing the Application

After completing these steps, you should be able to access your BRAC AI Guide application by opening a web browser and navigating to:

*   `http://your_domain_or_vm_ip` (if you haven't configured HTTPS yet)
*   `https://your_domain_name` (if you have configured HTTPS)

## Updating the Application

To update the application with new code:

1.  Connect to your server via SSH.
2.  Navigate to the application directory:

    ```bash
    cd ~/your-repo-name
    ```

3.  Pull the latest changes from GitHub:

    ```bash
    git pull origin main
    ```

4.  If you updated the `requirements.txt` file, install the new dependencies:

    ```bash
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

5.  Restart the application service:

    ```bash
    sudo systemctl restart brac-app.service
    ```