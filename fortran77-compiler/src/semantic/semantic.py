from dataclasses import dataclass

from .symbolTable import SymbolTable, VarSymbol, SubprogramSymbol
from parser.parser import ASTVisitor
from parser.ast import (
    Node,
    Program, MainProgram, FunctionDef, SubroutineDef, 
    Body, TypeDecl, 
    LabeledStmt, Assign, IfThen, LogicalIf, DoLoop, Goto, Continue, 
    PrintStmt, ReadStmt, CallStmt, ReturnStmt, StopStmt,
    Var, VarOrFuncCall, ArithmeticBinOp, LogicalBinOp, RelationalBinOp,
    ArithmeticUnaryOp, LogicalUnaryOp, FuncCall,
    IntLit, RealLit, StringLit, BoolLit
)

@dataclass
class SemanticError(Exception):
    """
    Erro gerado durante a análise semântica.
    """
    message: str    # mensagem de erro
    line:    int    # numero da linha

    def __str__(self) -> str:
        return f"[Semantic Analyser] Linha {self.line}: {self.message}"


# --- Constantes auxiliares -------------------------------------------------

# Tipos que podem ser operandos de operações aritméticas
_NUMERIC_TYPES  = {'INTEGER', 'REAL'}

# Funções intrínsecas
# (aridade, return_type)
_INTRINSICS: dict[str, tuple[int | None, str]] = {
    'MOD':  (2,    'INTEGER'),
    'SQRT': (1,    'REAL'),
    'MAX':  (None, 'REAL'),    # aridade >= 2 args
    'MIN':  (None, 'REAL'),    # aridade >= 2 args
}


