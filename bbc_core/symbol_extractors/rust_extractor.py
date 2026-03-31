"""
Rust Symbol Extractor using Tree-sitter
Handles structs, enums, traits, impl blocks, functions
"""

from typing import Dict, List, Any, Optional


class RustExtractor:
    """Extract symbols from Rust code using tree-sitter AST"""
    
    def extract(self, root_node, content: str) -> Dict[str, Any]:
        """Extract all Rust symbols"""
        symbols = {
            "structs": [],
            "enums": [],
            "traits": [],
            "impls": [],
            "functions": [],
            "mods": [],
            "uses": []
        }
        
        self._traverse(root_node, symbols, content)
        return symbols
    
    def _traverse(self, node, symbols: Dict, content: str):
        """Recursively traverse AST"""
        
        if node.type == 'struct_item':
            struct_info = self._extract_struct(node, content)
            symbols['structs'].append(struct_info)
        
        elif node.type == 'enum_item':
            enum_info = self._extract_enum(node, content)
            symbols['enums'].append(enum_info)
        
        elif node.type == 'trait_item':
            trait_info = self._extract_trait(node, content)
            symbols['traits'].append(trait_info)
        
        elif node.type == 'impl_item':
            impl_info = self._extract_impl(node, content)
            symbols['impls'].append(impl_info)
        
        elif node.type == 'function_item':
            func_info = self._extract_function(node, content)
            symbols['functions'].append(func_info)
        
        elif node.type == 'mod_item':
            mod_info = self._extract_mod(node, content)
            symbols['mods'].append(mod_info)
        
        elif node.type == 'use_declaration':
            use_info = self._extract_use(node, content)
            if use_info:
                symbols['uses'].append(use_info)
        
        for child in node.children:
            self._traverse(child, symbols, content)
    
    def _extract_struct(self, node, content: str) -> Dict[str, Any]:
        """Extract struct information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        fields = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'field_declaration':
                    field_name_node = child.child_by_field_name('name')
                    if field_name_node:
                        fields.append(self._get_text(field_name_node, content))
        
        is_pub = self._is_public(node)
        
        return {
            "name": name,
            "fields": fields,
            "is_pub": is_pub,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_enum(self, node, content: str) -> Dict[str, Any]:
        """Extract enum information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        variants = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'enum_variant':
                    variant_name_node = child.child_by_field_name('name')
                    if variant_name_node:
                        variants.append(self._get_text(variant_name_node, content))
        
        is_pub = self._is_public(node)
        
        return {
            "name": name,
            "variants": variants,
            "is_pub": is_pub,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_trait(self, node, content: str) -> Dict[str, Any]:
        """Extract trait information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        methods = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type in ('function_item', 'function_signature_item'):
                    method_name_node = child.child_by_field_name('name')
                    if method_name_node:
                        methods.append(self._get_text(method_name_node, content))
        
        is_pub = self._is_public(node)
        
        return {
            "name": name,
            "methods": methods,
            "is_pub": is_pub,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_impl(self, node, content: str) -> Dict[str, Any]:
        """Extract impl block information"""
        type_node = node.child_by_field_name('type')
        type_name = self._get_text(type_node, content) if type_node else "Unknown"
        
        trait_node = node.child_by_field_name('trait')
        trait_name = self._get_text(trait_node, content) if trait_node else None
        
        methods = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'function_item':
                    method_name_node = child.child_by_field_name('name')
                    if method_name_node:
                        methods.append(self._get_text(method_name_node, content))
        
        return {
            "type": type_name,
            "trait": trait_name,
            "methods": methods,
            "line": node.start_point[0] + 1,
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
                if child.type in ('parameter', 'self_parameter'):
                    pattern_node = child.child_by_field_name('pattern')
                    if pattern_node:
                        params.append(self._get_text(pattern_node, content))
        
        return_type = None
        return_node = node.child_by_field_name('return_type')
        if return_node:
            return_type = self._get_text(return_node, content)
        
        is_pub = self._is_public(node)
        is_async = self._is_async(node)
        
        return {
            "name": name,
            "params": params,
            "return_type": return_type,
            "is_pub": is_pub,
            "is_async": is_async,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_mod(self, node, content: str) -> Dict[str, Any]:
        """Extract module information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        is_pub = self._is_public(node)
        
        return {
            "name": name,
            "is_pub": is_pub,
            "line": node.start_point[0] + 1
        }
    
    def _extract_use(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract use declaration"""
        argument_node = node.child_by_field_name('argument')
        if argument_node:
            use_path = self._get_text(argument_node, content)
            return {
                "path": use_path,
                "line": node.start_point[0] + 1
            }
        return None
    
    def _is_public(self, node) -> bool:
        """Check if item is public"""
        for child in node.children:
            if child.type == 'visibility_modifier':
                return 'pub' in self._get_text(child, node)
        return False
    
    def _is_async(self, node) -> bool:
        """Check if function is async"""
        for child in node.children:
            if child.type == 'async':
                return True
        return False
    
    def _get_text(self, node, content: str) -> str:
        """Extract text from node"""
        if node is None:
            return ""
        return content[node.start_byte:node.end_byte]
