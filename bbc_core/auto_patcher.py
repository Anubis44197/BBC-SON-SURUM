"""
BBC Auto Patcher (v1.0)
CVP violation veya state bozulması tespit edildiğinde otomatik düzeltme
patch'i üretir ve güvenle uygular.

BBC Matematiği:
  - BBCScalar state-based healing: DEGENERATE → OmegaOperator → WEAK
  - Shannon Chaos Density: patch öncesi/sonrası kaos karşılaştırması
  - Aura Field Score: patch kalite doğrulaması
  - Constraint Violation Protocol: ihlal → patch → doğrulama döngüsü
"""

import json
import math
import os
import re
import shutil
import time
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .bbc_scalar import BBCScalar, STABLE, WEAK, UNSTABLE, DEGENERATE, OmegaOperator


class PatchAction:
    """Tek bir patch işlemi."""
    def __init__(self, file_path: str, action_type: str, description: str,
                 old_content: Optional[str] = None, new_content: Optional[str] = None,
                 line_start: Optional[int] = None, line_end: Optional[int] = None):
        self.file_path = file_path
        self.action_type = action_type      # "replace", "insert", "delete", "rename_symbol"
        self.description = description
        self.old_content = old_content
        self.new_content = new_content
        self.line_start = line_start
        self.line_end = line_end
        self.applied = False
        self.backup_path = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "action": self.action_type,
            "description": self.description,
            "applied": self.applied
        }


