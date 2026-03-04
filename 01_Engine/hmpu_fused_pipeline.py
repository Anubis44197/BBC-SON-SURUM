"""DEPRECATED: Stub module - search functionality not yet implemented.
Use bbc_core.hmpu_engine.HMPUEngine for recipe-based processing instead.
"""
import os
import sys
from hmpu_quantizer import HMPUQuantizer
from hmpu_indexer import HMPUIndexer

class HMPUFusedPipeline:
    def __init__(self):
        self.quantizer = HMPUQuantizer()
        self.indexer = HMPUIndexer(index_dir="hmpu_indices_v55")

    def run_search(self, query, top_k=5):
        # Not implemented - placeholder for future search functionality
        return []
