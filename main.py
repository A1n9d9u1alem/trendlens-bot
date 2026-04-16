"""
TrendLens Bot - Main Entry Point
Uses modular architecture from bot package
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import TrendLensBot


def main():
    """Main entry point for TrendLens Bot"""
    print("=" * 50)
    print("TrendLens AI Bot - Modular Architecture v2.0")
    print("=" * 50)
    print()
    
    # Initialize and run bot
    bot = TrendLensBot()
    
    # Check if webhook mode
    use_webhook = os.getenv('WEBHOOK_URL') is not None
    
    if use_webhook:
        print("Mode: Webhook (Production)")
    else:
        print("Mode: Polling (Development)")
    
    print()
    print("Starting bot...")
    print()
    
    bot.run(use_webhook=use_webhook)


if __name__ == '__main__':
    main()
