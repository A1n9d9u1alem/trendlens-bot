import os
import logging
from telegram.ext import Application
from bot import TrendLensBot
from dotenv import load_dotenv

load_dotenv()

async def setup_webhook(application: Application):
    """Setup webhook for the bot"""
    webhook_url = os.getenv('WEBHOOK_URL')  # e.g., https://yourdomain.com/webhook
    port = int(os.getenv('PORT', 8443))
    
    if webhook_url:
        await application.bot.set_webhook(
            url=f"{webhook_url}/{application.bot.token}",
            allowed_updates=["message", "callback_query", "inline_query"]
        )
        logging.info(f"Webhook set to: {webhook_url}")
    else:
        logging.warning("No WEBHOOK_URL set, using polling mode")

def main():
    logging.basicConfig(level=logging.INFO)
    
    bot = TrendLensBot()
    app = Application.builder().token(bot.token).build()
    
    # Add all handlers from bot
    bot.setup_handlers(app)
    
    # Check if webhook mode
    webhook_url = os.getenv('WEBHOOK_URL')
    port = int(os.getenv('PORT', 8443))
    
    if webhook_url:
        # Webhook mode
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=bot.token,
            webhook_url=f"{webhook_url}/{bot.token}"
        )
    else:
        # Polling mode (fallback)
        app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
