#!/usr/bin/env python3
"""
Launcher script for the Cloudsmith package insights CLI.
This script serves as the entry point for Docker containers.
"""

if __name__ == '__main__':
    import sys
    import os
    
    # Add the package directory to Python path
    package_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, package_dir)
    
    # Import and run the CLI directly from the relative path
    from package_insights.cli import package_insights
    package_insights()