class SemanticAnalyser(ASTVisitor):
    """
    Estado interno:
        _errors       - lista de SemanticError acumulados
        _symbol_table - tabela de símbolos
        _labels       - dict {label: lineno} dos labels definidos na unidade
                        de programa actual; reiniciado a cada nova unidade
        _goto_refs    - lista de (label, lineno) de referências a labels
                        (GOTO / DO) encontradas na unidade actual; validadas
                        no final de cada unidade por _check_label_refs()
        _do_stack     - lista de (label_terminacao, nome_var_controlo) dos
                        DO loops ativos; usada para fechar o loop correcto
                        quando se encontra o CONTINUE com o label certo
        _do_vars      - conjunto com os nomes das variáveis de controlo dos
                        DO loops activos; impede que sejam modificadas
        _current_unit - nome da unidade de programa actual
        _current_kind - 'PROGRAM' | 'FUNCTION' | 'SUBROUTINE'
    """

    def __init__(self):
        self._errors:       list[SemanticError]   = []
        self._symbol_table: SymbolTable           = SymbolTable()
        self._labels:       dict[int, int]        = {}
        self._goto_refs:    list[tuple[int, int]] = []
        self._do_stack:     list[tuple[int, str]] = []
        self._do_vars:      set[str]              = set()
        self._current_unit: str | None            = None
        self._current_kind: str | None            = None

    def analyse(self, ast: Program) -> list[SemanticError]:
        self._errors = []
        self.visit(ast)
        return list(self._errors)

    @property
    def has_errors(self) -> bool:
        return len(self._errors) > 0

    
    # --- Erros semânticos --------------------------------------------------
    def _error(self, message: str, line: int) -> None:
        self._errors.append(SemanticError(message=message, line=line))


    # --- Labels ------------------------------------------------------------
    def _reset_labels(self) -> None:
        """Reinicia o estado de labels ao entrar numa nova unidade de programa."""
        self._labels    = {}
        self._goto_refs = []

    def _define_label(self, label: int, lineno: int) -> None:
        """
        Regista a definição de um label.
        Emite erro se o label já foi definido nesta unidade.
        """
        if label in self._labels:
            self._error(f"Label {label} definido mais do que uma vez.", lineno)
        else:
            self._labels[label] = lineno

    def _reference_label(self, label: int, lineno: int) -> None:
        """
        Regista uma referência a um label (GOTO ou DO).
        """
        self._goto_refs.append((label, lineno))

    def _check_label_refs(self) -> None:
        """
        Verifica que todas as referências a labels acumuladas na unidade
        actual correspondem a labels definidos.
        Deve ser chamado no final de cada unidade (antes do pop do scope).
        """
        for label, lineno in self._goto_refs:
            if label not in self._labels:
                self._error(
                    f"Label {label} referenciado mas não definido nesta unidade.",
                    lineno,
                )

    # --- DO loops ----------------------------------------------------------
    def _close_do(self, label: int) -> None:
        """
        Fecha o DO loop mais interior que aguardava o label indicado.
        Remove a variável de controlo correspondente de _do_vars.
        Chamado em visit_LabeledStmt quando a instrução associada é CONTINUE.
        """
        for i in range(len(self._do_stack) - 1, -1, -1):
            if self._do_stack[i][0] == label:
                _, var = self._do_stack.pop(i)
                self._do_vars.discard(var)
                return
            
    # --- Visita às unidades de programa ------------------------------------
    def visit_Program(self, node: Program) -> None:
        """
        Visita a raiz da AST.

        Regista todos os subprogramas no scope global antes de analisar qualquer unidade,
        para que possam ser referenciados mesmo que a definição apareça depois de uma chamada.
        """
        # registo dos subprogramas
        for unit in node.units:
            if isinstance(unit, (FunctionDef, SubroutineDef)):
                self._regist_subprogram(unit)

        # analisa cada unidade de programa
        for unit in node.units:
            self.visit(unit)

    def _regist_subprogram(self, unit: FunctionDef | SubroutineDef) -> None:
        param_names = unit.params
        param_types = ['UNKNOWN'] * len(param_names)

        # se for Function, tenta descobrir o tipo de retorno
        return_type = 'UNKNOWN'
        if isinstance(unit, FunctionDef):
            return_type = unit.return_type if unit.return_type else 'UNKNOWN'

        # procura declarações de tipo no body para refinar os tipos dos parâmetros e do retorno
        for decl in unit.body.declarations:
            if isinstance(decl, TypeDecl):
                for vd in decl.variables:
                    if vd.name in param_names:
                        idx = param_names.index(vd.name)
                        param_types[idx] = decl.type_name
                    elif isinstance(unit, FunctionDef) and vd.name == unit.name:
                        return_type = decl.type_name

        if isinstance(unit, FunctionDef):
            sym = SubprogramSymbol(
                name=unit.name,
                kind='FUNCTION',
                return_type=return_type,
                param_names=param_names,
                param_types=param_types,
            )
        else:
            sym = SubprogramSymbol(
                name=unit.name,
                kind='SUBROUTINE',
                return_type=None,
                param_names=param_names,
                param_types=param_types,
            )

        if not self._symbol_table.declare_subprogram(sym):
            self._error(
                f"Subprograma '{unit.name}' definido mais do que uma vez.",
                unit.lineno,
            )

    def visit_MainProgram(self, node: MainProgram) -> None:
        """
        Analisa o programa principal.
        Cria um novo scope local, analisa o body e valida os labels no final.
        """
        self._current_unit = node.name
        self._current_kind = 'PROGRAM'
        self._reset_labels()
        self._do_stack = []
        self._do_vars  = set()
        self._symbol_table.push()

        self.visit(node.body)

        self._check_label_refs()
        self._symbol_table.pop()

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """
        Analisa uma função.
        No final verifica se a variável de retorno foi inicializada, pois
        uma função que nunca atribui o seu próprio nome não tem valor de
        retorno definido.
        """
        self._current_unit = node.name
        self._current_kind = 'FUNCTION'
        self._reset_labels()
        self._do_stack = []
        self._do_vars  = set()
        self._symbol_table.push()

        # parâmetros formais: índices negativos, não avançam o contador local
        for i, pname in enumerate(node.params):
            self._symbol_table.declare_param(
                VarSymbol(name=pname, var_type='UNKNOWN'),
                param_index=i,
            )

        # variável de retorno: primeiro índice local (0), acedida com PUSHL 0
        ret_type = node.return_type if node.return_type else 'UNKNOWN'
        self._symbol_table.declare_var(
            VarSymbol(name=node.name, var_type=ret_type)
        )

        self.visit(node.body)

        # verifica se a variável de retorno foi inicializada
        ret = self._symbol_table.lookup_var(node.name)
        if ret and not ret.initialized:
            self._error(
                f"Função '{node.name}': a variável de retorno '{node.name}' "
                f"pode não ser inicializada antes do RETURN.",
                node.lineno,
            )

        self._check_label_refs()
        self._symbol_table.pop()

    def visit_SubroutineDef(self, node: SubroutineDef) -> None:
        """
        Analisa uma subrotina.
        Declara os parâmetros formais com tipo 'UNKNOWN', refinado pelas
        declarações de tipo no body.
        """
        self._current_unit = node.name
        self._current_kind = 'SUBROUTINE'
        self._reset_labels()
        self._do_stack = []
        self._do_vars  = set()
        self._symbol_table.push()

        # parâmetros formais: índices negativos, não avançam o contador local
        for i, pname in enumerate(node.params):
            self._symbol_table.declare_param(
                VarSymbol(name=pname, var_type='UNKNOWN'),
                param_index=i,
            )

        self.visit(node.body)

        self._check_label_refs()
        self._symbol_table.pop()

    def visit_Body(self, node: Body) -> None:
        """
        Visita o body de uma unidade de programa.
        """
        for decl in node.declarations:
            self.visit(decl)
        for stmt in node.statements:
            self.visit(stmt)

    # --- Visita às declarações ---------------------------------------------
    def visit_TypeDecl(self, node: TypeDecl) -> None:
        """
        Processa uma declaração de tipo (ex: INTEGER N, NUMS(5)).
        """
        for vd in node.variables:
            existing = self._symbol_table.lookup_var(vd.name)

            if existing and existing.var_type == 'UNKNOWN':
                # parâmetro formal: actualiza tipo e dimensão; índice mantém-se
                existing.var_type  = node.type_name
                existing.dimension = vd.dimension
            elif existing:
                self._error(
                    f"Variável '{vd.name}' declarada mais do que uma vez.",
                    node.lineno,
                )
            else:
                self._symbol_table.declare_var(
                    VarSymbol(
                        name=vd.name,
                        var_type=node.type_name,
                        dimension=vd.dimension,
                    )
                )

    # --- Visita às linhas com label ----------------------------------------
    def visit_LabeledStmt(self, node: LabeledStmt) -> None:
        """
        Regista o label desta linha e visita a instrução contida.
        Se a instrução for CONTINUE, fecha o DO loop que aguardava este label.
        """
        self._define_label(node.label, node.lineno)

        if isinstance(node.stmt, Continue):
            self._close_do(node.label)

        self.visit(node.stmt)

    # --- Visita às instruções executáveis ----------------------------------
    def visit_Assign(self, node: Assign) -> None:
        """
        Verifica uma atribuição:
        """
        # determina o nome da variável destino
        if isinstance(node.target, Var):
            target_name = node.target.name
        elif isinstance(node.target, VarOrFuncCall):
            target_name = node.target.name
        else:
            target_name = None

        # proibido modificar a variável de controlo de um DO ativo
        if target_name and target_name in self._do_vars:
            self._error(
                f"A variável de controlo '{target_name}' não pode ser "
                f"modificada dentro do DO loop.",
                node.lineno,
            )

        ltype = self._type_of(node.target)
        rtype = self._type_of(node.value)
        self._check_assign_compat(ltype, rtype, node.lineno)

        if target_name:
            self._symbol_table.initialize(target_name)

    def visit_IfThen(self, node: IfThen) -> None:
        """Verifica que a condição do IF THEN é do tipo LOGICAL."""
        ctype = self._type_of(node.condition)
        if ctype is not None and ctype != 'LOGICAL':
            self._error(
                "A condição do IF deve ser do tipo LOGICAL.",
                node.lineno,
            )
        for stmt in node.then_body:
            self.visit(stmt)
        for stmt in node.else_body:
            self.visit(stmt)

    def visit_LogicalIf(self, node: LogicalIf) -> None:
        """Verifica que a condição do IF lógico é do tipo LOGICAL."""
        ctype = self._type_of(node.condition)
        if ctype is not None and ctype != 'LOGICAL':
            self._error(
                "A condição do IF lógico deve ser do tipo LOGICAL.",
                node.lineno,
            )
        self.visit(node.stmt)

    def visit_DoLoop(self, node: DoLoop) -> None:
        """
        Verifica o DO loop:

        O fecho do loop (pop do _do_stack) é feito em _close_do quando o
        CONTINUE com o label correspondente for encontrado.
        """
        self._reference_label(node.label, node.lineno)

        # verifica a variável de controlo
        var_sym = self._symbol_table.lookup_var(node.var)
        if var_sym is None:
            self._error(
                f"Variável de controlo '{node.var}' não declarada.",
                node.lineno,
            )
        elif var_sym.var_type not in _NUMERIC_TYPES:
            self._error(
                f"A variável de controlo '{node.var}' deve ser INTEGER ou REAL.",
                node.lineno,
            )

        # verifica os limites
        for expr, label in [(node.start, 'inicial'), (node.stop, 'final')]:
            t = self._type_of(expr)
            if t is not None and t not in _NUMERIC_TYPES:
                self._error(
                    f"O limite {label} do DO deve ser numérico.", node.lineno
                )

        if node.step is not None:
            t = self._type_of(node.step)
            if t is not None and t not in _NUMERIC_TYPES:
                self._error("O incremento do DO deve ser numérico.", node.lineno)

        # abre o loop
        self._do_stack.append((node.label, node.var))
        self._do_vars.add(node.var)

        for stmt in node.body:
            self.visit(stmt)
        # Fecha o loop automaticamente, pois o CONTINUE é absorvido pelo AST
        self._do_vars.discard(node.var)
        if self._do_stack:
            for i in range(len(self._do_stack) - 1, -1, -1):
                if self._do_stack[i][0] == node.label:
                    self._do_stack.pop(i)
                    break
        self._define_label(node.label, node.lineno)

    def visit_Goto(self, node: Goto) -> None:
        self._reference_label(node.label, node.lineno)

    def visit_Continue(self, node: Continue) -> None:
        """
        CONTINUE sem label não requer verificação adicional.
        O fecho do DO loop é tratado em visit_LabeledStmt.
        """
        pass

    def visit_PrintStmt(self, node: PrintStmt) -> None:
        for item in node.items:
            self._type_of(item)

    def visit_ReadStmt(self, node: ReadStmt) -> None:
        for target in node.targets:
            self._type_of(target)
            # Regista a variável lida como inicializada
            if isinstance(target, Var):
                self._symbol_table.initialize(target.name)
            elif isinstance(target, VarOrFuncCall):
                self._symbol_table.initialize(target.name)

    def visit_CallStmt(self, node: CallStmt) -> None:
        """
        Verifica uma chamada a subrotina com CALL:
        Visita também os argumentos para verificação de tipos.
        """
        sym = self._symbol_table.lookup_subprogram(node.name)
        if sym is None:
            self._error(f"Subrotina '{node.name}' não definida.", node.lineno)
            for arg in node.args:
                self._type_of(arg)
        else:
            if sym.is_function:
                self._error(
                    f"'{node.name}' é uma FUNCTION; não pode ser chamada com CALL.",
                    node.lineno,
                )
                for arg in node.args:
                    self._type_of(arg)
            elif len(node.args) != sym.arity:
                self._error(
                    f"Subrotina '{node.name}' espera {sym.arity} argumento(s), "
                    f"recebeu {len(node.args)}.",
                    node.lineno,
                )
                for arg in node.args:
                    self._type_of(arg)
            else:
                for i, arg in enumerate(node.args):
                    arg_type = self._type_of(arg)
                    expected_type = sym.param_types[i]
                    if arg_type is not None and expected_type != 'UNKNOWN':
                        if arg_type != expected_type:
                            self._error(
                                f"Argumento {i+1} da chamada a '{node.name}' deve "
                                f"ser {expected_type}, recebido {arg_type}.",
                                node.lineno,
                            )

    def visit_ReturnStmt(self, node: ReturnStmt) -> None:
        """RETURN é sempre válido; nenhuma verificação adicional."""
        pass

    def visit_StopStmt(self, node: StopStmt) -> None:
        """STOP é sempre válido."""
        pass


    # --- Inferência de tipos -----------------------------------------------
    def _type_of(self, node: Node) -> str | None:
        """
        Infere e devolve o tipo de uma expressão como string.
        """
        if isinstance(node, IntLit):    return 'INTEGER'
        if isinstance(node, RealLit):   return 'REAL'
        if isinstance(node, StringLit): return 'CHARACTER'
        if isinstance(node, BoolLit):   return 'LOGICAL'

        if isinstance(node, Var):               return self._type_of_var(node)
        if isinstance(node, VarOrFuncCall):     return self._type_of_var_or_func(node)
        if isinstance(node, ArithmeticBinOp):   return self._type_of_ArithmeticBinOp(node)
        if isinstance(node, LogicalBinOp):      return self._type_of_LogicalBinOp(node)
        if isinstance(node, RelationalBinOp):   return self._type_of_RelationalBinOp(node)
        if isinstance(node, ArithmeticUnaryOp): return self._type_of_ArithmeticUnaryOp(node)
        if isinstance(node, LogicalUnaryOp):    return self._type_of_LogicalUnaryOp(node)
        if isinstance(node, FuncCall):          return self._type_of_intrinsic(node)

        return None

    def _type_of_var(self, node: Var) -> str | None:
        """
        Devolve o tipo de uma variável simples (sem índices).
        Emite erro se não estiver declarada.
        Emite erro se for um array usado sem índices.
        """
        sym = self._symbol_table.lookup_var(node.name)
        if sym is None:
            self._error(f"Variável '{node.name}' não declarada.", node.lineno)
            return None
        if sym.is_array:
            self._error(
                f"'{node.name}' é um array; deve ser acedido com índice.",
                node.lineno,
            )
        return sym.var_type

    def _type_of_var_or_func(self, node: VarOrFuncCall) -> str | None:
        """
        Trata um nó VarOrFuncCall, que o parser produz para qualquer
        expressão da forma  IDEN(args)  — pode ser:

            (a) Acesso a array  - IDEN está declarado como VarSymbol com
                                is_array == True
            (b) Chamada de função de utilizador - IDEN está declarado como
                                SubprogramSymbol com kind == 'FUNCTION' (mesmo
                                que exista um VarSymbol escalar local com o mesmo nome,
                                que é o padrão no local onde a função é chamada)

        Regras de resolução (por ordem):
            1. Procura primeiro na symbol table como variável.
                Se encontrar e for array (ou não for array local, mas tmb não for função global):
                - verifica que o número de argumentos é 1 (arrays são
                    unidimensionais neste compilador);
                - verifica que o índice é INTEGER;
                - devolve o tipo do array.
                Se encontrar como escalar MAS não houver função correspondente:
                - emite erro (escalar usado com índice).
            2. Se não for variável array, procura como subprograma (ou se for Var escalar + função).
                Se encontrar e for FUNCTION:
                - verifica a aridade;
                - devolve o tipo de retorno.
                Se encontrar mas for SUBROUTINE:
                - emite erro (subrotina usada como expressão).
            3. Se não encontrar em nenhum dos dois:
                - emite erro (identificador não declarado).
        """
        var_sym  = self._symbol_table.lookup_var(node.name)
        func_sym = self._symbol_table.lookup_subprogram(node.name)

        # --- Caso (a): acesso a array ---
        if var_sym is not None:
            # Se é também função globamente, e não é array local, assumimos que é chamada de função!
            if not var_sym.is_array and func_sym is not None:
                pass # Prossegue para tratar como função (Caso b)
            elif not var_sym.is_array:
                self._error(
                    f"'{node.name}' é uma variável escalar; "
                    f"não pode ser indexada.",
                    node.lineno,
                )
                return var_sym.var_type
            else:
                # Arrays são unidimensionais: deve haver exactamente 1 argumento
                if len(node.args) != 1:
                    self._error(
                        f"Array '{node.name}' é unidimensional; "
                        f"esperado 1 índice, recebeu {len(node.args)}.",
                        node.lineno,
                    )
                else:
                    itype = self._type_of(node.args[0])
                    if itype is not None and itype != 'INTEGER':
                        self._error(
                            f"O índice de '{node.name}' deve ser INTEGER.",
                            node.lineno,
                        )
                return var_sym.var_type

        # --- Caso (b): chamada de função de utilizador ---
        if func_sym is not None:
            if func_sym.is_subroutine:
                self._error(
                    f"'{node.name}' é uma SUBROUTINE; "
                    f"não pode ser usada como expressão.",
                    node.lineno,
                )
                return None

            # É uma FUNCTION: verifica a aridade
            if len(node.args) != func_sym.arity:
                self._error(
                    f"Função '{node.name}' espera {func_sym.arity} "
                    f"argumento(s), recebeu {len(node.args)}.",
                    node.lineno,
                )
                for arg in node.args:
                    self._type_of(arg)
            else:
                # Aridade correta, validar também os tipos dos args
                for i, arg in enumerate(node.args):
                    arg_type = self._type_of(arg)
                    expected_type = func_sym.param_types[i]
                    if arg_type is not None and expected_type != 'UNKNOWN':
                        if arg_type != expected_type:
                            self._error(
                                f"Argumento {i+1} da função '{node.name}' deve "
                                f"ser {expected_type}, recebido {arg_type}.",
                                node.lineno,
                            )
            return func_sym.return_type

        # --- Caso (c): identificador desconhecido ---
        self._error(
            f"'{node.name}' não está declarado.",
            node.lineno,
        )
        return None

    def _type_of_ArithmeticBinOp(self, node: ArithmeticBinOp) -> str | None:
        lt = self._type_of(node.left)
        rt = self._type_of(node.right)

        for t, side in [(lt, 'esquerdo'), (rt, 'direito')]:
            if t is not None and t not in _NUMERIC_TYPES:
                self._error(
                    f"Operando {side} de '{node.op}' deve ser numérico, "
                    f"encontrado {t}.",
                    node.lineno,
                )
        if lt == 'REAL' or rt == 'REAL':
            return 'REAL'
        return 'INTEGER'

    def _type_of_RelationalBinOp(self, node: RelationalBinOp) -> str | None:
        lt = self._type_of(node.left)
        rt = self._type_of(node.right)

        valid = _NUMERIC_TYPES | {'CHARACTER'}
        for t, side in [(lt, 'esquerdo'), (rt, 'direito')]:
            if t is not None and t not in valid:
                self._error(
                    f"Operando {side} de '{node.op}' deve ser numérico "
                    f"ou CHARACTER, encontrado {t}.",
                    node.lineno,
                )
        if (lt in _NUMERIC_TYPES and rt == 'CHARACTER') or (rt in _NUMERIC_TYPES and lt == 'CHARACTER'):
            self._error(
                f"Comparação inválida entre tipo numérico e CHARACTER "
                f"com '{node.op}'.",
                node.lineno,
            )
        return 'LOGICAL'

    def _type_of_LogicalBinOp(self, node: LogicalBinOp) -> str | None:
        lt = self._type_of(node.left)
        rt = self._type_of(node.right)

        for t, side in [(lt, 'esquerdo'), (rt, 'direito')]:
            if t is not None and t != 'LOGICAL':
                self._error(
                    f"Operando {side} de '{node.op}' deve ser LOGICAL, "
                    f"encontrado {t}.",
                    node.lineno,
                )
        return 'LOGICAL'

    def _type_of_ArithmeticUnaryOp(self, node: ArithmeticUnaryOp) -> str | None:
        ot = self._type_of(node.operand)

        if ot is not None and ot not in _NUMERIC_TYPES:
            self._error(
                f"Operando de '{node.op}' unário deve ser numérico, "
                f"encontrado {ot}.",
                node.lineno,
            )
        return ot

    def _type_of_LogicalUnaryOp(self, node: LogicalUnaryOp) -> str | None:
        ot = self._type_of(node.operand)

        if ot is not None and ot != 'LOGICAL':
            self._error(
                f"Operando de '{node.op}' deve ser LOGICAL, encontrado {ot}.",
                node.lineno,
            )
        return 'LOGICAL'

    def _type_of_intrinsic(self, node: FuncCall) -> str | None:
        """
        Verifica e devolve o tipo de retorno de uma chamada a função
        intrínseca (MOD, SQRT, MAX, MIN).
        """
        expected_arity, ret_type = _INTRINSICS[node.name]

        if expected_arity is not None:
            # Aridade fixa (MOD, SQRT)
            if len(node.args) != expected_arity:
                self._error(
                    f"'{node.name}' espera {expected_arity} argumento(s), "
                    f"recebeu {len(node.args)}.",
                    node.lineno,
                )
            for arg in node.args:
                t = self._type_of(arg)
                if t is not None and t not in _NUMERIC_TYPES:
                    self._error(
                        f"Argumento para a função '{node.name}' deve ser numérico.", 
                        node.lineno
                    )
        else:
            # MAX / MIN precisam de pelo menos 2 args numéricos
            if len(node.args) < 2:
                self._error(
                    f"'{node.name}' requer pelo menos 2 argumentos.",
                    node.lineno,
                )
            for arg in node.args:
                t = self._type_of(arg)
                if t is not None and t not in _NUMERIC_TYPES:
                    self._error(
                        f"Os argumentos de '{node.name}' devem ser numéricos.",
                        node.lineno,
                    )
            # Afina o tipo de retorno
            arg_types = [self._type_of(a) for a in node.args]
            return 'REAL' if 'REAL' in arg_types else 'INTEGER'

        return ret_type


    def _check_assign_compat(self, ltype: str | None, rtype: str | None, lineno: int) -> None:
        """
        Verifica a compatibilidade de tipos numa atribuição.
        """
        if ltype is None or rtype is None:
            return
        if ltype in _NUMERIC_TYPES and rtype in _NUMERIC_TYPES:
            return   # conversão numérica implícita permitida
        if ltype != rtype:
            self._error(
                f"Tipos incompatíveis na atribuição: "
                f"variável é {ltype} mas o valor é {rtype}.",
                lineno,
            )