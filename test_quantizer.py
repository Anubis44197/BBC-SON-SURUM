#!/usr/bin/env python3
import sys
sys.path.insert(0, 'C:/Users/90535/Desktop/BBC-SON-SURUM-1')

from bbc_core.hmpu_quantizer import HMPUQuantizer

print("Testing HMPUQuantizer with tree-sitter...")

# Initialize with project root
quantizer = HMPUQuantizer(project_root='C:/Users/90535/Desktop/AutoResearchClaw', use_enhanced=True)

print(f"Enhanced extractor: {quantizer.enhanced_extractor is not None}")

if quantizer.enhanced_extractor:
    stats = quantizer.enhanced_extractor.get_stats()
    print(f"Tree-sitter available: {stats['tree_sitter_available']}")
    print(f"Supported languages: {stats['supported_languages']}")

# Test extraction
test_code = '''
class TestClass:
    def __init__(self):
        self.value = 42
    
    def method(self, x):
        return x * 2

def standalone_function():
    pass
'''

result = quantizer.process_content(test_code, file_ext='.py', file_path='test.py')
print(f"\nExtraction method: {result['stats'].get('method', 'unknown')}")
print(f"Classes: {result['structure']['classes']}")
print(f"Functions: {result['structure']['functions']}")

# Check cache
if quantizer.enhanced_extractor:
    stats = quantizer.enhanced_extractor.get_stats()
    print(f"\nCache files: {stats['cache_files']}")
    print(f"Indexed symbols: {stats['indexed_symbols']}")
