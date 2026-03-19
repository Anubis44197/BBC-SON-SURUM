import os
import json

class BBCMigratorEngine:
    def __init__(self, recipe_path: str):
        self.recipe_path = recipe_path
        self.recipe = self._load_recipe()

    def _load_recipe(self):
        if not os.path.exists(self.recipe_path):
            raise FileNotFoundError(f"Recipe file not found: {self.recipe_path}")
        print(f"[*] Loading recipe from: {self.recipe_path}")
        with open(self.recipe_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def build_dependency_graph(self):
        """
        Builds a simple dependency graph from the 'imports' section of the recipe.
        Returns a dict: {file_path: [dependencies]}
        """
        graph = {}
        
        skeleton = self.recipe.get("project_skeleton", {}).get("hierarchy", [])
        structures = self.recipe.get("code_structure", [])

        # Fallback to paths from code_structure when hierarchy is summarized/truncated.
        if not skeleton or len(skeleton) < len(structures):
            skeleton = [
                s.get("path", "") for s in structures
                if isinstance(s, dict) and s.get("path")
            ]
        
        # Mapping filename to index for fast lookup
        file_to_idx = {f: i for i, f in enumerate(skeleton)}
        
        for idx, file_path in enumerate(skeleton):
            deps = set()
            if idx < len(structures):
                raw_imports = structures[idx].get("imports", [])
                
                # Heuristic dependency resolution
                for imp in raw_imports:
                    # Clean import string (e.g., "import os" -> "os", "from .utils import x" -> ".utils")
                    # This is a very basic heuristic.
                    parts = imp.replace("import ", "").replace("from ", "").split(" ")
                    candidate = parts[0]
                    
                    # Check against all other files
                    # In a real scenario, this would be more robust (trie or map)
                    # For now, we check if the candidate module name matches a file stem
                    for potential_file in skeleton:
                        if potential_file == file_path:
                            continue
                            
                        potential_stem = os.path.splitext(os.path.basename(potential_file))[0]
                        
                        # Match "utils" with "utils.py"
                        if candidate == potential_stem or candidate.endswith(f".{potential_stem}"):
                            deps.add(potential_file)
                            
            graph[file_path] = list(deps)
            
        return graph

    def topological_sort(self, graph):
        """
        Returns a list of files in execution order (Dependencies FIRST).
        """
        visited = set()
        stack = []
        
        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for neighbor in graph.get(node, []):
                visit(neighbor)
            stack.append(node)

        for node in graph:
            visit(node)
            
        # Stack contains items in topological sort order (dependencies first) due to post-order traversal logic
        # Wait, usually DFS post-order gives [Leaf, ..., Root]. 
        # So Leaf (Dependency) comes first. This is exactly what we want for migration.
        # We want to migrate 'utils.py' (Leaf) before 'main.py' (Root).
        return stack

    def plan_migration(self, target_lang: str):
        skeleton = self.recipe.get('project_skeleton', {})
        file_count = int(skeleton.get('file_count', len(skeleton.get('hierarchy', []))))
        print(f"[*] Building Dependency Graph for {file_count} files...")
        
        try:
            graph = self.build_dependency_graph()
            
            print(f"[*] Calculating Topological Sort (Optimization Strategy)...")
            order = self.topological_sort(graph)
            
            print(f"\nBBC MIGRATION ENGINE - EXECUTION PLAN ({target_lang})")
            print("="*70)
            print(f"Target Project: {os.path.basename(self.recipe.get('project_skeleton', {}).get('root', 'Unknown'))}")
            print(f"Total Modules: {len(order)}")
            print(f"Strategy: Bottom-Up (Leaves -> Root)")
            print("="*70)
            
            # Show plan sample
            limit = 10
            if len(order) > limit:
                print(f"--- BASE LAYER (First 5) ---")
                for i in range(5):
                    print(f" [Step {i+1}] {order[i]}")
                print(f"\n ... ({len(order)-10} modules hidden) ...\n")
                print(f"--- APPLICATION LAYER (Last 5) ---")
                for i in range(len(order)-5, len(order)):
                    print(f" [Step {i+1}] {order[i]}")
            else:
                for i, f in enumerate(order):
                    print(f" [Step {i+1}] {f}")
            
            print("="*70)
            print(f"Ready to migrate. Run with --execute to perform actual migration.")
            return order
            
        except Exception as e:
            print(f"Error during planning: {str(e)}")
            return []
