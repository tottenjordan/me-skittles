#!/usr/bin/env python3
"""Check if browser-use is installed and install if missing."""
import subprocess
import sys

def check_and_install():
    """Check if browser-use is installed, install if not."""
    try:
        import browser_use
        print("✓ browser-use is already installed")
        return True
    except ImportError:
        print("browser-use not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "browser-use"])
            print("✓ browser-use installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install browser-use: {e}")
            return False

if __name__ == "__main__":
    success = check_and_install()
    sys.exit(0 if success else 1)
