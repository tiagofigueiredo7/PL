from dataclasses import dataclass, field

@dataclass
class VarSymbol:
    """
    Entrada na symbol table para uma variável.
    """
    
    name:        str
    var_type:    str
    dimension:   int  = 0      # 0 = escalar; >= 1 = array
    initialized: bool = False
    index:       int  = -1     # índice na stack da VM (-1 = ainda não atribuído)
    is_param:    bool = False   # True se for parâmetro formal de função/subrotina

    @property
    def is_array(self) -> bool:
        return self.dimension > 0

    @property
    def size(self) -> int:
        """
        Espaço ocupado na VM.
        """
        return self.dimension if self.is_array else 1


@dataclass
class SubprogramSymbol:
    """
    Entrada na symbol table para uma função ou subrotina.
    """
    
    name:        str
    kind:        str
    return_type: str | None
    param_names: list[str] = field(default_factory=list)
    param_types: list[str] = field(default_factory=list)

    @property
    def arity(self) -> int:
        return len(self.param_names)

    @property
    def is_function(self) -> bool:
        return self.kind == 'FUNCTION'

    @property
    def is_subroutine(self) -> bool:
        return self.kind == 'SUBROUTINE'


class SymbolTable:
    def __init__(self):
        self._table:    list[dict] = [{}]  # começa com o scope global
        self._counters: list[int]  = [0]   # contador de índices por scope

    # --- Gestão de scopes --------------------------------------------------
    def push(self) -> None:
        """
        Adiciona um novo scope.
        """
        self._table.append({})
        self._counters.append(0)

    def pop(self) -> None:
        """
        Sai do scope actual e descarta-o.
        """
        if len(self._table) > 1:
            self._table.pop()
            self._counters.pop()

    @property
    def is_global(self) -> bool:
        """True se estamos no scope global (programa principal)."""
        return len(self._table) == 1

    # --- Declaração --------------------------------------------------------

    def declare_var(self, symbol: VarSymbol) -> bool:
        if symbol.name in self._table[-1]:
            return False  # variável já declarada no scope actual

        symbol.index = self._counters[-1]
        self._counters[-1] += symbol.size
        self._table[-1][symbol.name] = symbol
        return True

    def declare_param(self, symbol: VarSymbol, param_index: int) -> bool:
        if symbol.name in self._table[-1]:
            return False

        symbol.index    = -(param_index + 1)
        symbol.is_param = True
        self._table[-1][symbol.name] = symbol
        return True

    def declare_subprogram(self, symbol: SubprogramSymbol) -> bool:
        """
        Regista uma função ou subrotina no scope global (índice 0).
        Sempre no scope global para que possa ser referenciada a partir
        de qualquer unidade de programa.
        """
        if symbol.name in self._table[0]:
            return False  # função/subrotina já declarada no scope global
        self._table[0][symbol.name] = symbol
        return True

    # --- Pesquisa ----------------------------------------------------------

    def lookup_var(self, name: str) -> VarSymbol | None:
        for scope in reversed(self._table):
            entry = scope.get(name)
            if isinstance(entry, VarSymbol):
                return entry
        return None

    def lookup_subprogram(self, name: str) -> SubprogramSymbol | None:
        entry = self._table[0].get(name)
        if isinstance(entry, SubprogramSymbol):
            return entry
        return None

    # --- Inicialização -----------------------------------------------------

    def initialize(self, name: str) -> bool:
        for scope in reversed(self._table):
            entry = scope.get(name)
            if isinstance(entry, VarSymbol):
                entry.initialized = True
                return True
        return False