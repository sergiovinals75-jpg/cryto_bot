import yfinance as yf
import telegram
from telegram import Bot
import schedule
import time
from datetime import datetime, timezone, timedelta
import ta
import pandas as pd
import logging
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token and Chat ID from environment variables (for security)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# List of cryptocurrencies to analyze (Yahoo Finance format)
CRYPTO_LIST = [
    "BTC-USD", "ETH-USD", "ADA-USD", "DOT-USD", "XRP-USD",
    "LTC-USD", "BCH-USD", "LINK-USD", "XLM-USD", "DOGE-USD"
]

# Positive and negative word lists for basic sentiment analysis
POSITIVE_WORDS = ["gain", "rise", "up", "bullish", "surge", "rally", "positive", "growth", "profit", "high", "strong", "buy", "long"]
NEGATIVE_WORDS = ["fall", "drop", "down", "bearish", "crash", "decline", "negative", "loss", "low", "weak", "sell", "short"]

def analyze_sentiment(text):
    """Basic sentiment analysis based on word lists."""
    text_lower = text.lower()
    positive_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    negative_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"

def get_crypto_news(symbol):
    """Fetch latest news for a cryptocurrency from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        if not news:
            return None
        # Get the most recent news item
        latest_news = news[0]
        title = latest_news.get('title', '')
        summary = latest_news.get('summary', '')
        return f"{title} {summary}"
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return None

def calculate_rsi(symbol, period=14):
    """Calculate RSI for a cryptocurrency."""
    try:
        # Download historical data (last 30 days to ensure enough data for RSI)
        data = yf.download(symbol, period="30d", interval="1d")
        if data.empty or len(data) < period:
            return None
        # Calculate RSI
        rsi = ta.momentum.RSIIndicator(data['Close'], window=period)
        rsi_value = rsi.rsi().iloc[-1]
        return rsi_value
    except Exception as e:
        logger.error(f"Error calculating RSI for {symbol}: {e}")
        return None

def generate_signal(symbol):
    """Generate trading signal based on news sentiment and RSI."""
    news_text = get_crypto_news(symbol)
    if not news_text:
        return None
    
    sentiment = analyze_sentiment(news_text)
    if sentiment == "neutral":
        return None
    
    rsi = calculate_rsi(symbol)
    if rsi is None:
        return None
    
    # Determine signal
    if sentiment == "positive" and rsi <= 30:
        signal = "BUY"
    elif sentiment == "negative" and rsi >= 70:
        signal = "SELL"
    else:
        return None
    
    return {
        'symbol': symbol,
        'sentiment': sentiment,
        'rsi': rsi,
        'signal': signal,
        'news': news_text[:200] + "..." if len(news_text) > 200 else news_text
    }

def send_daily_analysis():
    """Function to send daily analysis."""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        messages = []
        
        for symbol in CRYPTO_LIST:
            signal_info = generate_signal(symbol)
            if signal_info:
                msg = (
                    f"🔍 *{signal_info['symbol']}*\n"
                    f"Sentiment: {signal_info['sentiment'].upper()}\n"
                    f"RSI: {signal_info['rsi']:.2f}\n"
                    f"Signal: *{signal_info['signal']}*\n"
                    f"News: {signal_info['news']}\n"
                )
                messages.append(msg)
        
        if messages:
            header = f"📈 *Daily Crypto Analysis* ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})\n\n"
            full_message = header + "\n---\n\n".join(messages)
            bot.send_message(chat_id=CHAT_ID, text=full_message, parse_mode='Markdown')
        else:
            bot.send_message(chat_id=CHAT_ID, text="📊 No significant signals found today.", parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in send_daily_analysis: {e}")
        # Try to send error message to user
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
            bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Error generating analysis: {str(e)}")
        except:
            pass

if __name__ == '__main__':
    send_daily_analysis()