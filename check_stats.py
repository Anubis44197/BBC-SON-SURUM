#!/usr/bin/env python3
import sys
sys.path.insert(0, 'C:/Users/90535/Desktop/BBC-SON-SURUM-1')

from bbc_core.full_symbol_extractor import FullSymbolExtractor

e = FullSymbolExtractor('C:/Users/90535/Desktop/AutoResearchClaw')
stats = e.get_stats()

print(f"Tree-sitter: {stats['tree_sitter_available']}")
print(f"Diller: {len(stats['supported_languages'])} - {', '.join(stats['supported_languages'])}")
print(f"Cache dosyaları: {stats['cache_files']}")
print(f"Cache boyutu: {stats['cache_size_bytes'] / 1024:.1f} KB")
print(f"İndekslenmiş semboller: {stats['indexed_symbols']}")
