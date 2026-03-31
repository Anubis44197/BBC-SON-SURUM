"""
BBC Structure Manager - Auto-creates and manages .bbc directory structure
Ensures all required subdirectories exist when BBC initializes
"""

import os
from pathlib import Path
from typing import Dict, Optional


class BBCStructureManager:
    """
    Manages .bbc directory structure and ensures all subdirectories exist.
    Auto-creates folders on initialization: cache, indices, logs, manifest, skills
    """
    
    # Required subdirectories under .bbc/
    REQUIRED_SUBDIRS = {
        "cache": "Cached parse results and AST trees for faster re-analysis",
        "indices": "Fast symbol lookup indices and dependency graphs",
        "logs": "Telemetry and event logs (HEAL, DEGENERATE, etc.)",
        "manifest": "Injection manifest tracking which files were created",
        "skills": "Auto-generated project-specific skill files"
    }
    
    def __init__(self, project_root: str):
        """
        Initialize BBC structure manager
        
        Args:
            project_root: Absolute path to project root
        """
        self.project_root = Path(project_root).resolve()
        self.bbc_dir = self.project_root / ".bbc"
    
    def ensure_structure(self) -> Dict[str, Path]:
        """
        Ensure .bbc directory and all subdirectories exist.
        Creates them if missing.
        
        Returns:
            Dict mapping subdirectory name to absolute Path
        """
        # Create main .bbc directory
        self.bbc_dir.mkdir(parents=True, exist_ok=True)
        
        # Create all required subdirectories
        created_dirs = {}
        for subdir_name, description in self.REQUIRED_SUBDIRS.items():
            subdir_path = self.bbc_dir / subdir_name
            subdir_path.mkdir(parents=True, exist_ok=True)
            created_dirs[subdir_name] = subdir_path
        
        return created_dirs
    
    def get_cache_dir(self) -> Path:
        """Get cache directory path (creates if missing)"""
        cache_dir = self.bbc_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def get_indices_dir(self) -> Path:
        """Get indices directory path (creates if missing)"""
        indices_dir = self.bbc_dir / "indices"
        indices_dir.mkdir(parents=True, exist_ok=True)
        return indices_dir
    
    def get_logs_dir(self) -> Path:
        """Get logs directory path (creates if missing)"""
        logs_dir = self.bbc_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir
    
    def get_manifest_dir(self) -> Path:
        """Get manifest directory path (creates if missing)"""
        manifest_dir = self.bbc_dir / "manifest"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        return manifest_dir
    
    def get_skills_dir(self) -> Path:
        """Get skills directory path (creates if missing)"""
        skills_dir = self.bbc_dir / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        return skills_dir
    
    def get_cache_file(self, filename: str) -> Path:
        """Get path to file in cache directory"""
        return self.get_cache_dir() / filename
    
    def get_index_file(self, filename: str) -> Path:
        """Get path to file in indices directory"""
        return self.get_indices_dir() / filename
    
    def get_log_file(self, filename: str) -> Path:
        """Get path to file in logs directory"""
        return self.get_logs_dir() / filename
    
    def get_manifest_file(self, filename: str) -> Path:
        """Get path to file in manifest directory"""
        return self.get_manifest_dir() / filename
    
    def get_skill_file(self, filename: str) -> Path:
        """Get path to file in skills directory"""
        return self.get_skills_dir() / filename
    
    def verify_structure(self) -> bool:
        """
        Verify all required subdirectories exist
        
        Returns:
            True if all subdirectories exist, False otherwise
        """
        if not self.bbc_dir.exists():
            return False
        
        for subdir_name in self.REQUIRED_SUBDIRS.keys():
            subdir_path = self.bbc_dir / subdir_name
            if not subdir_path.exists() or not subdir_path.is_dir():
                return False
        
        return True
    
    def get_structure_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get information about .bbc directory structure
        
        Returns:
            Dict with info about each subdirectory (exists, file_count, description)
        """
        info = {}
        
        for subdir_name, description in self.REQUIRED_SUBDIRS.items():
            subdir_path = self.bbc_dir / subdir_name
            exists = subdir_path.exists()
            
            file_count = 0
            if exists:
                try:
                    file_count = len(list(subdir_path.iterdir()))
                except Exception:
                    file_count = -1
            
            info[subdir_name] = {
                "exists": exists,
                "path": str(subdir_path),
                "file_count": file_count,
                "description": description
            }
        
        return info
    
    def clean_empty_dirs(self) -> int:
        """
        Remove empty subdirectories (except required ones)
        
        Returns:
            Number of directories removed
        """
        removed_count = 0
        
        if not self.bbc_dir.exists():
            return 0
        
        for item in self.bbc_dir.iterdir():
            if not item.is_dir():
                continue
            
            # Don't remove required subdirectories
            if item.name in self.REQUIRED_SUBDIRS:
                continue
            
            # Remove if empty
            try:
                if not any(item.iterdir()):
                    item.rmdir()
                    removed_count += 1
            except Exception:
                pass
        
        return removed_count


def ensure_bbc_structure(project_root: str) -> BBCStructureManager:
    """
    Convenience function to ensure BBC structure exists
    
    Args:
        project_root: Project root path
    
    Returns:
        BBCStructureManager instance with structure ensured
    """
    manager = BBCStructureManager(project_root)
    manager.ensure_structure()
    return manager
