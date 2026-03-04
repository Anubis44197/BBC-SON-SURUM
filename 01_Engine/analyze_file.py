"""
analyze_file - Dosya analizi aracı
Büyük dosyaları BBC HMPU ile analiz eder, küçük tarif döner
"""

import os
import json
import sys
from pathlib import Path

# BBC HMPU Engine
sys.path.insert(0, str(Path(__file__).parent))
from hmpu_quantizer import HMPUQuantizer


async def analyze_file_tool(arguments: dict, stats: dict) -> str:
    """
    Dosyayı analiz et ve tarif oluştur
    
    Args:
        arguments: {"file_path": str, "analysis_type": str}
        stats: Global istatistik dictionary
    
    Returns:
        JSON formatında analiz sonucu
    """
    file_path = arguments.get("file_path")
    analysis_type = arguments.get("analysis_type", "auto")
    
    # Dosya kontrolü
    if not os.path.exists(file_path):
        return json.dumps({
            "error": f"Dosya bulunamadı: {file_path}",
            "success": False
        }, indent=2, ensure_ascii=False)
    
    try:
        # Dosya boyutunu al
        file_size = os.path.getsize(file_path)
        
        # Dosyayı oku
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # BBC HMPU ile işle
        quantizer = HMPUQuantizer()
        
        # Basit tarif oluştur (şimdilik)
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Kritik pattern'leri bul (basit versiyon)
        patterns = {}
        keywords = ['error', 'exception', 'failed', 'critical', 'warning']
        
        for keyword in keywords:
            count = sum(1 for line in lines if keyword.lower() in line.lower())
            if count > 0:
                patterns[keyword] = count
        
        # Tarif oluştur
        recipe = {
            "file_info": {
                "path": file_path,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "total_lines": total_lines
            },
            "analysis": {
                "type": analysis_type,
                "patterns_found": patterns,
                "total_patterns": sum(patterns.values())
            },
            "recipe": {
                "critical_lines": list(patterns.keys()),
                "summary": f"{total_lines} satır analiz edildi, {sum(patterns.values())} pattern bulundu"
            }
        }
        
        # Tarif boyutu
        recipe_json = json.dumps(recipe, ensure_ascii=False)
        recipe_size = len(recipe_json.encode('utf-8'))
        
        # Tasarruf hesapla
        compression_ratio = file_size / recipe_size if recipe_size > 0 else 0
        
        # İstatistikleri güncelle
        stats["total_files_analyzed"] += 1
        stats["total_data_processed"] += file_size
        stats["total_recipes_created"] += 1
        
        # Token tahmini (basit: 1 token ≈ 4 karakter)
        original_tokens = len(content) // 4
        recipe_tokens = recipe_size // 4
        token_savings = original_tokens - recipe_tokens
        stats["token_savings"] += token_savings * 0.000005  # $0.000005 per token
        
        # Sonuç
        result = {
            "success": True,
            "file_path": file_path,
            "original_size": f"{file_size:,} bytes ({round(file_size / (1024 * 1024), 2)} MB)",
            "recipe_size": f"{recipe_size:,} bytes ({round(recipe_size / 1024, 2)} KB)",
            "compression_ratio": f"{compression_ratio:.0f}x",
            "token_estimate": {
                "original": f"{original_tokens:,} tokens",
                "recipe": f"{recipe_tokens:,} tokens",
                "savings": f"{token_savings:,} tokens ({round(token_savings / original_tokens * 100, 1)}%)"
            },
            "recipe": recipe
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "success": False
        }, indent=2, ensure_ascii=False)
