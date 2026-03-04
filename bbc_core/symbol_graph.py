"""
BBC Symbol Graph - Aşama 3.6.1: AST Tabanlı, Import-Aware, Deterministik Call Graph

Bu modül semboller arası çağrı ilişkilerini analiz eder ve call graph oluşturur.
- Python AST modülü kullanır (deterministik)
- Import ve alias resolution yapar
- Symbol stack tabanlı caller tespiti
- UNKNOWN çağrıları raporlar
- LLM/AI kullanmaz - tamamen deterministiktir

Çıktı Formatı:
{
  "symbols": [
    {
      "symbol": "BBCNativeAdapter.compute_hash",
      "type": "method",
      "file": "path/to/file.py",
      "line": 22,
      "calls": [
        {"symbol": "hashlib.sha256", "type": "external", "line": 25, "raw_call": "hashlib.sha256(data)"},
        {"symbol": "BBCNativeAdapter._get_config", "type": "internal", "line": 26, "raw_call": "self._get_config()"}
      ],
      "called_by": [...]
    }
  ],
  "graph_stats": {
    "total_symbols": 10,
    "total_calls": 25,
    "internal_calls": 15,
    "external_calls": 10,
    "unknown_calls": 2,
    "unresolved_calls": [
      {"caller": "A.foo", "line": 10, "raw_call": "some_undefined_func()"}
    ]
  }
}
"""

import ast
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from enum import Enum


class CallType(Enum):
    """Çağrı tipleri."""
    INTERNAL = "internal"      # Aynı projedeki sembol
    EXTERNAL = "external"      # Harici kütüphane/standart kütüphane
    RECURSIVE = "recursive"    # Kendi kendini çağırma
    UNKNOWN = "unknown"        # Belirsiz/çözümlenemeyen


class SymbolType(Enum):
    """Sembol tipleri (symbol_extractor ile uyumlu)."""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    ENUM = "enum"
    PROPERTY = "property"


