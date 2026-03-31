"""
C/C++ Symbol Extractor using Tree-sitter
Handles structs, classes, functions, templates
"""

from typing import Dict, List, Any, Optional


class CCppExtractor:
    """Extract symbols from C/C++ code using tree-sitter AST"""
    
    def extract(self, root_node, content: str) -> Dict[str, Any]:
        """Extract all C/C++ symbols"""
        symbols = {
            "classes": [],
            "structs": [],
            "functions": [],
            "enums": [],
            "typedefs": [],
            "namespaces": [],
            "includes": []
        }
        
        self._traverse(root_node, symbols, content, namespace=None)
        return symbols
    
    def _traverse(self, node, symbols: Dict, content: str, namespace: Optional[str] = None):
        """Recursively traverse AST"""
        
        if node.type == 'class_specifier':
            class_info = self._extract_class(node, content, namespace)
            symbols['classes'].append(class_info)
        
        elif node.type == 'struct_specifier':
            struct_info = self._extract_struct(node, content, namespace)
            symbols['structs'].append(struct_info)
        
        elif node.type == 'function_definition':
            func_info = self._extract_function(node, content, namespace)
            symbols['functions'].append(func_info)
        
        elif node.type == 'enum_specifier':
            enum_info = self._extract_enum(node, content, namespace)
            symbols['enums'].append(enum_info)
        
        elif node.type == 'type_definition':
            typedef_info = self._extract_typedef(node, content)
            if typedef_info:
                symbols['typedefs'].append(typedef_info)
        
        elif node.type == 'namespace_definition':
            ns_info = self._extract_namespace(node, symbols, content)
            symbols['namespaces'].append(ns_info)
        
        elif node.type == 'preproc_include':
            include_info = self._extract_include(node, content)
            if include_info:
                symbols['includes'].append(include_info)
        
        else:
            for child in node.children:
                self._traverse(child, symbols, content, namespace)
    
    def _extract_class(self, node, content: str, namespace: Optional[str]) -> Dict[str, Any]:
        """Extract class information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        # Extract base classes
        bases = []
        for child in node.children:
            if child.type == 'base_class_clause':
                for subchild in child.children:
                    if subchild.type in ('type_identifier', 'qualified_identifier'):
                        bases.append(self._get_text(subchild, content))
        
        # Extract methods
        methods = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'function_definition':
                    declarator = child.child_by_field_name('declarator')
                    if declarator:
                        method_name = self._extract_function_name(declarator, content)
                        if method_name:
                            methods.append(method_name)
        
        return {
            "name": name,
            "bases": bases,
            "methods": methods,
            "namespace": namespace,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_struct(self, node, content: str, namespace: Optional[str]) -> Dict[str, Any]:
        """Extract struct information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        # Extract fields
        fields = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'field_declaration':
                    declarator = child.child_by_field_name('declarator')
                    if declarator:
                        field_name = self._extract_declarator_name(declarator, content)
                        if field_name:
                            fields.append(field_name)
        
        return {
            "name": name,
            "fields": fields,
            "namespace": namespace,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_function(self, node, content: str, namespace: Optional[str]) -> Dict[str, Any]:
        """Extract function information"""
        declarator = node.child_by_field_name('declarator')
        name = self._extract_function_name(declarator, content) if declarator else "anonymous"
        
        # Extract parameters
        params = []
        if declarator:
            params = self._extract_parameters(declarator, content)
        
        # Extract return type
        return_type = None
        type_node = node.child_by_field_name('type')
        if type_node:
            return_type = self._get_text(type_node, content)
        
        return {
            "name": name,
            "params": params,
            "return_type": return_type,
            "namespace": namespace,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_enum(self, node, content: str, namespace: Optional[str]) -> Dict[str, Any]:
        """Extract enum information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        # Extract enumerators
        enumerators = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'enumerator':
                    enum_name_node = child.child_by_field_name('name')
                    if enum_name_node:
                        enumerators.append(self._get_text(enum_name_node, content))
        
        return {
            "name": name,
            "enumerators": enumerators,
            "namespace": namespace,
            "line": node.start_point[0] + 1
        }
    
    def _extract_typedef(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract typedef information"""
        declarator = node.child_by_field_name('declarator')
        if declarator:
            name = self._extract_declarator_name(declarator, content)
            if name:
                return {
                    "name": name,
                    "line": node.start_point[0] + 1
                }
        return None
    
    def _extract_namespace(self, node, symbols: Dict, content: str) -> Dict[str, Any]:
        """Extract namespace information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        # Traverse namespace body
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                self._traverse(child, symbols, content, namespace=name)
        
        return {
            "name": name,
            "line": node.start_point[0] + 1
        }
    
    def _extract_include(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract include directive"""
        path_node = node.child_by_field_name('path')
        if path_node:
            path = self._get_text(path_node, content)
            return {
                "path": path.strip('<>"'),
                "line": node.start_point[0] + 1
            }
        return None
    
    def _extract_function_name(self, declarator, content: str) -> Optional[str]:
        """Extract function name from declarator"""
        if declarator.type == 'function_declarator':
            inner_declarator = declarator.child_by_field_name('declarator')
            if inner_declarator:
                return self._extract_declarator_name(inner_declarator, content)
        elif declarator.type == 'identifier':
            return self._get_text(declarator, content)
        return None
    
    def _extract_declarator_name(self, declarator, content: str) -> Optional[str]:
        """Extract name from declarator"""
        if declarator.type == 'identifier':
            return self._get_text(declarator, content)
        elif declarator.type == 'pointer_declarator':
            inner = declarator.child_by_field_name('declarator')
            if inner:
                return self._extract_declarator_name(inner, content)
        elif declarator.type == 'array_declarator':
            inner = declarator.child_by_field_name('declarator')
            if inner:
                return self._extract_declarator_name(inner, content)
        return None
    
    def _extract_parameters(self, declarator, content: str) -> List[str]:
        """Extract function parameters"""
        params = []
        
        if declarator.type == 'function_declarator':
            params_node = declarator.child_by_field_name('parameters')
            if params_node:
                for child in params_node.children:
                    if child.type == 'parameter_declaration':
                        param_declarator = child.child_by_field_name('declarator')
                        if param_declarator:
                            param_name = self._extract_declarator_name(param_declarator, content)
                            if param_name:
                                params.append(param_name)
        
        return params
    
    def _get_text(self, node, content: str) -> str:
        """Extract text from node"""
        if node is None:
            return ""
        return content[node.start_byte:node.end_byte]
