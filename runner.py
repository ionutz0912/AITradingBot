import os
import logging
from dotenv import load_dotenv

from lib import ai, custom_helpers, ForwardTester, BitunixFutures, BitunixError

load_dotenv()

# ===================== CONFIGURATION =====================
RUN_NAME = "run_btc_template_prompt"
CRYPTO = "Bitcoin"
SYMBOL = "BTCUSDT"
LEVERAGE = 1
MARGIN_MODE = "ISOLATION"

# Position Size Configuration
# POSITION_SIZE = "10%"  # Use 10% of capital per trade
POSITION_SIZE = 20  # Use 20 USDT per trade

# Stop Loss Configuration (LIVE TRADING ONLY - not supported in forward testing yet)
STOP_LOSS_PERCENT = 10  # 10% stop-loss from entry price
# STOP_LOSS_PERCENT = None  # Disabled

# Forward Testing Configuration
FORWARD_TESTING_CONFIG = {
    "run_name": RUN_NAME,
    "initial_capital": 10000,
    "fees": 0.0006,  # 0.06% taker fee
}

PROMPT = f"""
You are a cryptocurrency market analyst AI.

Based on your general knowledge of cryptocurrency markets and typical {CRYPTO} behavior patterns,
provide a trading outlook for the next 24 hours: Bullish, Bearish, or Neutral.

Consider general market factors:
- Common technical patterns and market cycles
- Typical support/resistance behavior
- General sentiment trends in crypto markets
- Broader macro conditions affecting crypto

Provide your reasoning in ~100-150 words, focusing on the most relevant general factors.

Return the result by calling the provided function/tool with your outlook and reasoning.
""".strip()

# ===================== PREP =====================
# AI Provider Configuration
AI_PROVIDER = os.environ.get("AI_PROVIDER", "anthropic").lower()
AI_API_KEYS = {
    "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
    "xai": os.environ.get("XAI_API_KEY"),
    "grok": os.environ.get("XAI_API_KEY"),  # Alias for xai
    "deepseek": os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY"),  # Backward compat
}
AI_API_KEY = AI_API_KEYS.get(AI_PROVIDER)

EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY")
EXCHANGE_API_SECRET = os.environ.get("EXCHANGE_API_SECRET")

# ===================== MAIN EXECUTION =====================
custom_helpers.configure_logger(RUN_NAME)
logging.info("=== Run Started ===")

# Initialize exchange client (real or forward testing)
if FORWARD_TESTING_CONFIG is not None:
    exchange = ForwardTester(FORWARD_TESTING_CONFIG)
    logging.info("Forward testing mode enabled")
else:
    exchange = BitunixFutures(EXCHANGE_API_KEY, EXCHANGE_API_SECRET)
    logging.info("Live trading mode enabled")

#  Call AI to get interpretation
try:
    ai.init_provider(AI_PROVIDER, AI_API_KEY)
    outlook = ai.send_request(PROMPT, CRYPTO)
    interpretation = outlook.interpretation
    logging.info(f"AI Interpretation: {interpretation}")
except (ai.AIResponseError, ai.AIProviderError, Exception) as e:
    logging.warning(f"AI request failed, defaulting to Neutral: {e}")
    interpretation = "Neutral"
    outlook = None

if outlook:
    ai.save_response(outlook, RUN_NAME)

# Call exchange to get current position status
try:
    position = exchange.get_pending_positions(symbol=SYMBOL)
    current_position = position.side.lower() if position else None
    logging.info(f"Current Position: {current_position}")
    logging.info(f"Available Capital: {exchange.get_account_balance('USDT')} USDT")

    # Execute trading actions
    exchange.set_margin_mode(SYMBOL, MARGIN_MODE)
    exchange.set_leverage(SYMBOL, LEVERAGE)

    # Bullish cases
    if interpretation == "Bullish" and current_position is None:
        logging.info("Bullish signal: Opening long position")
        custom_helpers.open_position(exchange, SYMBOL, direction="buy",
                                    position_size=POSITION_SIZE, stop_loss_percent=STOP_LOSS_PERCENT)

    elif interpretation == "Bullish" and current_position == "sell":
        logging.info("Bullish signal: Closing short, opening long")
        exchange.flash_close_position(position.positionId)
        custom_helpers.open_position(exchange, SYMBOL, direction="buy",
                                    position_size=POSITION_SIZE, stop_loss_percent=STOP_LOSS_PERCENT)

    elif interpretation == "Bullish" and current_position == "buy":
        logging.info("Bullish signal: Already in long position, holding")

    # Bearish cases
    elif interpretation == "Bearish" and current_position is None:
        logging.info("Bearish signal: Opening short position")
        custom_helpers.open_position(exchange, SYMBOL, direction="sell",
                                    position_size=POSITION_SIZE, stop_loss_percent=STOP_LOSS_PERCENT)

    elif interpretation == "Bearish" and current_position == "buy":
        logging.info("Bearish signal: Closing long, opening short")
        exchange.flash_close_position(position.positionId)
        custom_helpers.open_position(exchange, SYMBOL, direction="sell",
                                    position_size=POSITION_SIZE, stop_loss_percent=STOP_LOSS_PERCENT)

    elif interpretation == "Bearish" and current_position == "sell":
        logging.info("Bearish signal: Already in short position, holding")

    # Neutral cases
    elif interpretation == "Neutral" and current_position in ("buy", "sell"):
        logging.info(f"Neutral signal: Closing {current_position} position")
        exchange.flash_close_position(position.positionId)

    elif interpretation == "Neutral" and current_position is None:
        logging.info("Neutral signal: No position open, doing nothing")

    logging.info("=== Run Completed ===")

except (BitunixError, Exception) as e:
    logging.warning(f"Exchange operation failed, stopping execution: {e}")

    # SAFETY: Flash close any open position on error
    try:
        position = exchange.get_pending_positions(symbol=SYMBOL)
        if position:
            logging.warning("Emergency flash close triggered due to error")
            exchange.flash_close_position(position.positionId)
            logging.info("Emergency flash close completed")
    except Exception as close_error:
        logging.error(f"Failed to flash close position: {close_error}")

    logging.info("=== Run Failed ===")

