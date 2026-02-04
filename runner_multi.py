#!/usr/bin/env python3
"""
Multi-Symbol Trading Bot Runner

Trades multiple cryptocurrency pairs based on configuration file.
Supports concurrent AI analysis and sequential trade execution.

Usage:
    python runner_multi.py                    # Use default config
    python runner_multi.py --config my.json   # Use custom config
    python runner_multi.py --dry-run          # Analyze without trading
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, Any, Optional

from lib import (
    ai, custom_helpers, ForwardTester,
    BitunixFutures, BitunixError,
    CoinbaseAdvanced, CoinbaseError,
    DiscordNotifier,
    TelegramNotifier,
    get_tracker,
    load_config, get_enabled_symbols, validate_config, TradingConfig, SymbolConfig,
    get_enhanced_market_context, get_market_data
)

load_dotenv()


def create_prompt(symbol_config: SymbolConfig, include_market_data: bool = True) -> str:
    """Create AI prompt for a symbol, optionally including market data."""
    market_context = ""
    if include_market_data:
        try:
            market_context = f"\n\n{get_enhanced_market_context(symbol_config.symbol)}\n"
        except Exception as e:
            logging.warning(f"Could not fetch market data for {symbol_config.symbol}: {e}")
            market_context = "\n(Real-time market data unavailable)\n"

    return f"""You are a cryptocurrency market analyst AI.
{market_context}
Based on the market data above (if available) and your general knowledge of cryptocurrency markets and typical {symbol_config.crypto_name} behavior patterns, provide a trading outlook for the next 24 hours: Bullish, Bearish, or Neutral.

Consider:
- Current price action and 24h performance
- Common technical patterns and market cycles
- Typical support/resistance behavior
- General sentiment trends in crypto markets
- Broader macro conditions affecting crypto

Provide your reasoning in ~100-150 words, focusing on the most relevant factors.

