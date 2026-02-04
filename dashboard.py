#!/usr/bin/env python3
"""
AI Trading Bot Dashboard

Comprehensive dashboard showing:
- Account balances and positions
- Performance metrics and trade history
- Market data for tracked symbols
- Active configuration
- System health status

Usage:
    python dashboard.py                  # Full dashboard
    python dashboard.py --summary        # Quick summary only
    python dashboard.py --positions      # Positions only
    python dashboard.py --performance    # Performance only
    python dashboard.py --config         # Show active config
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, List, Any

load_dotenv()

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def print_header(title: str, char: str = "="):
    width = 60
    print(f"\n{BOLD}{CYAN}{char * width}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{char * width}{RESET}\n")


def print_section(title: str):
    print(f"\n{BOLD}{BLUE}--- {title} ---{RESET}\n")


def format_usd(value: float) -> str:
    if value >= 0:
        return f"{GREEN}${value:,.2f}{RESET}"
    return f"{RED}${value:,.2f}{RESET}"


def format_percent(value: float) -> str:
    if value >= 0:
        return f"{GREEN}+{value:.2f}%{RESET}"
    return f"{RED}{value:.2f}%{RESET}"


def format_status(ok: bool, text: str = "") -> str:
    if ok:
        return f"{GREEN}OK{RESET}" + (f" {text}" if text else "")
    return f"{RED}FAIL{RESET}" + (f" {text}" if text else "")


class Dashboard:
    def __init__(self):
        self.exchange = None
        self.config = None
        self.tracker = None
        self.is_spot = True

    def initialize(self) -> bool:
        """Initialize connections to exchange and load config."""
        try:
            from lib import (
                load_config, get_enabled_symbols,
                CoinbaseAdvanced, BitunixFutures, ForwardTester,
                get_tracker
            )

            # Load configuration
            self.config = load_config()
            self.enabled_symbols = get_enabled_symbols(self.config)

            # Initialize exchange
            if self.config.forward_testing:
                forward_config = {
                    "run_name": self.config.run_name,
                    "initial_capital": self.config.forward_testing_capital,
                    "fees": self.config.forward_testing_fees,
                }
                self.exchange = ForwardTester(forward_config)
                self.is_spot = False
                self.exchange_name = "Forward Tester (Simulated)"
            elif self.config.exchange_provider == "coinbase":
                api_key = os.environ.get("COINBASE_API_KEY")
                api_secret = os.environ.get("COINBASE_API_SECRET")
                if api_key and api_secret:
                    self.exchange = CoinbaseAdvanced(api_key, api_secret)
                    self.is_spot = True
                    self.exchange_name = "Coinbase (Spot)"
            elif self.config.exchange_provider == "bitunix":
                api_key = os.environ.get("BITUNIX_API_KEY")
                api_secret = os.environ.get("BITUNIX_API_SECRET")
                if api_key and api_secret:
                    self.exchange = BitunixFutures(api_key, api_secret)
                    self.is_spot = False
                    self.exchange_name = "Bitunix (Futures)"

            # Initialize tracker
            self.tracker = get_tracker(self.config.run_name)

            return True
        except Exception as e:
            print(f"{RED}Initialization error: {e}{RESET}")
            return False

    def show_account_summary(self):
        """Display account balances."""
        print_section("Account Summary")

        if not self.exchange:
            print(f"  {YELLOW}Exchange not connected{RESET}")
            return

        try:
            # Get USD/USDT balance
            if self.config.exchange_provider == "coinbase":
                usd_balance = self.exchange.get_account_balance("USD")
                usdc_balance = self.exchange.get_account_balance("USDC")
                print(f"  Exchange:     {self.exchange_name}")
                print(f"  USD Balance:  {format_usd(usd_balance)}")
                print(f"  USDC Balance: {format_usd(usdc_balance)}")
            else:
                usdt_balance = self.exchange.get_account_balance("USDT")
                print(f"  Exchange:      {self.exchange_name}")
                print(f"  USDT Balance:  {format_usd(usdt_balance)}")

            # Show mode
            mode = "Forward Testing" if self.config.forward_testing else "Live Trading"
            mode_color = YELLOW if self.config.forward_testing else GREEN
            print(f"  Mode:          {mode_color}{mode}{RESET}")

        except Exception as e:
            print(f"  {RED}Error fetching balance: {e}{RESET}")

    def show_positions(self):
        """Display current positions for all enabled symbols."""
        print_section("Open Positions")

        if not self.exchange:
            print(f"  {YELLOW}Exchange not connected{RESET}")
            return

        positions_found = False

        for symbol_config in self.enabled_symbols:
            try:
                position = self.exchange.get_pending_positions(symbol=symbol_config.symbol)
                if position:
                    positions_found = True
                    side = position.side.upper()
                    side_color = GREEN if side == "BUY" else RED

                    print(f"  {BOLD}{symbol_config.symbol}{RESET} ({symbol_config.crypto_name})")
                    print(f"    Side:        {side_color}{side}{RESET}")

                    # Try to get position details if available
                    if hasattr(position, 'qty'):
                        print(f"    Quantity:    {position.qty}")
                    if hasattr(position, 'entryPrice'):
                        print(f"    Entry Price: ${float(position.entryPrice):,.2f}")
                    if hasattr(position, 'unrealisedPNL'):
                        pnl = float(position.unrealisedPNL)
                        print(f"    Unrealized:  {format_usd(pnl)}")

                    # Show configured stop loss
                    if symbol_config.stop_loss_percent:
                        print(f"    Stop Loss:   {symbol_config.stop_loss_percent}%")
                    print()

            except Exception as e:
                print(f"  {symbol_config.symbol}: {RED}Error: {e}{RESET}")

        if not positions_found:
            print(f"  {DIM}No open positions{RESET}")

    def show_market_data(self):
        """Display market data for enabled symbols."""
        print_section("Market Data")

        try:
            from lib import get_market_data, MarketDataError

            for symbol_config in self.enabled_symbols:
                try:
                    data = get_market_data(symbol_config.symbol)
                    change_color = GREEN if data.price_change_24h_percent >= 0 else RED

                    print(f"  {BOLD}{symbol_config.crypto_name}{RESET} ({symbol_config.symbol})")
                    print(f"    Price:    ${data.price:,.2f}")
                    print(f"    24h:      {change_color}{data.price_change_24h_percent:+.2f}%{RESET}")
                    print(f"    High/Low: ${data.high_24h:,.2f} / ${data.low_24h:,.2f}")
                    print(f"    Volume:   ${data.volume_24h:,.0f}")
                    print()

                except MarketDataError as e:
                    print(f"  {symbol_config.symbol}: {YELLOW}Data unavailable{RESET}")

            # Fear & Greed Index
            from lib.market_data import get_fear_greed_index
            fng = get_fear_greed_index()
            if fng:
                value = fng['value']
                if value <= 25:
                    fng_color = RED
                elif value <= 45:
                    fng_color = YELLOW
                elif value <= 55:
                    fng_color = RESET
                elif value <= 75:
                    fng_color = GREEN
                else:
                    fng_color = GREEN + BOLD

                print(f"  {BOLD}Fear & Greed Index{RESET}")
                print(f"    Value:    {fng_color}{value}/100{RESET}")
                print(f"    Sentiment: {fng['classification']}")

        except Exception as e:
            print(f"  {RED}Error fetching market data: {e}{RESET}")

    def show_performance(self):
        """Display performance metrics."""
        print_section("Performance Metrics")

        if not self.tracker:
            print(f"  {YELLOW}Performance tracker not initialized{RESET}")
            return

        try:
            metrics = self.tracker.get_metrics()

            if metrics.total_trades == 0:
                print(f"  {DIM}No trades recorded yet{RESET}")
                return

            # Win rate color
            if metrics.win_rate >= 60:
                wr_color = GREEN
            elif metrics.win_rate >= 40:
                wr_color = YELLOW
            else:
                wr_color = RED

            print(f"  Strategy:       {self.config.run_name}")
            print(f"  Total Trades:   {metrics.total_trades}")
            print(f"  Win Rate:       {wr_color}{metrics.win_rate:.1f}%{RESET} ({metrics.winning_trades}W / {metrics.losing_trades}L)")
            print()
            print(f"  Total P&L:      {format_usd(metrics.total_pnl)}")
            print(f"  Average Win:    {format_usd(metrics.average_win)}")
            print(f"  Average Loss:   {format_usd(metrics.average_loss)}")
            print(f"  Largest Win:    {format_usd(metrics.largest_win)}")
            print(f"  Largest Loss:   {format_usd(metrics.largest_loss)}")
            print()
            print(f"  Profit Factor:  {metrics.profit_factor:.2f}")
            print(f"  Max Drawdown:   {format_usd(metrics.max_drawdown)}")
            print()

            # Streaks
            streak_text = f"{abs(metrics.current_streak)} {'wins' if metrics.current_streak > 0 else 'losses'}"
            print(f"  Current Streak: {streak_text}")
            print(f"  Best Streak:    {metrics.best_streak} wins")
            print(f"  Worst Streak:   {abs(metrics.worst_streak)} losses")

        except Exception as e:
            print(f"  {RED}Error loading performance data: {e}{RESET}")

    def show_recent_trades(self, count: int = 5):
        """Display recent trades."""
        print_section(f"Recent Trades (Last {count})")

        if not self.tracker:
            print(f"  {YELLOW}Performance tracker not initialized{RESET}")
            return

        try:
            trades = self.tracker.get_recent_trades(count)

            if not trades:
                print(f"  {DIM}No trades recorded{RESET}")
                return

            for trade in reversed(trades):
                pnl_color = GREEN if trade.pnl >= 0 else RED
                side_color = GREEN if trade.side == "buy" else RED

                print(f"  {BOLD}{trade.symbol}{RESET} - {side_color}{trade.side.upper()}{RESET}")
                print(f"    Entry: ${trade.entry_price:,.2f} -> Exit: ${trade.exit_price:,.2f}")
                print(f"    P&L:   {pnl_color}${trade.pnl:.2f} ({trade.pnl_percent:+.2f}%){RESET}")
                print(f"    Time:  {trade.exit_time[:19]}")
                print()

        except Exception as e:
            print(f"  {RED}Error loading trades: {e}{RESET}")

    def show_configuration(self):
        """Display active configuration."""
        print_section("Active Configuration")

        if not self.config:
            print(f"  {YELLOW}Configuration not loaded{RESET}")
            return

        print(f"  Run Name:       {self.config.run_name}")
        print(f"  AI Provider:    {self.config.ai_provider}")
        print(f"  Exchange:       {self.config.exchange_provider}")
        print(f"  Forward Test:   {'Yes' if self.config.forward_testing else 'No'}")
        print(f"  Market Data:    {'Enabled' if self.config.include_market_data else 'Disabled'}")
        print()

        # Notifications
        discord_status = "Enabled" if self.config.discord_enabled else "Disabled"
        telegram_env = os.environ.get("TELEGRAM_BOT_TOKEN")
        telegram_status = "Configured" if telegram_env else "Not configured"
        print(f"  Discord:        {discord_status}")
        print(f"  Telegram:       {telegram_status}")
        print()

        # Risk settings
        print(f"  Max Positions:  {self.config.max_positions}")
        print(f"  Max Daily:      {self.config.max_daily_trades}")
        print(f"  Max Drawdown:   {self.config.max_drawdown_percent}%")
        print()

        # Symbols
        print(f"  {BOLD}Enabled Symbols:{RESET}")
        for sym in self.enabled_symbols:
            size_str = f"{sym.position_size}%" if isinstance(sym.position_size, str) else f"${sym.position_size}"
            sl_str = f"{sym.stop_loss_percent}% SL" if sym.stop_loss_percent else "No SL"
            print(f"    - {sym.symbol} ({sym.crypto_name}): {size_str}, {sl_str}, {sym.leverage}x")

    def show_system_health(self):
        """Display system health status."""
        print_section("System Health")

        # Check AI provider
        ai_provider = self.config.ai_provider if self.config else os.environ.get("AI_PROVIDER", "anthropic")
        ai_keys = {
            "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
            "xai": os.environ.get("XAI_API_KEY"),
            "grok": os.environ.get("XAI_API_KEY"),
            "deepseek": os.environ.get("DEEPSEEK_API_KEY"),
        }
        ai_key = ai_keys.get(ai_provider)
        print(f"  AI Provider:    {format_status(bool(ai_key), ai_provider)}")

        # Check exchange
        exchange_provider = self.config.exchange_provider if self.config else os.environ.get("EXCHANGE_PROVIDER", "coinbase")
        exchange_ok = self.exchange is not None
        print(f"  Exchange:       {format_status(exchange_ok, exchange_provider)}")

        # Check directories
        dirs = ["logs", "ai_responses", "performance_data", "configs"]
        for d in dirs:
            exists = Path(d).exists()
            print(f"  Directory {d}/:  {format_status(exists)}")

        # Check config file
        config_exists = Path("configs/config.json").exists()
        print(f"  Config File:    {format_status(config_exists, 'configs/config.json' if config_exists else 'using defaults')}")

    def show_trading_logic(self):
        """Display trading logic summary."""
        print_section("Trading Logic")

        exchange_type = "Spot" if self.is_spot else "Futures"
        print(f"  Exchange Type: {exchange_type}")
        print()

        print(f"  {BOLD}Signal -> Action:{RESET}")
        print(f"    {GREEN}Bullish{RESET}  -> Open/Hold LONG position")
        if self.is_spot:
            print(f"    {RED}Bearish{RESET}  -> Close position (no shorting on spot)")
        else:
            print(f"    {RED}Bearish{RESET}  -> Open/Hold SHORT position")
        print(f"    {YELLOW}Neutral{RESET}  -> Close any position")
        print()

        print(f"  {BOLD}Position Sizing:{RESET}")
        for sym in self.enabled_symbols:
            if isinstance(sym.position_size, str) and sym.position_size.endswith('%'):
                print(f"    {sym.symbol}: {sym.position_size} of available capital")
            else:
                print(f"    {sym.symbol}: ${sym.position_size} fixed size")

        print()
        print(f"  {BOLD}Stop Loss:{RESET}")
        for sym in self.enabled_symbols:
            if sym.stop_loss_percent:
                print(f"    {sym.symbol}: {sym.stop_loss_percent}% from entry")
            else:
                print(f"    {sym.symbol}: {DIM}No stop loss{RESET}")

    def run_full_dashboard(self):
        """Run full dashboard display."""
        print_header("AI TRADING BOT DASHBOARD")
        print(f"  Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

        if not self.initialize():
            print(f"\n{RED}Failed to initialize dashboard{RESET}")
            return

        self.show_account_summary()
        self.show_positions()
        self.show_market_data()
        self.show_performance()
        self.show_recent_trades()
        self.show_configuration()
        self.show_trading_logic()
        self.show_system_health()

        print_header("END OF DASHBOARD", "-")

    def run_summary(self):
        """Run quick summary only."""
        print_header("QUICK SUMMARY")

        if not self.initialize():
            return

        self.show_account_summary()
        self.show_positions()

        # Quick performance
        if self.tracker:
            metrics = self.tracker.get_metrics()
            if metrics.total_trades > 0:
                print_section("Performance Quick Stats")
                print(f"  Trades: {metrics.total_trades} | Win Rate: {metrics.win_rate:.1f}% | P&L: {format_usd(metrics.total_pnl)}")

    def run_positions_only(self):
        """Show positions only."""
        print_header("POSITIONS")
        if not self.initialize():
            return
        self.show_account_summary()
        self.show_positions()

    def run_performance_only(self):
        """Show performance only."""
        print_header("PERFORMANCE")
        if not self.initialize():
            return
        self.show_performance()
        self.show_recent_trades(10)

    def run_config_only(self):
        """Show configuration only."""
        print_header("CONFIGURATION")
        if not self.initialize():
            return
        self.show_configuration()
        self.show_trading_logic()


def main():
    parser = argparse.ArgumentParser(
        description="AI Trading Bot Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--summary', '-s', action='store_true', help='Quick summary only')
    parser.add_argument('--positions', '-p', action='store_true', help='Positions only')
    parser.add_argument('--performance', '-r', action='store_true', help='Performance only')
    parser.add_argument('--config', '-c', action='store_true', help='Show configuration')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON (for integrations)')

    args = parser.parse_args()

    dashboard = Dashboard()

    if args.json:
        # JSON output for integrations
        dashboard.initialize()
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": dashboard.config.model_dump() if dashboard.config else None,
            "positions": [],
            "performance": None
        }
        if dashboard.tracker:
            metrics = dashboard.tracker.get_metrics()
            output["performance"] = {
                "total_trades": metrics.total_trades,
                "win_rate": metrics.win_rate,
                "total_pnl": metrics.total_pnl,
            }
        print(json.dumps(output, indent=2, default=str))
    elif args.summary:
        dashboard.run_summary()
    elif args.positions:
        dashboard.run_positions_only()
    elif args.performance:
        dashboard.run_performance_only()
    elif args.config:
        dashboard.run_config_only()
    else:
        dashboard.run_full_dashboard()


if __name__ == "__main__":
    main()
