"""
Java Symbol Extractor using Tree-sitter
Handles classes, interfaces, methods, annotations
"""

from typing import Dict, List, Any, Optional


class JavaExtractor:
    """Extract symbols from Java code using tree-sitter AST"""
    
    def extract(self, root_node, content: str) -> Dict[str, Any]:
        """Extract all Java symbols"""
        symbols = {
            "classes": [],
            "interfaces": [],
            "enums": [],
            "methods": [],
            "imports": [],
            "annotations": [],
            "packages": []
        }
        
        self._traverse(root_node, symbols, content, package=None, parent_class=None)
        return symbols
    
    def _traverse(self, node, symbols: Dict, content: str, package: Optional[str] = None, parent_class: Optional[str] = None):
        """Recursively traverse AST"""
        
        if node.type == 'package_declaration':
            package_info = self._extract_package(node, content)
            if package_info:
                symbols['packages'].append(package_info)
                package = package_info['name']
        
        elif node.type == 'class_declaration':
            class_info = self._extract_class(node, content, package)
            symbols['classes'].append(class_info)
            for child in node.children:
                self._traverse(child, symbols, content, package, parent_class=class_info['name'])
        
        elif node.type == 'interface_declaration':
            interface_info = self._extract_interface(node, content, package)
            symbols['interfaces'].append(interface_info)
        
        elif node.type == 'enum_declaration':
            enum_info = self._extract_enum(node, content, package)
            symbols['enums'].append(enum_info)
        
        elif node.type == 'method_declaration':
            method_info = self._extract_method(node, content, parent_class)
            symbols['methods'].append(method_info)
        
        elif node.type == 'import_declaration':
            import_info = self._extract_import(node, content)
            if import_info:
                symbols['imports'].append(import_info)
        
        elif node.type == 'annotation':
            annotation_info = self._extract_annotation(node, content)
            if annotation_info:
                symbols['annotations'].append(annotation_info)
        
        else:
            for child in node.children:
                self._traverse(child, symbols, content, package, parent_class)
    
    def _extract_package(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract package declaration"""
        for child in node.children:
            if child.type == 'scoped_identifier' or child.type == 'identifier':
                return {
                    "name": self._get_text(child, content),
                    "line": node.start_point[0] + 1
                }
        return None
    
    def _extract_class(self, node, content: str, package: Optional[str]) -> Dict[str, Any]:
        """Extract class information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        # Extract superclass
        superclass = None
        superclass_node = node.child_by_field_name('superclass')
        if superclass_node:
            for child in superclass_node.children:
                if child.type in ('type_identifier', 'scoped_type_identifier'):
                    superclass = self._get_text(child, content)
        
        # Extract interfaces
        interfaces = []
        interfaces_node = node.child_by_field_name('interfaces')
        if interfaces_node:
            for child in interfaces_node.children:
                if child.type in ('type_identifier', 'scoped_type_identifier'):
                    interfaces.append(self._get_text(child, content))
        
        # Extract methods
        methods = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'method_declaration':
                    method_name_node = child.child_by_field_name('name')
                    if method_name_node:
                        methods.append(self._get_text(method_name_node, content))
        
        # Extract modifiers
        modifiers = self._extract_modifiers(node, content)
        
        return {
            "name": name,
            "package": package,
            "superclass": superclass,
            "interfaces": interfaces,
            "methods": methods,
            "modifiers": modifiers,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_interface(self, node, content: str, package: Optional[str]) -> Dict[str, Any]:
        """Extract interface information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        # Extract extends
        extends = []
        extends_node = node.child_by_field_name('extends')
        if extends_node:
            for child in extends_node.children:
                if child.type in ('type_identifier', 'scoped_type_identifier'):
                    extends.append(self._get_text(child, content))
        
        # Extract methods
        methods = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'method_declaration':
                    method_name_node = child.child_by_field_name('name')
                    if method_name_node:
                        methods.append(self._get_text(method_name_node, content))
        
        modifiers = self._extract_modifiers(node, content)
        
        return {
            "name": name,
            "package": package,
            "extends": extends,
            "methods": methods,
            "modifiers": modifiers,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_enum(self, node, content: str, package: Optional[str]) -> Dict[str, Any]:
        """Extract enum information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "Anonymous"
        
        # Extract enum constants
        constants = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'enum_constant':
                    const_name_node = child.child_by_field_name('name')
                    if const_name_node:
                        constants.append(self._get_text(const_name_node, content))
        
        return {
            "name": name,
            "package": package,
            "constants": constants,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_method(self, node, content: str, parent_class: Optional[str]) -> Dict[str, Any]:
        """Extract method information"""
        name_node = node.child_by_field_name('name')
        name = self._get_text(name_node, content) if name_node else "anonymous"
        
        # Extract parameters
        params = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type == 'formal_parameter':
                    param_name_node = child.child_by_field_name('name')
                    if param_name_node:
                        params.append(self._get_text(param_name_node, content))
        
        # Extract return type
        return_type = None
        type_node = node.child_by_field_name('type')
        if type_node:
            return_type = self._get_text(type_node, content)
        
        # Extract modifiers
        modifiers = self._extract_modifiers(node, content)
        
        return {
            "name": name,
            "params": params,
            "return_type": return_type,
            "modifiers": modifiers,
            "class": parent_class,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1
        }
    
    def _extract_import(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract import declaration"""
        for child in node.children:
            if child.type in ('scoped_identifier', 'identifier'):
                return {
                    "path": self._get_text(child, content),
                    "line": node.start_point[0] + 1
                }
        return None
    
    def _extract_annotation(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Extract annotation"""
        name_node = node.child_by_field_name('name')
        if name_node:
            return {
                "name": self._get_text(name_node, content),
                "line": node.start_point[0] + 1
            }
        return None
    
    def _extract_modifiers(self, node, content: str) -> List[str]:
        """Extract modifiers (public, private, static, etc.)"""
        modifiers = []
        for child in node.children:
            if child.type == 'modifiers':
                for modifier in child.children:
                    if modifier.type in ('public', 'private', 'protected', 'static', 'final', 'abstract', 'synchronized'):
                        modifiers.append(modifier.type)
        return modifiers
    
    def _get_text(self, node, content: str) -> str:
        """Extract text from node"""
        if node is None:
            return ""
        return content[node.start_byte:node.end_byte]
