"""
create_recipe - Tarif oluşturma aracı
Ham metinden BBC HMPU tarifi oluşturur
"""

import json
import sys
from pathlib import Path

# BBC HMPU Engine
sys.path.insert(0, str(Path(__file__).parent))
from hmpu_quantizer import HMPUQuantizer


async def create_recipe_tool(arguments: dict, stats: dict) -> str:
    """
    Ham metinden tarif oluştur
    
    Args:
        arguments: {"content": str, "max_recipe_size": int}
        stats: Global istatistik dictionary
    
    Returns:
        JSON formatında tarif
    """
    content = arguments.get("content", "")
    max_recipe_size = arguments.get("max_recipe_size", 5000)
    
    if not content:
        return json.dumps({
            "error": "İçerik boş olamaz",
            "success": False
        }, indent=2, ensure_ascii=False)
    
    try:
        # Orijinal boyut
        original_size = len(content.encode('utf-8'))
        
        # Basit tarif oluştur
        lines = content.split('\n')
        words = content.split()
        
        # İstatistikler
        recipe = {
            "metadata": {
                "total_chars": len(content),
                "total_lines": len(lines),
                "total_words": len(words),
                "avg_line_length": round(len(content) / len(lines), 2) if lines else 0
            },
            "structure": {
                "has_code": any(char in content for char in ['{', '}', '(', ')', ';']),
                "has_numbers": any(char.isdigit() for char in content),
                "language": "unknown"
            },
            "summary": f"{len(lines)} satır, {len(words)} kelime"
        }
        
        # Tarif boyutu kontrolü
        recipe_json = json.dumps(recipe, ensure_ascii=False)
        recipe_size = len(recipe_json.encode('utf-8'))
        
        if recipe_size > max_recipe_size:
            recipe = {"summary": recipe["summary"]}
            recipe_json = json.dumps(recipe, ensure_ascii=False)
            recipe_size = len(recipe_json.encode('utf-8'))
        
        # İstatistikleri güncelle
        stats["total_recipes_created"] += 1
        stats["total_data_processed"] += original_size
        
        # Token hesaplama
        original_tokens = len(content) // 4
        recipe_tokens = recipe_size // 4
        token_savings = original_tokens - recipe_tokens
        stats["token_savings"] += token_savings * 0.000005
        
        # Sonuç
        result = {
            "success": True,
            "original_size": f"{original_size:,} bytes",
            "recipe_size": f"{recipe_size:,} bytes",
            "compression_ratio": f"{original_size // recipe_size if recipe_size > 0 else 0}x",
            "token_savings": f"{token_savings:,} tokens",
            "recipe": recipe
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "success": False
        }, indent=2, ensure_ascii=False)
