#!/usr/bin/env python3
"""
Launcher for the 7taps Analytics Streamlit Chat Interface
"""

import subprocess
import sys
import os

def main():
    """Launch the Streamlit app"""
    print("🧠 Starting Seven Analytics Chat Interface...")
    print("📊 Opening Streamlit app...")
    
    # Run streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "streamlit_app.py",
        "--server.port", "8501",
        "--server.address", "localhost",
        "--browser.gatherUsageStats", "false"
    ])

if __name__ == "__main__":
    main()
