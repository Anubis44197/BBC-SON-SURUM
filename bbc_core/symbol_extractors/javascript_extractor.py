"""
JavaScript/TypeScript Symbol Extractor using Tree-sitter
Handles ES6+, JSX, TSX, classes, arrow functions, exports
"""

from typing import Dict, List, Any, Optional


class JavaScriptExtractor:
    """Extract symbols from JavaScript/TypeScript using tree-sitter AST"""
    
    def extract(self, root_node, content: str) -> Dict[str, Any]:
        """Extract all JS/TS symbols"""
        symbols = {
            "classes": [],
            "functions": [],
            "imports": [],
            "exports": [],
            "variables": [],
            "interfaces": [],  # TypeScript
            "types": []  # TypeScript
        }
        
        self._traverse(root_node, symbols, content, parent_class=None)
        return symbols
    
    def _traverse(self, node, symbols: Dict, content: str, parent_class: Optional[str] = None):
        """Recursively traverse AST"""
        
        if node.type == 'class_declaration':
            class_info = self._extract_class(node, content)
            symbols['classes'].append(class_info)
            for child in node.children:
                self._traverse(child, symbols, content, parent_class=class_info['name'])
        
        elif node.type == 'function_declaration':
            func_info = self._extract_function(node, content, parent_class)
            symbols['functions'].append(func_info)
        
        elif node.type == 'arrow_function':
            func_info = self._extract_arrow_function(node, content)
            if func_info:
                symbols['functions'].append(func_info)
        
        elif node.type == 'method_definition':
            method_info = self._extract_method(node, content, parent_class)
            symbols['functions'].append(method_info)
        
        elif node.type == 'import_statement':
            import_info = self._extract_import(node, content)
            if import_info:
                symbols['imports'].append(import_info)
        
        elif node.type == 'export_statement':
            export_info = self._extract_export(node, content)
            if export_info:
                symbols['exports'].append(export_info)
        
        elif node.type == 'interface_declaration':
            interface_info = self._extract_interface(node, content)
            symbols['interfaces'].append(interface_info)
        
        elif node.type == 'type_alias_declaration':
            type_info = self._extract_type_alias(node, content)
            symbols['types'].append(type_info)
        
        else:
            for child in node.children:
                self._traverse(child, symbols, content, parent_class)
    
    def _extract_class(self, node, content: str) -> Dict[str, Any]:
        """Extract class information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        # Extract heritage (extends)
        heritage = []
        heritage_node = node.child_by_field_name('heritage')
        if heritage_node:
            for child in heritage_node.children:
                if child.type == 'identifier':
                    heritage.append(self._get_text(child, content))
        
        # Extract methods
        methods = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'method_definition':
                    method_name_node = child.child_by_field_name('name')
                    if method_name_node:
                        methods.append(self._get_text(method_name_node, content))
        
        return {
            "name": name,
            "extends": heritage,
            "methods": methods,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_function(self, node, content: str, parent_class: Optional[str]) -> Dict[str, Any]:
        """Extract function declaration"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "anonymous"
        
        params = self._extract_parameters(node, content)
        is_async = self._is_async(node)
        
        return {
            "name": name,
            "params": params,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "is_async": is_async,
            "is_method": parent_class is not None,
            "class": parent_class,
            "type": "function"
        }
    
    def _extract_arrow_function(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract arrow function (if assigned to variable)"""
        parent = node.parent
        if parent and parent.type == 'variable_declarator':
            name_node = parent.child_by_field_name('name')
            if name_node:
                name = self._get_text(name_node, content)
                params = self._extract_parameters(node, content)
                is_async = self._is_async(node)
                
                return {
                    "name": name,
                    "params": params,
                    "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "is_async": is_async,
                    "is_method": False,
                    "type": "arrow_function"
                }
        return None
    
    def _extract_method(self, node, content: str, parent_class: Optional[str]) -> Dict[str, Any]:
        """Extract class method"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "anonymous"
        
        params = self._extract_parameters(node, content)
        is_async = self._is_async(node)
        is_static = self._is_static(node)
        
        return {
            "name": name,
            "params": params,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "is_async": is_async,
            "is_method": True,
            "is_static": is_static,
            "class": parent_class,
            "type": "method"
        }
    
    def _extract_parameters(self, node, content: str) -> List[str]:
        """Extract function parameters"""
        params = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type in ('identifier', 'required_parameter', 'optional_parameter'):
                    param_name = self._get_text(child, content)
                    params.append(param_name)
        return params
    
    def _extract_import(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract import statement"""
        source_node = node.child_by_field_name('source')
        source = self._get_text(source_node, content).strip('"\'') if source_node else None
        
        imports = []
        for child in node.children:
            if child.type == 'import_clause':
                for subchild in child.children:
                    if subchild.type in ('identifier', 'named_imports'):
                        imports.append(self._get_text(subchild, content))
        
        if source:
            return {
                "source": source,
                "imports": imports,
                "line": node.start_point[0] + 1
            }
        return None
    
    def _extract_export(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract export statement"""
        declaration = node.child_by_field_name('declaration')
        if declaration:
            if declaration.type == 'class_declaration':
                name_node = declaration.child_by_field_name('name')
                name = self._get_text(name_node, content) if name_node else None
                return {"type": "class", "name": name, "line": node.start_point[0] + 1}
            elif declaration.type == 'function_declaration':
                name_node = declaration.child_by_field_name('name')
                name = self._get_text(name_node, content) if name_node else None
                return {"type": "function", "name": name, "line": node.start_point[0] + 1}
        return None
    
    def _extract_interface(self, node, content: str) -> Dict[str, Any]:
        """Extract TypeScript interface"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        return {
            "name": name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_type_alias(self, node, content: str) -> Dict[str, Any]:
        """Extract TypeScript type alias"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        return {
            "name": name,
            "line": node.start_point[0] + 1
        }
    
    def _is_async(self, node) -> bool:
        """Check if function is async"""
        for child in node.children:
            if child.type == 'async':
                return True
        return False
    
    def _is_static(self, node) -> bool:
        """Check if method is static"""
        for child in node.children:
            if child.type == 'static':
                return True
        return False
    
    def _get_text(self, node, content: str) -> str:
        """Extract text from node"""
        if node is None:
            return ""
        return content[node.start_byte:node.end_byte]


class TypeScriptExtractor(JavaScriptExtractor):
    """TypeScript extractor (inherits from JavaScript)"""
    pass
