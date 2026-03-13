import json
import asyncio
from .native_adapter import BBCNativeAdapter as NewNativeAdapter

class BBCNativeAdapter:
    """
    BBC v8.3 Modernized Adapter (Wrapper for NewNativeAdapter)
    Provides backward compatibility for legacy tool calls while using the v8.3 engine.
    """
    
    def __init__(self, project_root: str = "."):
        self.internal = NewNativeAdapter(project_root=project_root)
        self.state_manager = self.internal.state_manager
        self.stats = {"files_analyzed": 0, "total_bytes": 0}
        
    async def analyze_project(self, target_root, silent=True):
        """Projeyi analiz et ve recipe oluştur (v8.3 Engine)"""
        context_json = await self.internal.analyze_project(target_root, silent=silent)
        
        # İstatistikleri güncelle (Legacy uyumluluk için)
        metrics = context_json.get("metrics", {})
        self.stats["files_analyzed"] = metrics.get("files_scanned", 0)
        self.stats["total_bytes"] = metrics.get("raw_bytes", 0)
        
        return context_json
    
    async def create_recipe_from_project(self, target_root, output_file="bbc_context.json"):
        """Projeden recipe oluştur ve kaydet (v8.3 Engine)"""
        # Projeyi analiz et
        analysis = await self.analyze_project(target_root, silent=False)
        
        # Recipe'yi kaydet
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        # State manager'a kaydet
        self.state_manager.increment_recipes_created()
        
        return {
            "success": True,
            "recipe_file": output_file,
            "files_analyzed": analysis["metrics"]["files_scanned"],
            "total_bytes": analysis["metrics"]["raw_bytes"]
        }
    
    def get_stats(self):
        """Mevcut istatistikleri getir"""
        return {
            "session_stats": self.stats,
            "persistent_stats": self.state_manager.get_stats()
        }

# Geriye dönük uyumluluk için fonksiyon alias'ları (v7.2 Legacy Support)
async def create_recipe_tool(target_root, output_file="bbc_context.json"):
    adapter = BBCNativeAdapter()
    return await adapter.create_recipe_from_project(target_root, output_file)

def get_stats_tool():
    adapter = BBCNativeAdapter()
    return adapter.get_stats()

if __name__ == "__main__":
    async def main():
        adapter = BBCNativeAdapter()
        result = await adapter.analyze_project(".")
        print(f"[*] Analysis complete. Files: {result['metrics']['files_scanned']}")
    
    asyncio.run(main())
