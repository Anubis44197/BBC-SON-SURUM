"""
BBC Terminal Live Monitor
Compact 4-line professional terminal display
"""

import sys
import time
import threading
from .realtime_token_counter import get_token_counter, TokenMetrics


class TerminalMonitor:
    """Compact terminal monitoring interface"""

    def __init__(self, update_interval: float = 1.0):
        self.update_interval = update_interval
        self.is_running = False
        self.monitor_thread = None
        self.last_display = ""
        self.start_time = None

    def start_monitoring(self):
        """Start live monitoring"""
        if self.is_running:
            return

        self.is_running = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        get_token_counter().add_callback(self._on_metrics_update)

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._update_display()
                time.sleep(self.update_interval)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(2.0)

    def _on_metrics_update(self, metrics: TokenMetrics):
        """Metrics update callback"""
        self._update_display()

    def _format_duration(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _build_bar(self, percent: float, width: int = 40) -> str:
        """Build progress bar string"""
        filled = int(width * percent / 100)
        empty = width - filled
        return "\u2501" * filled + "\u2500" * empty

    def _update_display(self):
        """Update terminal display without clearing screen"""
        metrics = get_token_counter().get_metrics()
        if not metrics:
            return

        display = self._create_compact_display(metrics)

        if display != self.last_display:
            # Move cursor up and overwrite (no screen clear)
            if self.last_display:
                lines = self.last_display.count("\n")
                sys.stdout.write(f"\033[{lines}A\033[J")
            sys.stdout.write(display)
            sys.stdout.flush()
            self.last_display = display

    def _create_compact_display(self, metrics: TokenMetrics) -> str:
        """Create compact 4-line professional display"""
        # Colors
        g = "\033[92m"   # green
        y = "\033[93m"   # yellow
        c = "\033[96m"   # cyan
        w = "\033[97m"   # white
        d = "\033[90m"   # dim
        r = "\033[0m"    # reset

        # Duration
        elapsed = time.time() - self.start_time if self.start_time else 0
        duration = self._format_duration(elapsed)

        # Token prediction: estimate normal usage as used + saved
        normal_tokens = metrics.tokens_used + metrics.tokens_saved
        if normal_tokens == 0:
            normal_tokens = 0

        # Savings
        saved = metrics.tokens_saved
        saved_pct = (saved / normal_tokens * 100) if normal_tokens > 0 else 0

        # Progress bar based on savings ratio
        bar_pct = min(100, saved_pct)
        bar = self._build_bar(bar_pct, 40)

        # Bar color based on efficiency
        bar_color = g if saved_pct >= 50 else (y if saved_pct >= 20 else "\033[91m")

        # Compression ratio
        ratio = (normal_tokens / metrics.tokens_used) if metrics.tokens_used > 0 else 1.0

        # Average speed per file
        speed = (elapsed / metrics.files_processed) if metrics.files_processed > 0 else 0

        # Status color
        status = metrics.status
        sc = g if status == "ACTIVE" else (y if status == "WARNING" else "\033[91m")

        # Build 4-line compact display
        line1 = f"{d}\u250c\u2500 BBC \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510{r}\n"
        line2 = f"{d}\u2502{r} {bar_color}{bar}{r} {w}{bar_pct:.0f}%{r}  {duration}  {sc}{status}{r} {d}\u2502{r}\n"
        line3 = f"{d}\u2502{r} {w}used:{r} {c}{metrics.tokens_used:,}{r}    {w}normal:{r} {c}{normal_tokens:,}{r}    {w}saved:{r} {g}{saved:,} ({saved_pct:.1f}%){r} {d}\u2502{r}\n"
        line4 = f"{d}\u2502{r} {w}files:{r} {c}{metrics.files_processed}{r}       {w}time:{r} {c}{duration}{r}       {w}ratio:{r} {g}{ratio:.1f}x{r}   {w}speed:{r} {c}{speed:.1f}s{r} {d}\u2502{r}\n"
        line5 = f"{d}\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518{r}\n"

        return line1 + line2 + line3 + line4 + line5

    def print_summary(self, metrics: TokenMetrics):
        """Print final session summary"""
        g = "\033[92m"
        c = "\033[96m"
        w = "\033[97m"
        d = "\033[90m"
        r = "\033[0m"

        elapsed = time.time() - self.start_time if self.start_time else 0
        duration = self._format_duration(elapsed)

        normal_tokens = metrics.tokens_used + metrics.tokens_saved
        saved_pct = (metrics.tokens_saved / normal_tokens * 100) if normal_tokens > 0 else 0
        ratio = (normal_tokens / metrics.tokens_used) if metrics.tokens_used > 0 else 1.0

        print(f"\n{d}{'=' * 58}{r}")
        print(f"{w}  BBC SESSION COMPLETE{r}")
        print(f"{d}{'=' * 58}{r}")
        print(f"  {w}used:{r} {c}{metrics.tokens_used:,}{r}  {w}normal:{r} {c}{normal_tokens:,}{r}  {w}saved:{r} {g}{metrics.tokens_saved:,} ({saved_pct:.1f}%){r}")
        print(f"  {w}files:{r} {c}{metrics.files_processed}{r}  {w}time:{r} {c}{duration}{r}  {w}ratio:{r} {g}{ratio:.1f}x{r}  {w}status:{r} {g}{metrics.status}{r}")
        print(f"{d}{'=' * 58}{r}\n")


# Global instance
_global_monitor = None


def get_terminal_monitor() -> TerminalMonitor:
    """Get global terminal monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = TerminalMonitor()
    return _global_monitor


def start_live_monitoring():
    """Start live monitoring (global)"""
    get_terminal_monitor().start_monitoring()


def stop_live_monitoring():
    """Stop live monitoring (global)"""
    get_terminal_monitor().stop_monitoring()


def print_final_summary():
    """Print final summary (global)"""
    metrics = get_token_counter().get_metrics()
    if metrics:
        get_terminal_monitor().print_summary(metrics)
