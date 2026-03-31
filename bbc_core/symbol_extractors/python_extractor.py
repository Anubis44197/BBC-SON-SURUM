"""
Python Symbol Extractor using Tree-sitter
Extracts classes, functions, imports with full context
"""

from typing import Dict, List, Any, Optional


class PythonExtractor:
    """Extract symbols from Python code using tree-sitter AST"""
    
    def extract(self, root_node, content: str) -> Dict[str, Any]:
        """
        Extract all Python symbols from AST
        
        Args:
            root_node: Tree-sitter root node
            content: Source code content
            
        Returns:
            Dict with classes, functions, imports, etc.
        """
        symbols = {
            "classes": [],
            "functions": [],
            "imports": [],
            "variables": [],
            "decorators": []
        }
        
        self._traverse(root_node, symbols, content, parent_class=None)
        return symbols
    
    def _traverse(self, node, symbols: Dict, content: str, parent_class: Optional[str] = None):
        """Recursively traverse AST and extract symbols"""
        
        if node.type == 'class_definition':
            class_info = self._extract_class(node, content)
            symbols['classes'].append(class_info)
            
            for child in node.children:
                self._traverse(child, symbols, content, parent_class=class_info['name'])
        
        elif node.type == 'function_definition':
            func_info = self._extract_function(node, content, parent_class)
            symbols['functions'].append(func_info)
        
        elif node.type in ('import_statement', 'import_from_statement'):
            import_info = self._extract_import(node, content)
            if import_info:
                symbols['imports'].append(import_info)
        
        elif node.type == 'decorated_definition':
            decorator_info = self._extract_decorator(node, content)
            if decorator_info:
                symbols['decorators'].append(decorator_info)
        
        else:
            for child in node.children:
                self._traverse(child, symbols, content, parent_class)
    
    def _extract_class(self, node, content: str) -> Dict[str, Any]:
        """Extract class information"""
        name_node = node.child_by_field_name('name')
        if not name_node:
            return {"name": "Unknown", "bases": [], "methods": [], "line": node.start_point[0] + 1}
        
        name = self._get_text(name_node, content)
        
        bases = []
        superclasses_node = node.child_by_field_name('superclasses')
        if superclasses_node:
            for child in superclasses_node.children:
                if child.type in ('identifier', 'attribute'):
                    base = self._get_text(child, content)
                    bases.append(base)
        
        methods = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'function_definition':
                    method_name_node = child.child_by_field_name('name')
                    if method_name_node:
                        method_name = self._get_text(method_name_node, content)
                        methods.append(method_name)
        
        return {
            "name": name,
            "bases": bases,
            "methods": methods,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_function(self, node, content: str, parent_class: Optional[str]) -> Dict[str, Any]:
        """Extract function information"""
        name_node = node.child_by_field_name('name')
        if not name_node:
            return {"name": "Unknown", "params": [], "line": node.start_point[0] + 1}
        
        name = self._get_text(name_node, content)
        
        params = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type == 'identifier':
                    param = self._get_text(child, content)
                    if param not in ('self', 'cls'):
                        params.append(param)
                elif child.type == 'typed_parameter':
                    param_name = child.child_by_field_name('name')
                    if param_name:
                        param = self._get_text(param_name, content)
                        if param not in ('self', 'cls'):
                            params.append(param)
        
        return_type = None
        return_node = node.child_by_field_name('return_type')
        if return_node:
            return_type = self._get_text(return_node, content)
        
        is_async = self._is_async(node)
        is_method = parent_class is not None
        
        return {
            "name": name,
            "params": params,
            "return_type": return_type,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "is_async": is_async,
            "is_method": is_method,
            "class": parent_class
        }
    
    def _extract_import(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract import information"""
        if node.type == 'import_statement':
            imports = []
            for child in node.children:
                if child.type == 'dotted_name':
                    imports.append(self._get_text(child, content))
                elif child.type == 'aliased_import':
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        imports.append(self._get_text(name_node, content))
            
            if imports:
                return {
                    "type": "import",
                    "modules": imports,
                    "line": node.start_point[0] + 1
                }
        
        elif node.type == 'import_from_statement':
            module_node = node.child_by_field_name('module_name')
            module = self._get_text(module_node, content) if module_node else None
            
            imports = []
            for child in node.children:
                if child.type == 'dotted_name' and child != module_node:
                    imports.append(self._get_text(child, content))
                elif child.type == 'aliased_import':
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        imports.append(self._get_text(name_node, content))
            
            if module or imports:
                return {
                    "type": "from_import",
                    "module": module,
                    "names": imports,
                    "line": node.start_point[0] + 1
                }
        
        return None
    
    def _extract_decorator(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract decorator information"""
        decorators = []
        for child in node.children:
            if child.type == 'decorator':
                decorator_text = self._get_text(child, content)
                decorators.append(decorator_text.lstrip('@'))
        
        if decorators:
            return {
                "decorators": decorators,
                "line": node.start_point[0] + 1
            }
        
        return None
    
    def _is_async(self, node) -> bool:
        """Check if function is async"""
        for child in node.children:
            if child.type == 'async':
                return True
        return False
    
    def _get_text(self, node, content: str) -> str:
        """Extract text from node"""
        return content[node.start_byte:node.end_byte]
