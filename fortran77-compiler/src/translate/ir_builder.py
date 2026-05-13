from parser.parser import ASTVisitor
from parser.ast import (
    Node,
    Program, MainProgram, FunctionDef, SubroutineDef,
    TypeDecl,
    LabeledStmt, Assign, IfThen, LogicalIf, DoLoop, Goto, Continue,
    PrintStmt, ReadStmt, CallStmt, ReturnStmt, StopStmt,
    Var, VarOrFuncCall, ArithmeticBinOp, LogicalBinOp, RelationalBinOp,
    ArithmeticUnaryOp, LogicalUnaryOp, FuncCall,
    IntLit, RealLit, StringLit, BoolLit,
)
from semantic.symbolTable import SymbolTable, VarSymbol, SubprogramSymbol
from .ir import (
    IRInstr, IRUnit, IRProgram,
    IRPushI, IRPushF, IRPushS, IRPushN,
    IRPushG, IRPushL, IRStoreG, IRStoreL,
    IRAlloc, IRLoadN, IRStoreN,
    IRPop, IRSwap, IRCopyK,
    IRAdd, IRSub, IRMul, IRDiv, IRMod,
    IRFAdd, IRFSub, IRFMul, IRFDiv,
    IRAnd, IROr, IRNot, IREqual,
    IRInf, IRInfEq, IRSup, IRSupEq,
    IRFInf, IRFInfEq, IRFSup, IRFSupEq,
    IRItoF, IRFtoI, IRAtoi, IRAtof,
    IRLabel, IRJump, IRJZ, IRPushA, IRCall, IRReturn,
    IRRead, IRWriteI, IRWriteF, IRWriteS, IRWriteLn,
    IRStart, IRStop,
)


# Mapeamento de operadores relacionais (inteiros / reais) para classe IR
_REL_INT = {
    '.EQ.': IREqual,  '.NE.': None,
    '.LT.': IRInf,    '.LE.': IRInfEq,
    '.GT.': IRSup,    '.GE.': IRSupEq,
}
_REL_REAL = {
    '.EQ.': IREqual,  '.NE.': None,
    '.LT.': IRFInf,   '.LE.': IRFInfEq,
    '.GT.': IRFSup,   '.GE.': IRFSupEq,
}

# Mapeamento de operadores aritméticos para classe IR
_ARITH_INT  = {'+': IRAdd,  '-': IRSub,  '*': IRMul,  '/': IRDiv}
_ARITH_REAL = {'+': IRFAdd, '-': IRFSub, '*': IRFMul, '/': IRFDiv}