Return the result by calling the provided function/tool with your outlook and reasoning.
""".strip()


def initialize_exchange(config: TradingConfig):
    """Initialize the appropriate exchange client."""
    if config.forward_testing:
        forward_config = {
            "run_name": config.run_name,
            "initial_capital": config.forward_testing_capital,
            "fees": config.forward_testing_fees,
        }
        exchange = ForwardTester(forward_config)
        logging.info("Forward testing mode enabled")
        return exchange, False  # is_spot = False for forward tester

    if config.exchange_provider == "coinbase":
        api_key = os.environ.get("COINBASE_API_KEY")
        api_secret = os.environ.get("COINBASE_API_SECRET")
        exchange = CoinbaseAdvanced(api_key, api_secret)
        logging.info("Live trading mode: Coinbase")
        return exchange, True  # Coinbase is spot

    if config.exchange_provider == "bitunix":
        api_key = os.environ.get("BITUNIX_API_KEY") or os.environ.get("EXCHANGE_API_KEY")
        api_secret = os.environ.get("BITUNIX_API_SECRET") or os.environ.get("EXCHANGE_API_SECRET")
        exchange = BitunixFutures(api_key, api_secret)
        logging.info("Live trading mode: Bitunix")
        return exchange, False  # Bitunix supports shorting

    raise ValueError(f"Unknown exchange provider: {config.exchange_provider}")


def initialize_ai(config: TradingConfig):
    """Initialize the AI provider."""
    ai_keys = {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "xai": os.environ.get("XAI_API_KEY"),
        "grok": os.environ.get("XAI_API_KEY"),
        "deepseek": os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY"),
    }
    api_key = ai_keys.get(config.ai_provider)

    if not api_key:
        raise ValueError(f"No API key found for AI provider: {config.ai_provider}")

    ai.init_provider(config.ai_provider, api_key)
    logging.info(f"AI provider initialized: {config.ai_provider}")


def execute_trading_logic(
    exchange,
    is_spot: bool,
    symbol_config: SymbolConfig,
    interpretation: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Execute trading logic for a single symbol.

    Returns a dict with action taken and result.
    """
    symbol = symbol_config.symbol
    result = {
        "symbol": symbol,
        "interpretation": interpretation,
        "action": "none",
        "success": True,
        "message": ""
    }

    try:
        # Get current position
        position = exchange.get_pending_positions(symbol=symbol)
        current_position = position.side.lower() if position else None
        result["current_position"] = current_position

        if dry_run:
            result["action"] = f"dry_run_{interpretation.lower()}"
            result["message"] = f"Would execute {interpretation} logic (dry run)"
            logging.info(f"[DRY RUN] {symbol}: {interpretation} - Position: {current_position}")
            return result

        # Set margin mode and leverage (no-op for spot)
        exchange.set_margin_mode(symbol, symbol_config.margin_mode)
        exchange.set_leverage(symbol, symbol_config.leverage)

        # Execute based on interpretation
        if interpretation == "Bullish":
            if current_position is None:
                logging.info(f"{symbol}: Bullish - Opening long position")
                custom_helpers.open_position(
                    exchange, symbol, direction="buy",
                    position_size=symbol_config.position_size,
                    stop_loss_percent=symbol_config.stop_loss_percent
                )
                result["action"] = "open_long"
                result["message"] = "Opened long position"

            elif current_position == "sell":
                logging.info(f"{symbol}: Bullish - Closing short, opening long")
                exchange.flash_close_position(position.positionId)
                custom_helpers.open_position(
                    exchange, symbol, direction="buy",
                    position_size=symbol_config.position_size,
                    stop_loss_percent=symbol_config.stop_loss_percent
                )
                result["action"] = "flip_to_long"
                result["message"] = "Closed short and opened long"

            else:  # current_position == "buy"
                logging.info(f"{symbol}: Bullish - Already long, holding")
                result["action"] = "hold_long"
                result["message"] = "Already in long position"

        elif interpretation == "Bearish":
            if current_position is None:
                if is_spot:
                    logging.info(f"{symbol}: Bearish - Spot exchange, no position to close")
                    result["action"] = "no_action_spot"
                    result["message"] = "Spot exchange - cannot short"
                else:
                    logging.info(f"{symbol}: Bearish - Opening short position")
                    custom_helpers.open_position(
                        exchange, symbol, direction="sell",
                        position_size=symbol_config.position_size,
                        stop_loss_percent=symbol_config.stop_loss_percent
                    )
                    result["action"] = "open_short"
                    result["message"] = "Opened short position"

            elif current_position == "buy":
                if is_spot:
                    logging.info(f"{symbol}: Bearish - Closing long (no shorting on spot)")
                    exchange.flash_close_position(position.positionId)
                    result["action"] = "close_long_spot"
                    result["message"] = "Closed long position (spot - no shorting)"
                else:
                    logging.info(f"{symbol}: Bearish - Closing long, opening short")
                    exchange.flash_close_position(position.positionId)
                    custom_helpers.open_position(
                        exchange, symbol, direction="sell",
                        position_size=symbol_config.position_size,
                        stop_loss_percent=symbol_config.stop_loss_percent
                    )
                    result["action"] = "flip_to_short"
                    result["message"] = "Closed long and opened short"

            else:  # current_position == "sell"
                logging.info(f"{symbol}: Bearish - Already short, holding")
                result["action"] = "hold_short"
                result["message"] = "Already in short position"

        elif interpretation == "Neutral":
            if current_position:
                logging.info(f"{symbol}: Neutral - Closing {current_position} position")
                exchange.flash_close_position(position.positionId)
                result["action"] = f"close_{current_position}"
                result["message"] = f"Closed {current_position} position"
            else:
                logging.info(f"{symbol}: Neutral - No position, staying flat")
                result["action"] = "no_position"
                result["message"] = "No position to close"

    except Exception as e:
        logging.error(f"{symbol}: Trading error - {e}")
        result["success"] = False
        result["message"] = str(e)

        # Emergency close on error
        try:
            position = exchange.get_pending_positions(symbol=symbol)
            if position:
                logging.warning(f"{symbol}: Emergency closing position due to error")
                exchange.flash_close_position(position.positionId)
                result["action"] = "emergency_close"
        except Exception as close_error:
            logging.error(f"{symbol}: Failed to emergency close: {close_error}")

    return result


