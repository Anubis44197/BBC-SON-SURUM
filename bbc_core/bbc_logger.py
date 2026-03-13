"""
BBC Central Logger — v8.3
Tüm BBC modülleri için tek merkezi loglama noktası.

Kullanım:
    from .bbc_logger import get_logger
    logger = get_logger("ModuleName")
    logger.info("mesaj")

Konfigürasyon:
    BBC_LOG_LEVEL env değişkeni ile log seviyesi ayarlanır (varsayılan: INFO)
    Log dosyası: .bbc/logs/bbc_math.log
    Konsol çıktısı: sadece WARNING ve üstü
"""
import logging
import os

# BBC isolation: all logs go to .bbc/logs/
_BBC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BBC_LOG_DIR = os.path.join(_BBC_ROOT, '.bbc', 'logs')
_initialized = False


def _init_logging():
    """Loglama altyapısını bir kez başlat."""
    global _initialized
    if _initialized:
        return

    os.makedirs(_BBC_LOG_DIR, exist_ok=True)

    log_level_str = os.getenv("BBC_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)

    root_logger = logging.getLogger()

    # Zaten handler varsa tekrar ekleme (çoklu init koruması)
    if not root_logger.handlers:
        root_logger.setLevel(log_level)

        # 1. Dosya handler — tüm log seviyeleri
        try:
            file_handler = logging.FileHandler(
                os.path.join(_BBC_LOG_DIR, "bbc_math.log"),
                encoding="utf-8"
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # Dosyaya yazılamıyorsa sessizce devam et
            import sys
            print(f"[BBC Logger] File handler error: {e}", file=sys.stderr)

        # 2. Konsol handler — sadece WARNING ve üstü (kullanıcıyı rahatsız etmemek için)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    _initialized = True


def get_logger(name="BBC"):
    """
    BBC merkezi logger'ını döndür.

    Args:
        name: Logger ismi (modül adı önerilir, örn. "BBC_StateManager")

    Returns:
        logging.Logger instance
    """
    _init_logging()
    return logging.getLogger(name)


def get_log_dir():
    """BBC log dizinini döndür (.bbc/logs/)"""
    os.makedirs(_BBC_LOG_DIR, exist_ok=True)
    return _BBC_LOG_DIR