class IRBuilder(ASTVisitor):
    """
    Percorre a AST e emite instruções IR organizadas em unidades de programa.
    """
    def __init__(self) -> None:
        self._program:       IRProgram         = IRProgram()
        self._unit:          IRUnit | None      = None
        self._symbols:       SymbolTable        = SymbolTable()
        self._label_cnt:     int                = 0
        self._in_global:     bool               = True
        self._current_unit:  str | None         = None
        self._current_kind:   str | None         = None
        self._current_arity:  int               = 0
        self._current_n_eff:  int               = 0
        self._needs_power:    bool               = False

    def build(self, ast: Program) -> tuple[IRProgram, bool]:
        """
        Constrói e devolve (IRProgram, needs_power).
        needs_power indica se deve ser emitido o helper POWERFUNClabel no fim.
        """
        self._program    = IRProgram()
        self._symbols    = SymbolTable()
        self._label_cnt  = 0
        self._in_global  = True
        self._needs_power = False

        # Regista todos os subprogramas no scope global antes de traduzir qualquer unidade
        for unit in ast.units:
            if isinstance(unit, (FunctionDef, SubroutineDef)):
                self._register_subprogram(unit)

        self.visit(ast)
        return self._program, self._needs_power

    def _emit(self, *instrs: IRInstr) -> None:
        self._unit.instrs.extend(instrs)

    def _new_label(self) -> int:
        self._label_cnt += 1
        return self._label_cnt

    # --- Auxiliares de acesso a variáveis ----------------------------------
    def _push_var(self, sym: VarSymbol) -> None:
        """Emite PUSHG/PUSHL consoante o scope atual."""
        if self._in_global:
            self._emit(IRPushG(sym.index))
        else:
            self._emit(IRPushL(sym.index))

    def _store_var(self, sym: VarSymbol) -> None:
        """Emite STOREG/STOREL consoante o scope atual."""
        if self._in_global:
            self._emit(IRStoreG(sym.index))
        else:
            self._emit(IRStoreL(sym.index))

    def _push_array_elem(self, sym: VarSymbol, index_node: Node) -> None:
        self._push_var(sym)              # endereço da heap (gp/fp[idx])
        self.visit(index_node)           # índice Fortran (1-based)
        self._emit(IRPushI(1), IRSub())  # → 0-based
        self._emit(IRLoadN())

    def _begin_array_store(self, sym: VarSymbol, index_node: Node) -> None:
        self._push_var(sym)
        self.visit(index_node)
        self._emit(IRPushI(1), IRSub())  # 0-based

    def _end_array_store(self) -> None:
        """Emite STOREN para concluir o store de array."""
        self._emit(IRStoreN())

    # --- Mudança de tipo ---------------------------------------------------
    def _switch_to_real(self, t: str) -> None:
        if t == 'INTEGER':
            self._emit(IRItoF())

    def _switch_to_int(self, t: str) -> None:
        if t == 'REAL':
            self._emit(IRFtoI())


    def _register_subprogram(self, unit: FunctionDef | SubroutineDef) -> None:
        """Regista um subprograma no scope global para lookups de chamadas."""
        param_names = list(unit.params)
        param_types = ['UNKNOWN'] * len(param_names)
        return_type = None

        if isinstance(unit, FunctionDef):
            return_type = unit.return_type or 'UNKNOWN'

        for decl in unit.body.declarations:
            if isinstance(decl, TypeDecl):
                for vd in decl.variables:
                    if vd.name in param_names:
                        param_types[param_names.index(vd.name)] = decl.type_name
                    if isinstance(unit, FunctionDef) and vd.name == unit.name:
                        return_type = decl.type_name

        kind = 'FUNCTION' if isinstance(unit, FunctionDef) else 'SUBROUTINE'
        self._symbols.declare_subprogram(SubprogramSymbol(
            name=unit.name, kind=kind,
            return_type=return_type,
            param_names=param_names,
            param_types=param_types,
        ))

    def _process_decl(self, node: TypeDecl) -> None:
        """Atualiza a symbol table com declarações de tipo."""
        for vd in node.variables:
            existing = self._symbols.lookup_var(vd.name)
            if existing and existing.var_type == 'UNKNOWN':
                # Parâmetro formal: actualiza tipo e dimensão, mantém índice negativo
                existing.var_type  = node.type_name
                existing.dimension = vd.dimension
            elif existing is None:
                self._symbols.declare_var(VarSymbol(
                    name=vd.name,
                    var_type=node.type_name,
                    dimension=vd.dimension,
                ))

    def _count_locals(self) -> int:
        """Total de slots locais não-parâmetro no scope atual."""
        scope = self._symbols._table[-1]
        return sum(
            sym.size for sym in scope.values()
            if isinstance(sym, VarSymbol) and not sym.is_param
        )

    def _emit_array_allocs(self) -> None:
        """
        Emite ALLOC + STORE para cada array declarado no scope atual.
        """
        scope = self._symbols._table[-1]
        for sym in scope.values():
            if isinstance(sym, VarSymbol) and sym.is_array and not sym.is_param:
                self._emit(IRAlloc(sym.dimension))   # aloca dimension slots na heap
                self._store_var(sym)                 # guarda o endereço no slot

    # RETURN de funções (copia variável de retorno para slot do chamador)
    def _emit_function_return(self) -> None:
        """
        Antes de RETURN, escreve o valor de retorno no slot reservado pelo
        chamador e limpa a frame.
        """
        ret_sym = self._symbols.lookup_var(self._current_unit)
        if ret_sym is None:
            return
        n_locals = self._current_n_eff
        # 1. Copia resultado para o slot de retorno do chamador
        self._emit(IRPushL(ret_sym.index))
        self._emit(IRStoreL(-(self._current_arity + 1)))
        # 2. Limpa apenas os locais (POP não pode ir abaixo de fp).
        # O chamador faz POP n_arity depois de RETURN (quando fp já foi restaurado).
        if n_locals > 0:
            self._emit(IRPop(n_locals))

    # --- Visita às unidades de programa ------------------------------------
    def visit_Program(self, node: Program) -> None:
        for unit in node.units:
            self.visit(unit)

    def visit_MainProgram(self, node: MainProgram) -> None:
        self._in_global    = True
        self._current_unit = node.name
        self._current_kind = 'PROGRAM'
        self._unit         = IRUnit(name=node.name, kind='PROGRAM')
        self._program.units.append(self._unit)
        self._symbols.push()

        for decl in node.body.declarations:
            self._process_decl(decl)

        n = self._count_locals()
        self._emit(IRStart())
        if n > 0:
            self._emit(IRPushN(n))

        self._emit_array_allocs()

        for stmt in node.body.statements:
            self.visit(stmt)

        self._emit(IRStop())
        self._symbols.pop()

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        saved_unit        = self._unit
        self._unit        = IRUnit(name=node.name, kind='FUNCTION')
        self._program.units.append(self._unit)

        self._in_global     = False
        self._current_unit  = node.name
        self._current_kind  = 'FUNCTION'
        self._current_arity = len(node.params)
        self._symbols.push()

        for i, pname in enumerate(node.params):
            self._symbols.declare_param(VarSymbol(name=pname, var_type='UNKNOWN'), i)

        ret_type = node.return_type or 'UNKNOWN'
        self._symbols.declare_var(VarSymbol(name=node.name, var_type=ret_type))

        for decl in node.body.declarations:
            self._process_decl(decl)

        n_locals = self._count_locals()
        self._current_n_eff = n_locals

        self._emit(IRLabel(node.name))
        if n_locals > 0:
            self._emit(IRPushN(n_locals))
        self._emit_array_allocs()

        for stmt in node.body.statements:
            self.visit(stmt)

        self._emit_function_return()
        self._emit(IRReturn())

        self._symbols.pop()
        self._unit      = saved_unit
        self._in_global = True

    def visit_SubroutineDef(self, node: SubroutineDef) -> None:
        saved_unit        = self._unit
        self._unit        = IRUnit(name=node.name, kind='SUBROUTINE')
        self._program.units.append(self._unit)

        self._in_global     = False
        self._current_unit  = node.name
        self._current_kind  = 'SUBROUTINE'
        self._current_arity = len(node.params)
        self._symbols.push()

        for i, pname in enumerate(node.params):
            self._symbols.declare_param(VarSymbol(name=pname, var_type='UNKNOWN'), i)

        for decl in node.body.declarations:
            self._process_decl(decl)

        n = self._count_locals()
        self._current_n_eff = n

        self._emit(IRLabel(node.name))
        if n > 0:
            self._emit(IRPushN(n))
        self._emit_array_allocs()

        for stmt in node.body.statements:
            self.visit(stmt)

        # A função limpa apenas os locais (POP não pode ir abaixo de fp).
        # O chamador faz POP n_arity depois de RETURN.
        if n > 0:
            self._emit(IRPop(n))
        self._emit(IRReturn())

        self._symbols.pop()
        self._unit      = saved_unit
        self._in_global = True

    # --- Visita às instruções ----------------------------------------------

    def visit_LabeledStmt(self, node: LabeledStmt) -> None:
        self._emit(IRLabel(f'label{node.label}'))
        self.visit(node.stmt)

    def visit_Assign(self, node: Assign) -> None:
        if isinstance(node.target, Var):
            sym   = self._symbols.lookup_var(node.target.name)
            vtype = self.visit(node.value)
            if sym and sym.var_type == 'REAL' and vtype == 'INTEGER':
                self._emit(IRItoF())
            elif sym and sym.var_type == 'INTEGER' and vtype == 'REAL':
                self._emit(IRFtoI())
            self._symbols.initialize(node.target.name)
            self._store_var(sym)

        elif isinstance(node.target, VarOrFuncCall):
            # Array store: emite addr+idx ANTES do valor para STOREN
            sym = self._symbols.lookup_var(node.target.name)
            self._begin_array_store(sym, node.target.args[0])
            vtype = self.visit(node.value)
            if sym and sym.var_type == 'REAL' and vtype == 'INTEGER':
                self._emit(IRItoF())
            elif sym and sym.var_type == 'INTEGER' and vtype == 'REAL':
                self._emit(IRFtoI())
            self._end_array_store()
            self._symbols.initialize(node.target.name)

    def visit_IfThen(self, node: IfThen) -> None:
        lid      = self._new_label()
        else_lbl = f'ELSElabel{lid}'
        end_lbl  = f'ENDIFlabel{lid}'

        self.visit(node.condition)
        self._emit(IRJZ(else_lbl))

        for stmt in node.then_body:
            self.visit(stmt)

        self._emit(IRJump(end_lbl))
        self._emit(IRLabel(else_lbl))

        for stmt in node.else_body:
            self.visit(stmt)

        self._emit(IRLabel(end_lbl))

    def visit_LogicalIf(self, node: LogicalIf) -> None:
        lid     = self._new_label()
        end_lbl = f'ENDLIFlabel{lid}'

        self.visit(node.condition)
        self._emit(IRJZ(end_lbl))
        self.visit(node.stmt)
        self._emit(IRLabel(end_lbl))

    def visit_DoLoop(self, node: DoLoop) -> None:
        lid     = self._new_label()
        do_lbl = f'DOlabel{lid}'
        end_lbl = f'ENDDOlabel{lid}'   # label Fortran do CONTINUE terminal

        var_sym = self._symbols.lookup_var(node.var)

        # Inicialização: var = start
        self.visit(node.start)
        self._store_var(var_sym)

        # Verificação: var <= stop
        self._emit(IRLabel(do_lbl))
        self._push_var(var_sym)
        self.visit(node.stop)
        self._emit(IRInfEq())          # var <= stop
        self._emit(IRJZ(end_lbl))

        # Corpo
        for stmt in node.body:
            self.visit(stmt)

        # Incremento: var += step (default 1)
        self._push_var(var_sym)
        if node.step is not None:
            self.visit(node.step)
        else:
            self._emit(IRPushI(1))
        self._emit(IRAdd())
        self._store_var(var_sym)

        self._emit(IRJump(do_lbl))
        self._emit(IRLabel(end_lbl))

    def visit_Goto(self, node: Goto) -> None:
        # Usa o mesmo prefixo que visit_LabeledStmt para garantir consistência
        self._emit(IRJump(f'label{node.label}'))

    def visit_Continue(self, node: Continue) -> None:
        pass  # label já emitido por visit_LabeledStmt

    def visit_PrintStmt(self, node: PrintStmt) -> None:
        for i, item in enumerate(node.items):
            if i > 0:
                self._emit(IRPushS(' '), IRWriteS())
            vtype = self.visit(item)
            if vtype == 'REAL':
                self._emit(IRWriteF())
            elif vtype == 'CHARACTER':
                self._emit(IRWriteS())
            else:
                self._emit(IRWriteI())
        self._emit(IRWriteLn())

    def visit_ReadStmt(self, node: ReadStmt) -> None:
        for target in node.targets:
            if isinstance(target, Var):
                sym = self._symbols.lookup_var(target.name)
                self._emit(IRRead())
                if sym and sym.var_type == 'REAL':
                    self._emit(IRAtof())
                else:
                    self._emit(IRAtoi())
                self._symbols.initialize(target.name)
                self._store_var(sym)

            elif isinstance(target, VarOrFuncCall):
                # Array: addr+idx antes de READ para STOREN
                sym = self._symbols.lookup_var(target.name)
                self._begin_array_store(sym, target.args[0])
                self._emit(IRRead())
                if sym and sym.var_type == 'REAL':
                    self._emit(IRAtof())
                else:
                    self._emit(IRAtoi())
                self._end_array_store()
                self._symbols.initialize(target.name)

    def visit_CallStmt(self, node: CallStmt) -> None:
        # Subrotina limpa os locais; o chamador remove os args após RETURN.
        for arg in reversed(node.args):
            self.visit(arg)
        self._emit(IRPushA(node.name), IRCall())
        if node.args:
            self._emit(IRPop(len(node.args)))

    def visit_ReturnStmt(self, node: ReturnStmt) -> None:
        if self._current_kind == 'FUNCTION':
            self._emit_function_return()
        elif self._current_kind == 'SUBROUTINE' and self._current_n_eff > 0:
            self._emit(IRPop(self._current_n_eff))  # só locais; args ficam para o chamador
        self._emit(IRReturn())

    def visit_StopStmt(self, node: StopStmt) -> None:
        self._emit(IRStop())

    # --- Visita às expressões ----------------------------------------------

    def visit_IntLit(self, node: IntLit) -> str:
        self._emit(IRPushI(node.value))
        return 'INTEGER'

    def visit_RealLit(self, node: RealLit) -> str:
        self._emit(IRPushF(node.value))
        return 'REAL'

    def visit_StringLit(self, node: StringLit) -> str:
        self._emit(IRPushS(node.value))
        return 'CHARACTER'

    def visit_BoolLit(self, node: BoolLit) -> str:
        self._emit(IRPushI(1 if node.value else 0))
        return 'LOGICAL'

    def visit_Var(self, node: Var) -> str:
        sym = self._symbols.lookup_var(node.name)
        if sym is None:
            return 'UNKNOWN'
        self._push_var(sym)
        return sym.var_type

    def visit_VarOrFuncCall(self, node: VarOrFuncCall) -> str:
        var_sym  = self._symbols.lookup_var(node.name)
        func_sym = self._symbols.lookup_subprogram(node.name)

        # Acesso a elemento de array (heap dinâmica)
        if var_sym is not None and var_sym.is_array:
            self._push_array_elem(var_sym, node.args[0])
            return var_sym.var_type

        # Chamada a função de utilizador
        if func_sym is not None and func_sym.is_function:
            # PUSHI 0 (slot de retorno) + args + CALL + POP n_arity.
            # Após RETURN, fp foi restaurado; POP n_arity remove os args
            # (abaixo do antigo fp da função), expondo o slot de retorno no topo.
            self._emit(IRPushI(0))           # slot de retorno
            for arg in reversed(node.args):  # ordem inversa (param0 → fp[-1])
                self.visit(arg)
            self._emit(IRPushA(func_sym.name), IRCall())
            if func_sym.arity > 0:
                self._emit(IRPop(func_sym.arity))
            return func_sym.return_type or 'UNKNOWN'

        return 'UNKNOWN'

    def visit_ArithmeticBinOp(self, node: ArithmeticBinOp) -> str:
        if node.op == '**':
            return self._emit_power(node)

        lt = self.visit(node.left)
        rt = self.visit(node.right)

        use_real = (lt == 'REAL' or rt == 'REAL')

        # converte operando INTEGER para REAL se necessário
        # A stack tem [left, right]; ITOF actua no topo (right)
        if use_real:
            if rt == 'INTEGER':
                self._emit(IRItoF())       # converte right (topo)
            elif lt == 'INTEGER':
                # left está abaixo de right; troca, converte, troca de volta
                self._emit(IRSwap(), IRItoF(), IRSwap())

        table = _ARITH_REAL if use_real else _ARITH_INT
        self._emit(table[node.op]())
        return 'REAL' if use_real else 'INTEGER'

    def _emit_power(self, node: ArithmeticBinOp) -> str:
        """
        Emite chamada ao helper POWERFUNClabel(base, exp) para calcular base**exp.
        O helper usa a mesma convenção de chamada que as funções de utilizador.
        """
        self._needs_power = True
        self._emit(IRPushI(0))                              # slot de retorno
        self.visit(node.right)                              # exp → fp[-2]
        self.visit(node.left)                               # base → fp[-1]
        self._emit(IRPushA('POWERFUNClabel'), IRCall())
        self._emit(IRPop(2))                                # remove exp e base (n_arity=2)
        return 'INTEGER'

    def visit_LogicalBinOp(self, node: LogicalBinOp) -> str:
        self.visit(node.left)
        self.visit(node.right)
        self._emit(IRAnd() if node.op == '.AND.' else IROr())
        return 'LOGICAL'

    def visit_LogicalUnaryOp(self, node: LogicalUnaryOp) -> str:
        self.visit(node.operand)
        self._emit(IRNot())
        return 'LOGICAL'

    def visit_RelationalBinOp(self, node: RelationalBinOp) -> str:
        lt = self.visit(node.left)
        rt = self.visit(node.right)

        use_real = (lt == 'REAL' or rt == 'REAL')
        if use_real:
            if rt == 'INTEGER':
                self._emit(IRItoF())
            elif lt == 'INTEGER':
                self._emit(IRSwap(), IRItoF(), IRSwap())

        table   = _REL_REAL if use_real else _REL_INT
        ir_cls  = table[node.op]

        if ir_cls is None:   # .NE. → EQUAL + NOT
            self._emit(IREqual(), IRNot())
        else:
            self._emit(ir_cls())
        return 'LOGICAL'

    def visit_ArithmeticUnaryOp(self, node: ArithmeticUnaryOp) -> str:
        t = self.visit(node.operand)
        if node.op == '-':
            if t == 'REAL':
                self._emit(IRPushF(-1.0), IRFMul())
            else:
                self._emit(IRPushI(-1), IRMul())
        return t

    def visit_FuncCall(self, node: FuncCall) -> str:
        if node.name == 'MOD':
            self.visit(node.args[0])
            self.visit(node.args[1])
            self._emit(IRMod())
            return 'INTEGER'

        if node.name in ('MAX', 'MIN'):
            return self._emit_max_min(node)

        # SQRT: EWVM não tem instrução nativa, emitir erro em runtime
        if node.name == 'SQRT':
            t = self.visit(node.args[0])
            self._switch_to_real(t)
            self._emit(IRPushS('SQRT not supported by EWVM'), IRWriteS(), IRStop())
            return 'REAL'

        return 'UNKNOWN'

    def _emit_max_min(self, node: FuncCall) -> str:
        types    = [self.visit(arg) for arg in node.args]
        use_real = 'REAL' in types
        cmp_cls  = (IRFSup if use_real else IRSup) if node.name == 'MAX' else \
                   (IRFInf if use_real else IRInf)

        for _ in range(len(node.args) - 1):
            lid     = self._new_label()
            take_b  = f'MINMAXlabel{lid}'
            end_lbl = f'MINMAXENDlabel{lid}'

            self._emit(IRCopyK(2))          # duplica top-2: [a, b, a, b]
            self._emit(cmp_cls())           # [a, b, (a>b)]
            self._emit(IRJZ(take_b))

            self._emit(IRPop(1))            # remove b, fica a
            self._emit(IRJump(end_lbl))

            self._emit(IRLabel(take_b))
            self._emit(IRSwap(), IRPop(1))  # remove a, fica b

            self._emit(IRLabel(end_lbl))

        return 'REAL' if use_real else 'INTEGER'
