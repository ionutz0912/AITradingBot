#!/usr/bin/env python3
"""
Health Check Utility for AI Trading Bot

Verifies API connectivity and configuration before running the trading bot.
Run this script to diagnose issues with your setup.

Usage:
    python health_check.py
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'=' * 50}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 50}{RESET}\n")


def print_check(name: str, passed: bool, details: str = ""):
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {name}")
    if details:
        print(f"         {details}")


def print_warning(text: str):
    print(f"  [{YELLOW}WARN{RESET}] {text}")


def check_environment_variables() -> dict:
    """Check required and optional environment variables."""
    print_header("Environment Variables")

    results = {
        "ai_provider": False,
        "exchange_provider": False,
        "ai_key": False,
        "exchange_key": False
    }

    # AI Provider
    ai_provider = os.environ.get("AI_PROVIDER", "").lower()
    if ai_provider:
        print_check("AI_PROVIDER", True, f"Set to '{ai_provider}'")
        results["ai_provider"] = True
    else:
        print_check("AI_PROVIDER", False, "Not set (will default to 'anthropic')")
        ai_provider = "anthropic"

    # AI API Keys
    ai_keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "xai": "XAI_API_KEY",
        "grok": "XAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY"
    }
    key_name = ai_keys.get(ai_provider, "ANTHROPIC_API_KEY")
    api_key = os.environ.get(key_name, "")
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "****"
        print_check(key_name, True, f"Set ({masked})")
        results["ai_key"] = True
    else:
        print_check(key_name, False, f"Required for {ai_provider} provider")

    # Exchange Provider
    exchange_provider = os.environ.get("EXCHANGE_PROVIDER", "").lower()
    if exchange_provider:
        print_check("EXCHANGE_PROVIDER", True, f"Set to '{exchange_provider}'")
        results["exchange_provider"] = True
    else:
        print_check("EXCHANGE_PROVIDER", False, "Not set (will default to 'coinbase')")
        exchange_provider = "coinbase"

    # Exchange API Keys
    if exchange_provider == "coinbase":
        coinbase_key = os.environ.get("COINBASE_API_KEY", "")
        coinbase_secret = os.environ.get("COINBASE_API_SECRET", "")

        if coinbase_key:
            print_check("COINBASE_API_KEY", True, f"Set (length: {len(coinbase_key)})")
        else:
            print_check("COINBASE_API_KEY", False, "Required for Coinbase")

        if coinbase_secret:
            has_pem = "BEGIN" in coinbase_secret
            print_check("COINBASE_API_SECRET", True, f"Set (PEM format: {has_pem})")
            results["exchange_key"] = True
        else:
            print_check("COINBASE_API_SECRET", False, "Required for Coinbase")

    elif exchange_provider == "bitunix":
        bitunix_key = os.environ.get("BITUNIX_API_KEY", "")
        bitunix_secret = os.environ.get("BITUNIX_API_SECRET", "")

        if bitunix_key:
            print_check("BITUNIX_API_KEY", True, f"Set (length: {len(bitunix_key)})")
            results["exchange_key"] = True
        else:
            print_check("BITUNIX_API_KEY", False, "Required for Bitunix")

        if bitunix_secret:
            print_check("BITUNIX_API_SECRET", True, "Set")
        else:
            print_check("BITUNIX_API_SECRET", False, "Required for Bitunix")

    # Optional: Discord
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if discord_url:
        print_check("DISCORD_WEBHOOK_URL", True, "Set (optional)")
    else:
        print_warning("DISCORD_WEBHOOK_URL not set (notifications disabled)")

    return results


def check_ai_provider() -> bool:
    """Test AI provider connectivity."""
    print_header("AI Provider Connectivity")

    ai_provider = os.environ.get("AI_PROVIDER", "anthropic").lower()

    try:
        from lib import ai

        # Get appropriate API key
        ai_keys = {
            "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
            "xai": os.environ.get("XAI_API_KEY"),
            "grok": os.environ.get("XAI_API_KEY"),
            "deepseek": os.environ.get("DEEPSEEK_API_KEY")
        }
        api_key = ai_keys.get(ai_provider)

        if not api_key:
            print_check(f"Initialize {ai_provider}", False, "API key not configured")
            return False

        # Initialize and test
        ai.init_provider(ai_provider, api_key)
        print_check(f"Initialize {ai_provider}", True, f"Provider ready")

        # Quick test (minimal tokens)
        test_prompt = "Reply with only the word 'OK' to confirm you're working."
        try:
            response = ai.send_request(test_prompt, "test", save_response=False)
            print_check("AI Response Test", True, f"Received response: '{response.interpretation}'")
            return True
        except Exception as e:
            print_check("AI Response Test", False, str(e)[:100])
            return False

    except ImportError as e:
        print_check("Import AI module", False, str(e))
        return False
    except Exception as e:
        print_check(f"AI Provider ({ai_provider})", False, str(e)[:100])
        return False


def check_exchange_provider() -> bool:
    """Test exchange provider connectivity."""
    print_header("Exchange Provider Connectivity")

    exchange_provider = os.environ.get("EXCHANGE_PROVIDER", "coinbase").lower()

    try:
        if exchange_provider == "coinbase":
            from lib import CoinbaseAdvanced, CoinbaseError

            api_key = os.environ.get("COINBASE_API_KEY")
            api_secret = os.environ.get("COINBASE_API_SECRET")

            if not api_key or not api_secret:
                print_check("Coinbase credentials", False, "API key or secret not set")
                return False

            try:
                client = CoinbaseAdvanced(api_key, api_secret)
                print_check("Initialize Coinbase client", True)

                # Test balance fetch
                balance = client.get_account_balance("USD")
                print_check("Fetch USD balance", True, f"${balance:.2f} available")

                # Test price fetch
                price = client.get_current_price("BTCUSDT")
                print_check("Fetch BTC price", True, f"${price:,.2f}")

                return True

            except CoinbaseError as e:
                print_check("Coinbase API", False, str(e)[:100])
                return False

        elif exchange_provider == "bitunix":
            from lib import BitunixFutures, BitunixError

            api_key = os.environ.get("BITUNIX_API_KEY")
            api_secret = os.environ.get("BITUNIX_API_SECRET")

            if not api_key or not api_secret:
                print_check("Bitunix credentials", False, "API key or secret not set")
                return False

            try:
                client = BitunixFutures(api_key, api_secret)
                print_check("Initialize Bitunix client", True)

                # Test balance fetch
                balance = client.get_account_balance("USDT")
                print_check("Fetch USDT balance", True, f"${balance:.2f} available")

                return True

            except BitunixError as e:
                print_check("Bitunix API", False, str(e)[:100])
                return False

        else:
            print_check("Exchange provider", False, f"Unknown provider: {exchange_provider}")
            return False

    except ImportError as e:
        print_check("Import exchange module", False, str(e))
        return False
    except Exception as e:
        print_check(f"Exchange ({exchange_provider})", False, str(e)[:100])
        return False


def check_market_data() -> bool:
    """Test market data fetching."""
    print_header("Market Data Services")

    try:
        from lib.market_data import get_market_data, get_fear_greed_index, MarketDataError

        # Test price data
        try:
            btc_data = get_market_data("BTC")
            print_check("Fetch BTC market data", True,
                       f"${btc_data.price:,.2f} ({btc_data.price_change_24h_percent:+.2f}% 24h)")
        except MarketDataError as e:
            print_check("Fetch BTC market data", False, str(e)[:100])
            return False

        # Test Fear & Greed Index
        fng = get_fear_greed_index()
        if fng:
            print_check("Fear & Greed Index", True, f"{fng['value']}/100 - {fng['classification']}")
        else:
            print_warning("Fear & Greed Index unavailable")

        return True

    except ImportError as e:
        print_check("Import market_data module", False, str(e))
        return False
    except Exception as e:
        print_check("Market data services", False, str(e)[:100])
        return False


def check_directories() -> bool:
    """Check required directories exist or can be created."""
    print_header("Directory Structure")

    dirs = ["logs", "ai_responses", "performance_data", "forward_testing_results"]
    all_ok = True

    for dir_name in dirs:
        if os.path.exists(dir_name):
            print_check(f"Directory: {dir_name}/", True, "Exists")
        else:
            try:
                os.makedirs(dir_name, exist_ok=True)
                print_check(f"Directory: {dir_name}/", True, "Created")
            except Exception as e:
                print_check(f"Directory: {dir_name}/", False, str(e))
                all_ok = False

    return all_ok


def check_dependencies() -> bool:
    """Check required Python packages are installed."""
    print_header("Python Dependencies")

    required = [
        ("requests", "requests"),
        ("pydantic", "pydantic"),
        ("dotenv", "python-dotenv"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
    ]

    optional = [
        ("coinbase", "coinbase-advanced-py"),
    ]

    all_ok = True

    for module, package in required:
        try:
            __import__(module)
            print_check(f"Package: {package}", True)
        except ImportError:
            print_check(f"Package: {package}", False, "pip install " + package)
            all_ok = False

    for module, package in optional:
        try:
            __import__(module)
            print_check(f"Package: {package}", True, "(optional)")
        except ImportError:
            print_warning(f"Package {package} not installed (optional)")

    return all_ok


def main():
    """Run all health checks."""
    print(f"\n{BOLD}AI Trading Bot - Health Check{RESET}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Python: {sys.version.split()[0]}")

    results = {
        "dependencies": check_dependencies(),
        "directories": check_directories(),
        "environment": check_environment_variables(),
        "market_data": check_market_data(),
    }

    # Only check AI/Exchange if env vars are set
    env_check = results["environment"]
    if env_check.get("ai_key"):
        results["ai_provider"] = check_ai_provider()
    else:
        print_header("AI Provider Connectivity")
        print_warning("Skipped - API key not configured")
        results["ai_provider"] = False

    if env_check.get("exchange_key"):
        results["exchange_provider"] = check_exchange_provider()
    else:
        print_header("Exchange Provider Connectivity")
        print_warning("Skipped - Exchange credentials not configured")
        results["exchange_provider"] = False

    # Summary
    print_header("Summary")

    critical_passed = results["dependencies"] and results["directories"]
    optional_passed = results.get("ai_provider", False) and results.get("exchange_provider", False)

    if critical_passed and optional_passed:
        print(f"  {GREEN}{BOLD}All checks passed! Bot is ready to run.{RESET}")
        return 0
    elif critical_passed:
        print(f"  {YELLOW}{BOLD}Core checks passed. Some services need configuration.{RESET}")
        print(f"  Review failed checks above and update your .env file.")
        return 1
    else:
        print(f"  {RED}{BOLD}Critical checks failed. Please fix issues above.{RESET}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
