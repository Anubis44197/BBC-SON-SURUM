#!/usr/bin/env python3
"""Test tree-sitter installation and FullSymbolExtractor"""

import sys
import traceback

print("=" * 60)
print("TREE-SITTER TEST")
print("=" * 60)

# Test 1: Import tree-sitter
print("\n[1] Testing tree-sitter import...")
try:
    from tree_sitter import Parser
    print("✅ tree_sitter.Parser imported")
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()

# Test 2: Import language modules
print("\n[2] Testing language modules...")
languages = {
    'python': 'tree_sitter_python',
    'javascript': 'tree_sitter_javascript',
    'typescript': 'tree_sitter_typescript',
    'rust': 'tree_sitter_rust',
    'go': 'tree_sitter_go',
    'c': 'tree_sitter_c',
    'cpp': 'tree_sitter_cpp',
    'java': 'tree_sitter_java',
}

for lang, module_name in languages.items():
    try:
        module = __import__(module_name)
        print(f"✅ {lang}: {module_name}")
    except Exception as e:
        print(f"❌ {lang}: {e}")

# Test 3: Create parsers
print("\n[3] Testing parser creation...")
try:
    import tree_sitter_python
    parser = Parser(tree_sitter_python.language())
    print(f"✅ Python parser created")
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()

# Test 4: Test FullSymbolExtractor
print("\n[4] Testing FullSymbolExtractor...")
try:
    from bbc_core.full_symbol_extractor import FullSymbolExtractor
    extractor = FullSymbolExtractor(".")
    stats = extractor.get_stats()
    print(f"✅ FullSymbolExtractor created")
    print(f"   Tree-sitter available: {stats['tree_sitter_available']}")
    print(f"   Supported languages: {stats['supported_languages']}")
    print(f"   Cache files: {stats['cache_files']}")
    print(f"   Indexed symbols: {stats['indexed_symbols']}")
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()

# Test 5: Test actual extraction
print("\n[5] Testing symbol extraction...")
try:
    from bbc_core.full_symbol_extractor import FullSymbolExtractor
    extractor = FullSymbolExtractor(".")
    
    test_code = '''
class TestClass:
    def __init__(self):
        self.value = 42
    
    def method(self, x):
        return x * 2

def standalone_function():
    pass
'''
    
    symbols = extractor.extract_symbols("test.py", test_code, ".py")
    print(f"✅ Extraction successful")
    print(f"   Method: {symbols.get('_meta', {}).get('method', 'unknown')}")
    print(f"   Classes: {[c.get('name') for c in symbols.get('classes', [])]}")
    print(f"   Functions: {[f.get('name') for f in symbols.get('functions', [])]}")
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
