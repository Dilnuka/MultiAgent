#!/usr/bin/env python3
"""
Quick test for Enhanced AI Risk Assessment System
Tests core functionality without complex UI components.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_basic_functionality():
    """Test basic functionality without UI components."""
    print("Testing Enhanced AI Risk Assessment System")
    print("=" * 50)
    
    try:
        # Test theme function
        from ai_latest_development.enhanced_ui_app import _get_risk_theme
        
        print("Testing UI Themes...")
        for risk_level in ["HIGH", "MEDIUM", "LOW"]:
            theme = _get_risk_theme(risk_level)
            print(f"{risk_level}: {theme['color']} - {theme['title']}")
        
        print("\nTesting Crew Configuration...")
        from ai_latest_development.crew import AiLatestDevelopment
        
        crew_instance = AiLatestDevelopment()
        
        # Check if new task exists
        if hasattr(crew_instance, 'scenario_risk_classification_task'):
            print("scenario_risk_classification_task found")
        else:
            print("scenario_risk_classification_task not found")
        
        print("\nAll basic tests completed!")
        print("\nReady to run the enhanced UI!")
        print("   Run: python run_enhanced_ui.py")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running from the correct directory and dependencies are installed.")
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    test_basic_functionality()
