#!/usr/bin/env python3
"""
Enhanced AI Risk Assessment UI Launcher
Run this script to start the enhanced UI with automatic risk analysis and Pro upgrade flow.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set up environment
os.environ.setdefault('STREAMLIT_SERVER_PORT', '8501')
os.environ.setdefault('STREAMLIT_SERVER_ADDRESS', 'localhost')

if __name__ == "__main__":
    try:
        import streamlit.web.cli as stcli
        
        # Get the path to the enhanced UI app
        app_path = Path(__file__).parent / "src" / "ai_latest_development" / "enhanced_ui_app.py"
        
        print("🚀 Starting Enhanced AI Risk Assessment UI...")
        print(f"📱 App will be available at: http://localhost:8501")
        print("🔍 Features:")
        print("   • Automatic scenario risk analysis")
        print("   • Modern color-coded risk display")
        print("   • Pro upgrade flow with dummy payment")
        print("   • Human specialist contact page")
        print("   • Full comprehensive assessment")
        print("\n" + "="*50)
        
        # Run Streamlit
        sys.argv = [
            "streamlit", 
            "run", 
            str(app_path),
            "--server.port=8501",
            "--server.address=localhost"
        ]
        
        sys.exit(stcli.main())
        
    except ImportError:
        print("❌ Streamlit not found. Please install it with:")
        print("   pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting the application: {e}")
        sys.exit(1)
