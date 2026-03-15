"""
BBC Telemetry Logger — v8.3
Yapılandırılmış JSON event loglama sistemi.

Tüm BBC operasyonları (heal, degenerate, session, analiz, inject)
burada izlenebilir event'ler olarak kaydedilir.

Log dosyası: .bbc/logs/telemetry.jsonl
Format: Her satır bağımsız bir JSON nesnesi (JSON Lines)

Kullanım:
    from .telemetry import get_telemetry
    tele = get_telemetry()
    tele.log_event("HEAL_APPROVED", {"source": "hmpu_core", "remaining": 99})
"""
import os
import json
from datetime import datetime
from pathlib import Path
from .bbc_logger import get_log_dir, get_logger

logger = get_logger("BBC_Telemetry")

# Desteklenen event türleri (dokümantasyon amaçlı, zorunlu değil)
EVENT_TYPES = {
    # Session lifecycle
    "SESSION_START",
    "SESSION_END",
    "SESSION_RESET",
    # Heal mekanizması
    "HEAL_APPROVED",
    "HEAL_DENIED",
    "HEAL_CONSUMED",
    # Kritik durumlar
    "DEGENERATE",
    # Token metrikleri
    "TOKEN_UPDATE",
    "FILES_PROCESSED",
    # Analiz & Inject
    "ANALYZE_START",
    "ANALYZE_COMPLETE",
    "INJECT_START",
    "INJECT_COMPLETE",
    # Hata & Uyarı
    "ERROR",
    "WARNING",
}


class TelemetryLogger:
    """
    BBC Telemetry — Yapılandırılmış event loglama.

    Her event şu formatta .bbc/logs/telemetry.jsonl dosyasına yazılır:
    {"ts": "2026-02-20T17:43:00", "event": "HEAL_APPROVED", "data": {...}, "session": "20260220_174300"}
    """

    def __init__(self, log_path=None):
        if log_path is None:
            log_path = os.path.join(get_log_dir(), "telemetry.jsonl")
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        self.log_path = log_path
        self.session_id = None
        self._event_count = 0

    def set_session(self, session_id: str):
        """Aktif session ID'yi ayarla."""
        self.session_id = session_id

    def log_event(self, event_type: str, data: dict = None):
        """
        Yapılandırılmış bir event kaydet.

        Args:
            event_type: Event türü (SESSION_START, HEAL_APPROVED, vb.)
            data: Event'e özel ek veriler (opsiyonel)
        """
        event = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "event": event_type,
            "data": data or {},
        }
        if self.session_id:
            event["session"] = self.session_id

        self._event_count += 1

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except (OSError, PermissionError) as e:
            logger.warning(f"Telemetry write failed: {e}")

    def get_event_count(self) -> int:
        """Bu instance'ın toplam yazdığı event sayısı."""
        return self._event_count

    def get_recent_events(self, limit: int = 20) -> list:
        """
        Son N event'i oku ve döndür.

        Args:
            limit: Döndürülecek maksimum event sayısı

        Returns:
            Event dict listesi (en yenisi sonda)
        """
        if not os.path.exists(self.log_path):
            return []

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            events = []
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return events
        except (OSError, PermissionError):
            return []


    # ------------------------------------------------------------------
    # Feedback Telemetry — Command Performance Tracking (v8.6)
    # ------------------------------------------------------------------

    def log_command(self, command: str, duration_sec: float,
                    files: int = 0, tokens_saved: int = 0,
                    savings_pct: float = 0.0, mode: str = None,
                    success: bool = True, extra: dict = None):
        """
        Log a BBC command execution with performance metrics.
        This powers the 'bbc telemetry' summary dashboard.
        """
        data = {
            "command": command,
            "duration_sec": round(duration_sec, 3),
            "files": files,
            "tokens_saved": tokens_saved,
            "savings_pct": round(savings_pct, 1),
            "success": success,
        }
        if mode:
            data["mode"] = mode
        if extra:
            data.update(extra)
        self.log_event("COMMAND_COMPLETE", data)

    def get_command_history(self, limit: int = 100) -> list:
        """Return recent COMMAND_COMPLETE events."""
        all_events = self.get_recent_events(limit=500)
        return [e for e in all_events if e.get("event") == "COMMAND_COMPLETE"][-limit:]

    def generate_summary(self) -> dict:
        """
        Generate a telemetry summary from all logged command events.
        Returns aggregated stats: total commands, total time, total tokens saved,
        command breakdown, avg duration per command, trend data.
        """
        history = self.get_command_history(limit=1000)
        if not history:
            return {
                "total_commands": 0,
                "total_duration_sec": 0,
                "total_tokens_saved": 0,
                "commands": {},
                "recent": [],
            }

        total_cmds = len(history)
        total_duration = sum(e.get("data", {}).get("duration_sec", 0) for e in history)
        total_tokens = sum(e.get("data", {}).get("tokens_saved", 0) for e in history)
        total_files = sum(e.get("data", {}).get("files", 0) for e in history)
        successes = sum(1 for e in history if e.get("data", {}).get("success", True))

        # Per-command breakdown
        cmd_stats = {}
        for e in history:
            d = e.get("data", {})
            cmd = d.get("command", "unknown")
            if cmd not in cmd_stats:
                cmd_stats[cmd] = {"count": 0, "total_sec": 0, "tokens_saved": 0, "files": 0}
            cmd_stats[cmd]["count"] += 1
            cmd_stats[cmd]["total_sec"] += d.get("duration_sec", 0)
            cmd_stats[cmd]["tokens_saved"] += d.get("tokens_saved", 0)
            cmd_stats[cmd]["files"] += d.get("files", 0)

        for cmd in cmd_stats:
            c = cmd_stats[cmd]
            c["avg_sec"] = round(c["total_sec"] / c["count"], 3) if c["count"] > 0 else 0
            c["total_sec"] = round(c["total_sec"], 3)

        # Recent 10
        recent = []
        for e in history[-10:]:
            d = e.get("data", {})
            recent.append({
                "ts": e.get("ts", ""),
                "command": d.get("command", "?"),
                "duration": d.get("duration_sec", 0),
                "tokens_saved": d.get("tokens_saved", 0),
                "success": d.get("success", True),
            })

        return {
            "total_commands": total_cmds,
            "total_duration_sec": round(total_duration, 2),
            "total_tokens_saved": total_tokens,
            "total_files_processed": total_files,
            "success_rate": round(successes / total_cmds * 100, 1) if total_cmds > 0 else 0,
            "commands": cmd_stats,
            "recent": recent,
        }


# ─── Global singleton ───────────────────────────────────────
_global_telemetry = None


def get_telemetry() -> TelemetryLogger:
    """Global TelemetryLogger instance'ını döndür."""
    global _global_telemetry
    if _global_telemetry is None:
        _global_telemetry = TelemetryLogger()
    return _global_telemetry