@dataclass
class Call:
    """Bir çağrıyı temsil eden veri sınıfı."""
    symbol: str           # Çağrılan sembolün tam adı
    call_type: str        # internal, external, recursive, unknown
    line: int             # Çağrının bulunduğu satır
    column: int = 0       # Sütun
    raw_call: str = ""    # Çağrı kaynak kodu (örn: "self.compute_hash()")
    
    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştür."""
        result = {
            "symbol": self.symbol,
            "type": self.call_type,
            "line": self.line,
        }
        if self.column:
            result["column"] = self.column
        if self.raw_call:
            result["raw_call"] = self.raw_call
        return result


@dataclass
class SymbolNode:
    """Graph'taki bir sembol düğümünü temsil eder."""
    name: str                    # Sembol adı
    full_name: str              # Tam nitelikli ad (ClassName.method_name)
    symbol_type: str            # class, function, method, vb.
    file: str                   # Bulunduğu dosya
    line: int                   # Tanım satırı
    column: int = 0
    class_name: Optional[str] = None
    module: Optional[str] = None  # Modül adı
    
    # Çağrı ilişkileri
    calls: List[Call] = field(default_factory=list)        # Bu sembolün çağırdıkları
    called_by: List[Call] = field(default_factory=list)    # Bu sembolü çağıranlar
    
    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştür."""
        result = {
            "symbol": self.full_name,
            "type": self.symbol_type,
            "file": self.file,
            "line": self.line,
        }
        if self.class_name:
            result["class"] = self.class_name
        if self.module:
            result["module"] = self.module
        if self.calls:
            result["calls"] = [c.to_dict() for c in self.calls]
        if self.called_by:
            result["called_by"] = [c.to_dict() for c in self.called_by]
        return result


class ImportResolver:
    """
    Import ifadelerini çözümleyen ve alias map oluşturan sınıf.
    
    Desteklenen import tipleri:
    - import x → {"x": "x"}
    - import x as y → {"y": "x"}
    - from x import a → {"a": "x.a"}
    - from x import a as b → {"b": "x.a"}
    - from x import * → module_exports ile çözümlenir
    """
    
    def __init__(self):
        self.import_map: Dict[str, str] = {}  # alias -> fully_qualified_name
        self.module_imports: Set[str] = set()  # Tam modül importları
        self.from_imports: Dict[str, str] = {}  # name -> module
        
    def resolve_imports(self, tree: ast.AST) -> Dict[str, str]:
        """
        AST'den import ifadelerini çözümle ve alias map döndür.
        
        Returns:
            Dict mapping alias/name to fully qualified name
        """
        self.import_map = {}
        self.module_imports = set()
        self.from_imports = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self._handle_import(node)
            elif isinstance(node, ast.ImportFrom):
                self._handle_import_from(node)
        
        return self.import_map
    
    def _handle_import(self, node: ast.Import):
        """import x veya import x as y işle."""
        for alias in node.names:
            if alias.asname:
                # import x as y
                self.import_map[alias.asname] = alias.name
            else:
                # import x
                self.import_map[alias.name] = alias.name
            self.module_imports.add(alias.name)
    
    def _handle_import_from(self, node: ast.ImportFrom):
        """from x import a veya from x import a as b işle."""
        module = node.module or ""
        level = node.level  # Relative import seviyesi (., .., vs)
        
        # Relative import handling
        prefix = ""
        if level > 0:
            prefix = "." * level
            if module:
                module = prefix + module
            else:
                module = prefix
        
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if alias.name == "*":
                # from x import * - special case
                self.from_imports["*"] = module
            else:
                fully_qualified = f"{module}.{alias.name}" if module else alias.name
                self.import_map[name] = fully_qualified
                self.from_imports[name] = module
    
    def resolve_symbol(self, name: str) -> Optional[str]:
        """Bir ismi çözümle ve tam adı döndür."""
        return self.import_map.get(name)
    
    def is_module_imported(self, module: str) -> bool:
        """Bir modülün import edilip edilmediğini kontrol et."""
        return module in self.module_imports or module in self.import_map


class ASTCallExtractor(ast.NodeVisitor):
    """
    Python AST kullanarak dosya düzeyinde çağrıları bulan extractor.
    
    Özellikler:
    - Tüm fonksiyon/metod çağrılarını (ast.Call) tespit eder
    - Symbol stack ile caller tespiti
    - Import resolution ile nitelikli ad çözümleme
    - func() → ast.Name
    - obj.method() → ast.Attribute
    - Class.method(obj) → ast.Attribute
    - module.func() → ast.Attribute
    """
    
    def __init__(self, source_code: str, filename: str = "<unknown>"):
        self.source_code = source_code
        self.filename = filename
        self.lines = source_code.split('\n')
        
        # Import resolution
        self.import_resolver = ImportResolver()
        
        # Symbol stack - şu anki context'i takip et
        self.symbol_stack: List[str] = []  # ["ClassName", "method_name"]
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        
        # Sonuçlar
        self.calls: List[Dict[str, Any]] = []  # Tespit edilen çağrılar
        
    def extract(self) -> List[Dict[str, Any]]:
        """Kaynak koddan tüm çağrıları çıkar."""
        try:
            tree = ast.parse(self.source_code)
            # Önce import'ları çözümle
            self.import_resolver.resolve_imports(tree)
            # Sonra çağrıları bul (symbol stack ile)
            self.visit(tree)
        except SyntaxError as e:
            pass
        return self.calls
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Sınıf tanımına gir."""
        old_class = self.current_class
        self.current_class = node.name
        self.symbol_stack.append(node.name)
        
        self.generic_visit(node)
        
        self.symbol_stack.pop()
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Fonksiyon tanımına gir."""
        self._enter_function(node.name, node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Async fonksiyon tanımına gir."""
        self._enter_function(node.name, node)
    
    def _enter_function(self, name: str, node: ast.AST):
        """Fonksiyon/metod context'ine gir."""
        old_function = self.current_function
        self.current_function = name
        self.symbol_stack.append(name)
        
        # Çağrıları topla
        self.generic_visit(node)
        
        self.symbol_stack.pop()
        self.current_function = old_function
    
    def visit_Call(self, node: ast.Call):
        """Fonksiyon çağrısını tespit et."""
        call_info = self._analyze_call(node)
        if call_info:
            self.calls.append(call_info)
        self.generic_visit(node)
    
    def _get_current_caller(self) -> Optional[str]:
        """Şu anki caller'ın tam adını döndür."""
        if not self.symbol_stack:
            return None
        return ".".join(self.symbol_stack)
    
    def _get_raw_call(self, node: ast.Call) -> str:
        """Çağrının ham kaynak kodunu al."""
        try:
            return ast.unparse(node)
        except Exception:
            # Fallback: sadece fonksiyon kısmını al
            try:
                return ast.unparse(node.func)
            except Exception:
                return "<unparseable>"
    
    def _analyze_call(self, node: ast.Call) -> Optional[Dict[str, Any]]:
        """
        Bir ast.Call node'unu analiz et ve çağrı bilgisi döndür.
        
        Returns:
            Dict with caller, callee, line, raw_call, etc.
        """
        caller = self._get_current_caller()
        if not caller:
            # Global seviyede çağrı - atla veya işaretle
            return None
        
        line = node.lineno
        column = node.col_offset
        raw_call = self._get_raw_call(node)
        
        # Çağrılan fonksiyonu analiz et
        func = node.func
        callee, call_type = self._resolve_callee(func)
        
        return {
            "caller": caller,
            "callee": callee,
            "call_type": call_type,
            "line": line,
            "column": column,
            "raw_call": raw_call,
            "file": self.filename
        }
    
    def _resolve_callee(self, func: ast.expr) -> Tuple[str, str]:
        """
        Çağrılan fonksiyonun adını ve tipini çözümle.
        
        Returns:
            (callee_name, call_type)
        """
        if isinstance(func, ast.Name):
            # Basit fonksiyon çağrısı: func()
            return self._resolve_simple_call(func.id)
            
        elif isinstance(func, ast.Attribute):
            # Nitelikli çağrı: obj.method()
            return self._resolve_attribute_call(func)
        
        elif isinstance(func, ast.Subscript):
            # obj[method]() gibi karmaşık çağrılar
            return ("UNKNOWN", CallType.UNKNOWN.value)
        
        elif isinstance(func, ast.Lambda):
            # Lambda çağrısı
            return ("<lambda>", CallType.EXTERNAL.value)
        
        return ("UNKNOWN", CallType.UNKNOWN.value)
    
    def _resolve_simple_call(self, name: str) -> Tuple[str, str]:
        """Basit fonksiyon çağrısını çözümle: func()"""
        # Recursive check
        current_caller = self._get_current_caller()
        if current_caller:
            caller_parts = current_caller.split('.')
            if name == caller_parts[-1]:
                return (current_caller, CallType.RECURSIVE.value)
        
        # Import edilmiş mi?
        resolved = self.import_resolver.resolve_symbol(name)
        if resolved:
            return (resolved, CallType.EXTERNAL.value)
        
        # Built-in mi?
        builtins = {'print', 'len', 'range', 'enumerate', 'zip', 'map', 'filter',
                   'open', 'input', 'int', 'str', 'list', 'dict', 'set', 'tuple',
                   'isinstance', 'hasattr', 'getattr', 'setattr', 'super',
                   'classmethod', 'staticmethod', 'property', 'type', 'id',
                   'iter', 'next', 'sum', 'min', 'max', 'abs', 'round',
                   'divmod', 'pow', 'callable', 'repr', 'dir', 'vars',
                   'globals', 'locals', 'eval', 'exec', 'compile',
                   'breakpoint', 'help', 'exit', 'quit'}
        
        if name in builtins:
            return (f"builtins.{name}", CallType.EXTERNAL.value)
        
        # Aynı sınıf içinde mi (metod çağrısı)?
        if self.current_class:
            # Muhtemelen aynı sınıfın başka bir metodu
            return (f"{self.current_class}.{name}", CallType.INTERNAL.value)
        
        # Bilinmeyen - muhtemelen proje içi ama çözümlenemeyen
        return (name, CallType.UNKNOWN.value)
    
    def _resolve_attribute_call(self, func: ast.Attribute) -> Tuple[str, str]:
        """Nitelikli çağrıyı çözümle: obj.method()"""
        obj = self._get_object_chain(func.value)
        method = func.attr
        
        if not obj:
            return (f"<unknown>.{method}", CallType.UNKNOWN.value)
        
        # self.method() çağrısı
        if obj == 'self' and self.current_class:
            return (f"{self.current_class}.{method}", CallType.INTERNAL.value)
        
        # cls.method() çağrısı
        if obj == 'cls' and self.current_class:
            return (f"{self.current_class}.{method}", CallType.INTERNAL.value)
        
        # super().method() çağrısı
        if obj == 'super':
            if self.current_class:
                return (f"{self.current_class}.{method}", CallType.EXTERNAL.value)
            return (f"super.{method}", CallType.EXTERNAL.value)
        
        # Import edilmiş modül çağrısı: os.path.exists()
        resolved = self.import_resolver.resolve_symbol(obj)
        if resolved:
            return (f"{resolved}.{method}", CallType.EXTERNAL.value)
        
        # Çok parçalı obje zinciri: obj.attr.method()
        if '.' in obj:
            parts = obj.split('.')
            first_part = parts[0]
            resolved_first = self.import_resolver.resolve_symbol(first_part)
            if resolved_first:
                # Modül importu var, gerisini birleştir
                full_path = f"{resolved_first}.{'.'.join(parts[1:])}.{method}"
                return (full_path, CallType.EXTERNAL.value)
        
        # self/cls harici attribute erişimi
        # Bu genellikle harici kütüphane veya proje içi nesne
        return (f"{obj}.{method}", CallType.EXTERNAL.value)
    
    def _get_object_chain(self, node: ast.expr) -> Optional[str]:
        """AST node'undan obje zincirini çıkar: obj.attr1.attr2"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parent = self._get_object_chain(node.value)
            if parent:
                return f"{parent}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Call):
            # super() gibi durumlar
            if isinstance(node.func, ast.Name):
                return node.func.id
        elif isinstance(node, ast.Subscript):
            # obj[key] -> obj
            return self._get_object_chain(node.value)
        return None


class SymbolGraph:
    """
    Semboller arası çağrı ilişkilerini tutan graph yapısı.
    
    Özellikler:
    - SymbolExtractor çıktısını input olarak alır
    - AST tabanlı çağrı analizi
    - Import resolution
    - UNKNOWN çağrı raporlama
    - Reverse lookup (called_by) desteği
    """
    
    def __init__(self):
        self.nodes: Dict[str, SymbolNode] = {}  # full_name -> SymbolNode
        self.file_symbols: Dict[str, List[SymbolNode]] = {}  # file -> [symbols]
        self.unresolved_calls: List[Dict[str, Any]] = []  # UNKNOWN çağrılar
        self.stats = {
            'total_symbols': 0,
            'total_calls': 0,
            'internal_calls': 0,
            'external_calls': 0,
            'recursive_calls': 0,
            'unknown_calls': 0,
            'unresolved_calls': []
        }
    
    def build_from_symbols(self, symbols_data: List[Dict[str, Any]], 
                          source_files: Optional[Dict[str, str]] = None):
        """
        Symbol listesinden graph oluştur.
        
        Args:
            symbols_data: SymbolExtractor çıktısı (files listesi)
            source_files: Dosya içerikleri {filepath: source_code}
        """
        # Önce tüm sembolleri node olarak kaydet
        for file_data in symbols_data:
            filepath = file_data.get('file', '')
            symbols = file_data.get('symbols', [])
            
            for sym in symbols:
                self._add_symbol_node(sym, filepath)
        
        # Sonra AST tabanlı çağrı analizi yap
        if source_files:
            self._analyze_calls_ast(source_files)
        
        # Reverse lookup (called_by) ilişkilerini kur
        self._build_reverse_edges()
        
        # İstatistikleri güncelle
        self._update_stats()
    
    def build_from_extractor_output(self, extractor_output: Dict[str, Any],
                                   source_files: Optional[Dict[str, str]] = None):
        """
        SymbolExtractor JSON çıktısından graph oluştur.
        
        Args:
            extractor_output: {"stats": {}, "files": [...]}
            source_files: Dosya içerikleri {filepath: source_code}
        """
        files = extractor_output.get('files', [])
        self.build_from_symbols(files, source_files)
    
    def _add_symbol_node(self, symbol: Dict[str, Any], filepath: str):
        """Bir sembolü node olarak ekle."""
        name = symbol.get('name', '')
        sym_type = symbol.get('type', 'unknown')
        line = symbol.get('line', 0)
        column = symbol.get('column', 0)
        class_name = symbol.get('class')
        module = symbol.get('module')
        
        # Full name oluştur
        if class_name:
            full_name = f"{class_name}.{name}"
        else:
            full_name = name
        
        # Node oluştur
        node = SymbolNode(
            name=name,
            full_name=full_name,
            symbol_type=sym_type,
            file=filepath,
            line=line,
            column=column,
            class_name=class_name,
            module=module
        )
        
        self.nodes[full_name] = node
        
        # File index'e ekle
        if filepath not in self.file_symbols:
            self.file_symbols[filepath] = []
        self.file_symbols[filepath].append(node)
    
    def _analyze_calls_ast(self, source_files: Dict[str, str]):
        """
        AST tabanlı çağrı analizi.
        
        Her dosya için:
        1. AST parse et
        2. Import resolution
        3. Symbol stack ile caller tespiti
        4. Çağrıları kaydet
        """
        for filepath, source_code in source_files.items():
            if filepath not in self.file_symbols:
                continue
            
            # AST extractor çalıştır
            extractor = ASTCallExtractor(
                source_code=source_code,
                filename=filepath
            )
            calls = extractor.extract()
            
            # Çağrıları işle
            for call_info in calls:
                self._process_call(call_info)
    
    def _process_call(self, call_info: Dict[str, Any]):
        """Tek bir çağrıyı işle ve node'lara ekle."""
        caller = call_info['caller']
        callee = call_info['callee']
        call_type = call_info['call_type']
        line = call_info['line']
        column = call_info['column']
        raw_call = call_info['raw_call']
        
        # Caller node'u bul veya oluştur
        caller_node = self.nodes.get(caller)
        if not caller_node:
            # Caller sembol graph'ta yoksa - bu bir hata olmamalı
            # ama yine de kaydetmeyelim çünkü sembol listesi dışında
            return
        
        # Callee tipini doğrula ve güncelle
        if call_type == CallType.INTERNAL.value:
            if callee not in self.nodes:
                # Internal olarak işaretlendi ama graph'ta yok
                # UNKNOWN olarak işaretle
                call_type = CallType.UNKNOWN.value
                self.unresolved_calls.append({
                    "caller": caller,
                    "callee": callee,
                    "line": line,
                    "raw_call": raw_call,
                    "reason": "callee_not_in_graph"
                })
        
        # Call nesnesi oluştur
        call = Call(
            symbol=callee,
            call_type=call_type,
            line=line,
            column=column,
            raw_call=raw_call
        )
        
        # Caller node'a ekle
        caller_node.calls.append(call)
    
    def _build_reverse_edges(self):
        """Called_by (reverse) ilişkilerini kur."""
        for node in self.nodes.values():
            for call in node.calls:
                # Çağrılan sembolü bul
                called_symbol = call.symbol
                if called_symbol in self.nodes:
                    # Reverse edge ekle
                    reverse_call = Call(
                        symbol=node.full_name,
                        call_type=call.call_type,
                        line=call.line,
                        column=call.column,
                        raw_call=call.raw_call
                    )
                    self.nodes[called_symbol].called_by.append(reverse_call)
    
    def _update_stats(self):
        """İstatistikleri güncelle."""
        self.stats['total_symbols'] = len(self.nodes)
        
        total_calls = 0
        internal = 0
        external = 0
        recursive = 0
        unknown = 0
        
        for node in self.nodes.values():
            for call in node.calls:
                total_calls += 1
                if call.call_type == CallType.INTERNAL.value:
                    internal += 1
                elif call.call_type == CallType.EXTERNAL.value:
                    external += 1
                elif call.call_type == CallType.RECURSIVE.value:
                    recursive += 1
                elif call.call_type == CallType.UNKNOWN.value:
                    unknown += 1
        
        self.stats['total_calls'] = total_calls
        self.stats['internal_calls'] = internal
        self.stats['external_calls'] = external
        self.stats['recursive_calls'] = recursive
        self.stats['unknown_calls'] = unknown
        self.stats['unresolved_calls'] = self.unresolved_calls
    
    def get_node(self, full_name: str) -> Optional[SymbolNode]:
        """İsme göre node döndür."""
        return self.nodes.get(full_name)
    
    def get_dependents(self, full_name: str) -> List[str]:
        """
        Bir sembole bağımlı olan (onu çağıran) tüm sembolleri döndür.
        
        Bu 'blast radius' hesaplaması için kullanılır.
        """
        node = self.nodes.get(full_name)
        if not node:
            return []
        
        dependents = set()
        visited = set()
        
        def collect(sym_name: str):
            if sym_name in visited:
                return
            visited.add(sym_name)
            
            sym_node = self.nodes.get(sym_name)
            if sym_node:
                for call in sym_node.called_by:
                    if call.symbol != full_name:  # Kendisi hariç
                        dependents.add(call.symbol)
                        collect(call.symbol)
        
        collect(full_name)
        return list(dependents)
    
    def get_dependencies(self, full_name: str) -> List[str]:
        """Bir sembolün bağımlı olduğu (çağırdığı) tüm sembolleri döndür."""
        node = self.nodes.get(full_name)
        if not node:
            return []
        
        return [call.symbol for call in node.calls 
                if call.call_type in [CallType.INTERNAL.value, CallType.RECURSIVE.value]]
    
    def get_blast_radius(self, full_name: str) -> Dict[str, Any]:
        """
        Bir sembolün 'blast radius'ını hesapla.
        
        Blast radius: Bir değişikliğin etkileyebileceği tüm semboller.
        """
        dependents = self.get_dependents(full_name)
        
        return {
            "symbol": full_name,
            "direct_dependents": [call.symbol for call in 
                                  self.nodes.get(full_name, SymbolNode("", "", "", "", 0)).called_by],
            "total_dependents": len(dependents),
            "all_dependents": dependents,
            "impact_score": len(dependents)  # Basit etki skoru
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Graph'ı sözlük formatına dönüştür."""
        return {
            "symbols": [node.to_dict() for node in self.nodes.values()],
            "graph_stats": self.stats
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Graph'ı JSON formatına dönüştür."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def export_to_json(self, output_path: str):
        """Graph'ı JSON dosyasına kaydet."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())


class SymbolGraphBuilder:
    """
    SymbolExtractor ve kaynak dosyalardan SymbolGraph oluşturan builder.
    """
    
    def __init__(self):
        self.graph = SymbolGraph()
    
    def build_from_directory(self, symbols_json_path: str, 
                            source_dir: str) -> SymbolGraph:
        """
        Dizinden symbol extractor çıktısı ve kaynak dosyalardan graph oluştur.
        
        Args:
            symbols_json_path: SymbolExtractor JSON çıktısı
            source_dir: Kaynak dosyaların bulunduğu dizin
        """
        # Symbol verilerini oku
        with open(symbols_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Kaynak dosyaları oku
        source_files = {}
        files = data.get('files', [])
        
        for file_data in files:
            filepath = file_data.get('file', '')
            full_path = Path(source_dir) / filepath
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as sf:
                        source_files[filepath] = sf.read()
                except Exception:
                    pass
        
        # Graph oluştur
        self.graph.build_from_extractor_output(data, source_files)
        return self.graph
    
    def build_simple(self, symbols_data: List[Dict[str, Any]]) -> SymbolGraph:
        """
        Sadece sembol listesinden graph oluştur (çağrı analizi olmadan).
        
        Bu hızlı bir analiz için kullanılır.
        """
        self.graph.build_from_symbols(symbols_data)
        return self.graph
    
    def build_with_source_mapping(self, symbols_data: List[Dict[str, Any]],
                                   source_mapping: Dict[str, str]) -> SymbolGraph:
        """
        Sembol verisi ve kaynak kod mapping'inden graph oluştur.
        
        Args:
            symbols_data: Symbol listesi
            source_mapping: {filepath: source_code} mapping
        """
        self.graph.build_from_symbols(symbols_data, source_mapping)
        return self.graph


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='BBC Symbol Graph - Symbol call graph builder (v3.6.1 AST-based)'
    )
    parser.add_argument('symbols_json', help='SymbolExtractor JSON output')
    parser.add_argument('--source-dir', '-s', help='Source directory', default='.')
    parser.add_argument('--out', '-o', help='Output JSON file', default='symbol_graph.json')
    parser.add_argument('--blast-radius', '-b', help='Compute blast radius (symbol name)')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--unresolved', '-u', action='store_true', help='Show UNKNOWN calls')
    
    args = parser.parse_args()
    
    # Build graph
    builder = SymbolGraphBuilder()
    graph = builder.build_from_directory(args.symbols_json, args.source_dir)
    
    # Blast radius
    if args.blast_radius:
        radius = graph.get_blast_radius(args.blast_radius)
        print(f"\nBlast Radius: {args.blast_radius}")
        print(f"Affected symbol count: {radius['total_dependents']}")
        print(f"Impact score: {radius['impact_score']}")
        if radius['all_dependents']:
            print("Affected symbols:")
            for sym in radius['all_dependents'][:20]:  # İlk 20
                print(f"  - {sym}")
            if len(radius['all_dependents']) > 20:
                print(f"  ... and {len(radius['all_dependents']) - 20} more")
    
    # Statistics
    if args.stats:
        print(f"\nGraph Statistics:")
        for key, value in graph.stats.items():
            if key != 'unresolved_calls':
                print(f"  {key}: {value}")
    
    # UNKNOWN calls
    if args.unresolved:
        if graph.unresolved_calls:
            print(f"\nUNRESOLVED CALLS ({len(graph.unresolved_calls)}):")
            for call in graph.unresolved_calls[:20]:
                print(f"  {call['caller']} -> {call['callee']} at line {call['line']}")
            if len(graph.unresolved_calls) > 20:
                print(f"  ... and {len(graph.unresolved_calls) - 20} more")
        else:
            print("\nUNRESOLVED CALLS: None")
    
    # Save
    graph.export_to_json(args.out)
    print(f"\nGraph saved: {args.out}")
    
    # Summary
    print(f"\nSummary:")
    print(f"  Total symbols: {graph.stats['total_symbols']}")
    print(f"  Total calls: {graph.stats['total_calls']}")
    print(f"  Internal: {graph.stats['internal_calls']}")
    print(f"  External: {graph.stats['external_calls']}")
    print(f"  Recursive: {graph.stats['recursive_calls']}")
    print(f"  Unknown: {graph.stats['unknown_calls']}")


if __name__ == '__main__':
    main()
