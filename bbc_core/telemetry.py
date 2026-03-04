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


# ─── Global singleton ───────────────────────────────────────
_global_telemetry = None


def get_telemetry() -> TelemetryLogger:
    """Global TelemetryLogger instance'ını döndür."""
    global _global_telemetry
    if _global_telemetry is None:
        _global_telemetry = TelemetryLogger()
    return _global_telemetry
