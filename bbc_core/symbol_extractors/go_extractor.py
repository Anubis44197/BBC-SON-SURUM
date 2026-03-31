"""
Go Symbol Extractor using Tree-sitter
Handles structs, interfaces, functions, methods
"""

from typing import Dict, List, Any, Optional


class GoExtractor:
    """Extract symbols from Go code using tree-sitter AST"""
    
    def extract(self, root_node, content: str) -> Dict[str, Any]:
        """Extract all Go symbols"""
        symbols = {
            "structs": [],
            "interfaces": [],
            "functions": [],
            "methods": [],
            "imports": [],
            "constants": [],
            "variables": []
        }
        
        self._traverse(root_node, symbols, content)
        return symbols
    
    def _traverse(self, node, symbols: Dict, content: str):
        """Recursively traverse AST"""
        
        if node.type == 'type_declaration':
            self._extract_type_declaration(node, symbols, content)
        
        elif node.type == 'function_declaration':
            func_info = self._extract_function(node, content)
            symbols['functions'].append(func_info)
        
        elif node.type == 'method_declaration':
            method_info = self._extract_method(node, content)
            symbols['methods'].append(method_info)
        
        elif node.type == 'import_declaration':
            import_info = self._extract_import(node, content)
            if import_info:
                symbols['imports'].extend(import_info)
        
        elif node.type == 'const_declaration':
            const_info = self._extract_const(node, content)
            if const_info:
                symbols['constants'].extend(const_info)
        
        elif node.type == 'var_declaration':
            var_info = self._extract_var(node, content)
            if var_info:
                symbols['variables'].extend(var_info)
        
        for child in node.children:
            self._traverse(child, symbols, content)
    
    def _extract_type_declaration(self, node, symbols: Dict, content: str):
        """Extract type declaration (struct or interface)"""
        for child in node.children:
            if child.type == 'type_spec':
                name_node = child.child_by_field_name('name')
                type_node = child.child_by_field_name('type')
                
                if name_node and type_node:
                    name = self._get_text(name_node, content)
                    
                    if type_node.type == 'struct_type':
                        struct_info = self._extract_struct(name, type_node, content, node.start_point[0] + 1)
                        symbols['structs'].append(struct_info)
                    
                    elif type_node.type == 'interface_type':
                        interface_info = self._extract_interface(name, type_node, content, node.start_point[0] + 1)
                        symbols['interfaces'].append(interface_info)
    
    def _extract_struct(self, name: str, node, content: str, line: int) -> Dict[str, Any]:
        """Extract struct information"""
        fields = []
        
        field_list_node = node.child_by_field_name('field_declaration_list')
        if field_list_node:
            for child in field_list_node.children:
                if child.type == 'field_declaration':
                    for subchild in child.children:
                        if subchild.type == 'field_identifier':
                            fields.append(self._get_text(subchild, content))
        
        return {
            "name": name,
            "fields": fields,
            "line": line,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_interface(self, name: str, node, content: str, line: int) -> Dict[str, Any]:
        """Extract interface information"""
        methods = []
        
        method_list_node = node.child_by_field_name('method_spec_list')
        if method_list_node:
            for child in method_list_node.children:
                if child.type == 'method_spec':
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        methods.append(self._get_text(name_node, content))
        
        return {
            "name": name,
            "methods": methods,
            "line": line,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_function(self, node, content: str) -> Dict[str, Any]:
        """Extract function information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "anonymous"
        
        params = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type == 'parameter_declaration':
                    for subchild in child.children:
                        if subchild.type == 'identifier':
                            params.append(self._get_text(subchild, content))
        
        return {
            "name": name,
            "params": params,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_method(self, node, content: str) -> Dict[str, Any]:
        """Extract method information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "anonymous"
        
        receiver_node = node.child_by_field_name('receiver')
        receiver_type = None
        if receiver_node:
            for child in receiver_node.children:
                if child.type in ('type_identifier', 'pointer_type'):
                    receiver_type = self._get_text(child, content)
        
        params = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type == 'parameter_declaration':
                    for subchild in child.children:
                        if subchild.type == 'identifier':
                            params.append(self._get_text(subchild, content))
        
        return {
            "name": name,
            "receiver": receiver_type,
            "params": params,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_import(self, node, content: str) -> List[Dict[str, Any]]:
        """Extract import declarations"""
        imports = []
        
        for child in node.children:
            if child.type == 'import_spec':
                path_node = child.child_by_field_name('path')
                if path_node:
                    path = self._get_text(path_node, content).strip('"')
                    imports.append({
                        "path": path,
                        "line": child.start_point[0] + 1
                    })
        
        return imports
    
    def _extract_const(self, node, content: str) -> List[Dict[str, Any]]:
        """Extract constant declarations"""
        constants = []
        
        for child in node.children:
            if child.type == 'const_spec':
                name_node = child.child_by_field_name('name')
                if name_node:
                    constants.append({
                        "name": self._get_text(name_node, content),
                        "line": child.start_point[0] + 1
                    })
        
        return constants
    
    def _extract_var(self, node, content: str) -> List[Dict[str, Any]]:
        """Extract variable declarations"""
        variables = []
        
        for child in node.children:
            if child.type == 'var_spec':
                name_node = child.child_by_field_name('name')
                if name_node:
                    variables.append({
                        "name": self._get_text(name_node, content),
                        "line": child.start_point[0] + 1
                    })
        
        return variables
    
    def _get_text(self, node, content: str) -> str:
        """Extract text from node"""
        if node is None:
            return ""
        return content[node.start_byte:node.end_byte]
