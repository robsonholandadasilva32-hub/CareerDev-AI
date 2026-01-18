#!/usr/bin/env python3
import os
import smtplib
import socket
import sys
from dotenv import load_dotenv

# Try to load .env from current directory or parent directory
load_dotenv()

def print_header(msg):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")

def print_step(msg):
    print(f"\n[-] {msg}")

def print_success(msg):
    print(f"    [OK] {msg}")

def print_error(msg):
    print(f"    [ERROR] {msg}")

def main():
    print_header("SMTP CONNECTIVITY CHECKER")

    # 1. Load Configuration
    print_step("Loading Configuration...")

    # Try to import settings from app to see what the app sees, if possible
    try:
        sys.path.append(os.getcwd())
        from app.core.config import settings
        smtp_server = settings.SMTP_SERVER
        smtp_port = settings.SMTP_PORT
        smtp_username = settings.SMTP_USERNAME
        smtp_password = settings.SMTP_PASSWORD
        use_tls = settings.SMTP_USE_TLS
        use_starttls = settings.SMTP_USE_STARTTLS

        print_success("Loaded settings via app.core.config")
    except ImportError:
        print_error("Could not import app.core.config. Falling back to raw .env vars.")
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        use_tls = os.getenv("SMTP_USE_TLS", "False").lower() == "true"
        use_starttls = os.getenv("SMTP_USE_STARTTLS", "True").lower() == "true"

    if not smtp_server:
        print_error("SMTP_SERVER is not set!")
        return

    print(f"    Server: {smtp_server}")
    print(f"    Port: {smtp_port}")
    print(f"    User: {smtp_username}")
    print(f"    TLS: {use_tls}")
    print(f"    STARTTLS: {use_starttls}")

    # 2. DNS Resolution
    print_step(f"Checking DNS resolution for {smtp_server}...")
    try:
        ip_address = socket.gethostbyname(smtp_server)
        print_success(f"Resolved to {ip_address}")
    except socket.gaierror as e:
        print_error(f"DNS Resolution Failed: {e}")
        return

    # 3. TCP Connectivity
    print_step(f"Checking TCP connection to {smtp_server}:{smtp_port}...")
    try:
        sock = socket.create_connection((smtp_server, smtp_port), timeout=10)
        sock.close()
        print_success("TCP Connection Established")
    except Exception as e:
        print_error(f"TCP Connection Failed: {e}")
        print_error("This suggests a Firewall or Network Block.")
        return

    # 4. SMTP Handshake & Auth
    print_step("Attempting SMTP Handshake & Authentication...")
    try:
        if use_tls:
             # Implicit TLS (usually port 465)
             print("    Connecting with implicit TLS (SMTP_SSL)...")
             server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        else:
             # Regular connection (usually port 587 or 25)
             print("    Connecting with standard SMTP...")
             server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)

        server.set_debuglevel(1) # Verbose output
        print_success(f"Connected to {smtp_server}")

        server.ehlo()

        if use_starttls:
            if server.has_extn("STARTTLS"):
                print("    Starting TLS (STARTTLS)...")
                server.starttls()
                server.ehlo() # Re-identify after TLS
                print_success("STARTTLS negotiation successful")
            else:
                print_error("Server does not support STARTTLS but it was requested.")

        if smtp_username and smtp_password:
            print("    Attempting login...")
            server.login(smtp_username, smtp_password)
            print_success("Authentication Successful!")
        else:
            print("    Skipping authentication (No username/password provided)")

        server.quit()

    except smtplib.SMTPAuthenticationError as e:
        print_error(f"Authentication Failed: {e}")
    except Exception as e:
        print_error(f"SMTP Error: {e}")

if __name__ == "__main__":
    main()