class AutoPatcher:
    """
    BBC Auto Patcher — state bozulması ve CVP ihlallerini otomatik düzeltir.

    Kullanım:
        patcher = AutoPatcher(recipe_path, project_root)
        report = patcher.analyze_and_patch(dry_run=True)  # Önizleme
        report = patcher.analyze_and_patch(dry_run=False)  # Uygula
    """

    def __init__(self, recipe_path: str, project_root: str):
        self.recipe_path = recipe_path
        self.project_root = os.path.abspath(project_root)
        self.context = {}
        self.patches: List[PatchAction] = []
        self._load_context()

    def _load_context(self):
        """BBC context'i yükle."""
        if not os.path.exists(self.recipe_path):
            return
        with open(self.recipe_path, "r", encoding="utf-8") as f:
            self.context = json.load(f)

    # ─── BBC Matematik: Shannon Chaos ──────────────────────────────

    def _calculate_chaos(self, text: str) -> BBCScalar:
        """Shannon Chaos Density — BBCScalar native."""
        if not text or not isinstance(text, str):
            return BBCScalar(0.0, state=STABLE, metadata={"origin": "math"})
        cnt = Counter(text)
        ln = len(text)
        entropy = sum(-(v / ln) * math.log2(v / ln) for v in cnt.values())
        if math.isnan(entropy):
            entropy = 0.0
        state = STABLE if entropy <= 3.0 else WEAK if entropy <= 5.0 else UNSTABLE if entropy <= 7.0 else DEGENERATE
        return BBCScalar(entropy, state=state, metadata={"origin": "math"})

    # ─── Sorun Tespit ──────────────────────────────────────────────

    def detect_unused_imports(self, file_path: str, content: str) -> List[PatchAction]:
        """Kullanılmayan import'ları tespit et."""
        patches = []
        lines = content.split("\n")
        import_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'^(?:import|from)\s+', stripped):
                # import edilen modülün adını çıkar
                m = re.match(r'^import\s+(\w+)', stripped)
                if m:
                    module = m.group(1)
                    # Dosyanın geri kalanında kullanılıyor mu?
                    rest = "\n".join(lines[:i] + lines[i+1:])
                    if module not in rest and module not in ["os", "sys", "json", "re", "math"]:
                        patches.append(PatchAction(
                            file_path=file_path,
                            action_type="delete",
                            description=f"Unused import: {module}",
                            old_content=line,
                            new_content="",
                            line_start=i + 1,
                            line_end=i + 1
                        ))
        return patches

    def detect_degenerate_patterns(self, file_path: str, content: str) -> List[PatchAction]:
        """Kod kalitesini bozan dejenere kalıpları tespit et."""
        patches = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Boş except (tüm hataları yutan)
            if re.match(r'^\s*except\s*:', line):
                indent = len(line) - len(line.lstrip())
                patches.append(PatchAction(
                    file_path=file_path,
                    action_type="replace",
                    description="Bare except → except Exception (BBC CVP: catch-all violation)",
                    old_content=line,
                    new_content=" " * indent + "except Exception:",
                    line_start=i + 1,
                    line_end=i + 1
                ))

            # pass-only except bloğu
            if re.match(r'^\s*except.*:\s*$', line):
                if i + 1 < len(lines) and lines[i + 1].strip() == "pass":
                    indent = len(lines[i + 1]) - len(lines[i + 1].lstrip())
                    patches.append(PatchAction(
                        file_path=file_path,
                        action_type="replace",
                        description="Silent except pass → logging (BBC CVP: silent failure violation)",
                        old_content=lines[i + 1],
                        new_content=" " * indent + "pass  # BBC: Consider logging this exception",
                        line_start=i + 2,
                        line_end=i + 2
                    ))

        return patches

    def detect_symbol_drift(self) -> List[PatchAction]:
        """
        Context'teki semboller ile dosyadaki semboller arasındaki drift'i tespit et.
        Drift = context'te var ama dosyada artık yok olan semboller → stale context.
        """
        patches = []

        for entry in self.context.get("code_structure", []):
            path = entry.get("path", "")
            structure = entry.get("structure", {})
            full_path = os.path.join(self.project_root, path)

            if not os.path.exists(full_path):
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    current_content = f.read()
            except Exception:
                continue

            # Context'teki fonksiyonlar
            ctx_funcs = set(structure.get("functions", []))
            ctx_classes = set(structure.get("classes", []))

            # Dosyadaki mevcut fonksiyonlar (basit regex)
            current_funcs = set(re.findall(r'^\s*def\s+(\w+)', current_content, re.MULTILINE))
            current_classes = set(re.findall(r'^\s*class\s+(\w+)', current_content, re.MULTILINE))

            # Drift: context'te var ama dosyada yok
            missing_funcs = ctx_funcs - current_funcs
            missing_classes = ctx_classes - current_classes

            if missing_funcs or missing_classes:
                patches.append(PatchAction(
                    file_path=path,
                    action_type="reseal",
                    description=f"Symbol drift detected: {len(missing_funcs)} functions, {len(missing_classes)} classes removed since last seal"
                ))

        return patches

    # ─── Patch Üretimi ─────────────────────────────────────────────

    def generate_patches(self) -> List[PatchAction]:
        """Tüm dosyaları tara ve patch'leri üret."""
        self.patches = []

        for entry in self.context.get("code_structure", []):
            path = entry.get("path", "")
            full_path = os.path.join(self.project_root, path)

            if not os.path.exists(full_path):
                continue

            # Sadece Python dosyaları (şimdilik)
            if not path.endswith(".py"):
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            # Sorun tespitleri
            self.patches.extend(self.detect_unused_imports(path, content))
            self.patches.extend(self.detect_degenerate_patterns(path, content))

        # Symbol drift
        self.patches.extend(self.detect_symbol_drift())

        return self.patches

    # ─── Patch Uygulama ────────────────────────────────────────────

    def _backup_file(self, file_path: str) -> str:
        """Dosyanın yedeğini al."""
        full_path = os.path.join(self.project_root, file_path)
        backup_dir = os.path.join(self.project_root, ".bbc", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(file_path)}.{timestamp}.bak"
        backup_path = os.path.join(backup_dir, backup_name)
        shutil.copy2(full_path, backup_path)
        return backup_path

    def apply_patch(self, patch: PatchAction, dry_run: bool = True) -> Dict[str, Any]:
        """
        Tek bir patch'i uygula.

        BBC Matematiği:
          - Patch öncesi chaos → BBCScalar
          - Patch sonrası chaos → BBCScalar
          - dC = |chaos_after - chaos_before| → eğer artıyorsa ROLLBACK
          - State propagation: patch sonucu STABLE mı?
        """
        full_path = os.path.join(self.project_root, patch.file_path)

        if patch.action_type == "reseal":
            return {
                "patch": patch.to_dict(),
                "action": "RESEAL_NEEDED",
                "message": f"Run 'bbc analyze' to reseal {patch.file_path}",
                "applied": False
            }

        if not os.path.exists(full_path):
            return {
                "patch": patch.to_dict(),
                "error": f"File not found: {full_path}",
                "applied": False
            }

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"patch": patch.to_dict(), "error": str(e), "applied": False}

        # Chaos before (BBCScalar)
        chaos_before = self._calculate_chaos(content)

        # Patch uygula (in-memory)
        if patch.action_type == "replace" and patch.old_content is not None:
            if patch.old_content in content:
                new_content = content.replace(patch.old_content, patch.new_content or "", 1)
            else:
                return {"patch": patch.to_dict(), "error": "old_content not found", "applied": False}
        elif patch.action_type == "delete" and patch.old_content is not None:
            new_content = content.replace(patch.old_content + "\n", "", 1)
        else:
            return {"patch": patch.to_dict(), "error": f"Unsupported action: {patch.action_type}", "applied": False}

        # Chaos after (BBCScalar)
        chaos_after = self._calculate_chaos(new_content)

        # BBC Matematik: dC kontrolü — kaos artarsa ROLLBACK
        dc = BBCScalar(abs(float(chaos_after) - float(chaos_before)), metadata={"origin": "math"})
        chaos_increased = float(chaos_after) > float(chaos_before) + 0.5

        # State propagation: patch güvenli mi?
        patch_state = STABLE
        if chaos_increased:
            patch_state = UNSTABLE
        elif dc.state in [UNSTABLE, DEGENERATE]:
            patch_state = WEAK

        patch_quality = BBCScalar(
            1.0 - min(1.0, float(dc) / 8.0),
            state=patch_state,
            metadata={"origin": "math"}
        )

        # Heal denemesi
        if patch_quality.state in [UNSTABLE, DEGENERATE]:
            patch_quality = OmegaOperator.trigger(
                BBCScalar(patch_quality.value, state=patch_quality.state,
                          heal_count=patch_quality.heal_count,
                          metadata=patch_quality.metadata)
            )

        result = {
            "patch": patch.to_dict(),
            "chaos_before": {"value": round(float(chaos_before), 3), "state": chaos_before.state},
            "chaos_after": {"value": round(float(chaos_after), 3), "state": chaos_after.state},
            "chaos_delta": round(float(dc), 3),
            "patch_quality": {"value": round(float(patch_quality), 3), "state": patch_quality.state},
            "safe_to_apply": patch_quality.state in [STABLE, WEAK],
            "applied": False
        }

        if not dry_run and result["safe_to_apply"]:
            # Backup + atomic write
            backup = self._backup_file(patch.file_path)
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                patch.applied = True
                patch.backup_path = backup
                result["applied"] = True
                result["backup"] = backup
            except Exception as e:
                # Rollback
                shutil.copy2(backup, full_path)
                result["error"] = f"Write failed, rolled back: {e}"

        return result

    # ─── Ana Pipeline ──────────────────────────────────────────────

    def analyze_and_patch(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Tam patch pipeline'ı:
          1. Tüm dosyaları tara, sorunları tespit et
          2. Patch üret
          3. Her patch'i BBC matematiğiyle doğrula
          4. Güvenli olanları uygula (dry_run=False ise)

        Returns:
            Tam rapor: patches, applied, skipped, aura quality
        """
        patches = self.generate_patches()

        results = []
        applied_count = 0
        skipped_count = 0
        reseal_needed = []

        for patch in patches:
            if patch.action_type == "reseal":
                reseal_needed.append(patch.to_dict())
                continue
            result = self.apply_patch(patch, dry_run=dry_run)
            results.append(result)
            if result.get("applied"):
                applied_count += 1
            elif not result.get("safe_to_apply", True):
                skipped_count += 1

        # Genel kalite skoru — tüm patch'lerin quality ortalaması
        qualities = [r["patch_quality"]["value"] for r in results if "patch_quality" in r]
        if qualities:
            avg_quality = sum(qualities) / len(qualities)
            q_state = STABLE if avg_quality >= 0.8 else WEAK if avg_quality >= 0.5 else UNSTABLE
        else:
            avg_quality = 1.0
            q_state = STABLE

        overall_quality = BBCScalar(avg_quality, state=q_state, metadata={"origin": "math"})

        return {
            "mode": "dry_run" if dry_run else "apply",
            "total_patches": len(patches),
            "patch_results": results,
            "applied": applied_count,
            "skipped_unsafe": skipped_count,
            "reseal_needed": reseal_needed,
            "overall_quality": {
                "value": round(float(overall_quality), 3),
                "state": overall_quality.state
            }
        }