def run_multi_symbol_bot(
    config_file: str = "config.json",
    dry_run: bool = False,
    symbols_override: Optional[list] = None
):
    """
    Run the multi-symbol trading bot.

    Args:
        config_file: Path to configuration file (relative to configs/)
        dry_run: If True, analyze but don't execute trades
        symbols_override: List of symbols to trade (overrides config)
    """
    # Load configuration
    config = load_config(config_file)

    # Validate configuration
    issues = validate_config(config)
    if issues:
        logging.error("Configuration issues found:")
        for issue in issues:
            logging.error(f"  - {issue}")
        if not dry_run:
            logging.error("Fix configuration issues before live trading")
            return

    # Setup logging
    custom_helpers.configure_logger(config.run_name + "_multi")
    logging.info("=== Multi-Symbol Run Started ===")
    logging.info(f"Config: {config_file}, Dry Run: {dry_run}")

    # Get enabled symbols
    if symbols_override:
        symbols = [s for s in config.symbols if s.symbol in symbols_override]
    else:
        symbols = get_enabled_symbols(config)

    if not symbols:
        logging.warning("No symbols to trade")
        return

    logging.info(f"Trading {len(symbols)} symbols: {[s.symbol for s in symbols]}")

    # Initialize exchange
    try:
        exchange, is_spot = initialize_exchange(config)
    except Exception as e:
        logging.error(f"Failed to initialize exchange: {e}")
        return

    # Initialize AI
    try:
        initialize_ai(config)
    except Exception as e:
        logging.error(f"Failed to initialize AI: {e}")
        return

    # Initialize Discord notifier if enabled
    discord = None
    if config.discord_enabled:
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        if webhook_url:
            discord = DiscordNotifier(webhook_url)

    # Initialize Telegram notifier if enabled
    telegram = None
    if config.telegram_enabled:
        telegram = TelegramNotifier()
        if telegram.enabled:
            logging.info("Telegram notifications enabled")
        else:
            logging.warning("Telegram configured but missing credentials")
            telegram = None

    # Initialize performance tracker
    tracker = get_tracker(config.run_name)

    # Process each symbol
    results = []
    for symbol_config in symbols:
        logging.info(f"\n--- Processing {symbol_config.symbol} ({symbol_config.crypto_name}) ---")

        # Generate prompt
        prompt = create_prompt(symbol_config, config.include_market_data)

        # Get AI interpretation
        try:
            outlook = ai.send_request(prompt, symbol_config.crypto_name)
            interpretation = outlook.interpretation
            logging.info(f"{symbol_config.symbol}: AI says {interpretation}")

            # Save AI response
            ai.save_response(outlook, f"{config.run_name}_{symbol_config.symbol}")

        except Exception as e:
            logging.warning(f"{symbol_config.symbol}: AI request failed, defaulting to Neutral: {e}")
            interpretation = "Neutral"
            outlook = None

        # Execute trading logic
        result = execute_trading_logic(
            exchange, is_spot, symbol_config, interpretation, dry_run
        )
        results.append(result)

        # Send Discord notification
        if discord and outlook:
            try:
                reasoning = outlook.reasoning if config.discord_include_reasoning else None
                discord.send_notification(
                    symbol=symbol_config.symbol,
                    interpretation=interpretation,
                    reasoning=reasoning
                )
            except Exception as e:
                logging.warning(f"Discord notification failed: {e}")

        # Send Telegram notification
        if telegram and outlook:
            try:
                # Get current price for stop loss calculation
                current_price = None
                stop_loss_price = None
                try:
                    market_data = get_market_data(symbol_config.symbol)
                    current_price = market_data.price
                    # Calculate stop loss price if configured
                    if symbol_config.stop_loss_percent and current_price:
                        if result["action"] in ["open_long", "flip_to_long", "hold_long"]:
                            stop_loss_price = current_price * (1 - symbol_config.stop_loss_percent / 100)
                        elif result["action"] in ["open_short", "flip_to_short", "hold_short"]:
                            stop_loss_price = current_price * (1 + symbol_config.stop_loss_percent / 100)
                except Exception:
                    pass

                reasoning = outlook.reasoning if config.telegram_include_reasoning else None
                telegram.send_trade_signal(
                    symbol=symbol_config.symbol,
                    signal=interpretation,
                    action=result["action"],
                    crypto_name=symbol_config.crypto_name,
                    current_price=current_price,
                    entry_price=current_price if result["action"] in ["open_long", "open_short", "flip_to_long", "flip_to_short"] else None,
                    stop_loss_price=stop_loss_price if config.telegram_include_stop_loss else None,
                    stop_loss_percent=symbol_config.stop_loss_percent if config.telegram_include_stop_loss else None,
                    position_size=symbol_config.position_size,
                    reasoning=reasoning
                )
            except Exception as e:
                logging.warning(f"Telegram notification failed: {e}")

    # Summary
    logging.info("\n=== Multi-Symbol Run Summary ===")
    for result in results:
        status = "OK" if result["success"] else "FAILED"
        logging.info(f"  {result['symbol']}: {result['interpretation']} -> {result['action']} [{status}]")

    logging.info("=== Multi-Symbol Run Completed ===")

    return results


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="AI Trading Bot - Multi-Symbol Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner_multi.py                        # Run with default config
  python runner_multi.py --config my_config.json  # Use custom config
  python runner_multi.py --dry-run              # Analyze without trading
  python runner_multi.py --symbols BTC ETH      # Trade specific symbols only
        """
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.json',
        help='Configuration file name (in configs/ directory)'
    )

    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Analyze markets without executing trades'
    )

    parser.add_argument(
        '--symbols', '-s',
        nargs='+',
        help='Specific symbols to trade (overrides config)'
    )

    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create a sample configuration file and exit'
    )

    args = parser.parse_args()

    if args.create_config:
        from lib.config import create_sample_config
        path = create_sample_config()
        print(f"Sample configuration created: {path}")
        print("Copy to configs/config.json and customize for your needs.")
        return

    # Normalize symbol names
    symbols = None
    if args.symbols:
        symbols = [s.upper() + "USDT" if not s.upper().endswith("USDT") else s.upper()
                   for s in args.symbols]

    try:
        run_multi_symbol_bot(
            config_file=args.config,
            dry_run=args.dry_run,
            symbols_override=symbols
        )
    except KeyboardInterrupt:
        logging.info("Run interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
