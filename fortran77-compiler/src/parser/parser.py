import ply.yacc as yacc

from lexer import Lexer, TOKENS, LITERALS
from .ast import *
from dataclasses import dataclass

@dataclass
class ParserError(Exception):
    """
    Erro gerado durante a análise sintática.
    """
    message: str    # mensagem de erro
    line:    int    # numero da linha

    def __str__(self) -> str:
        return f"[Parser] Linha {self.line}: {self.message}"

class Parser:
    """
    Class da análise sintática (parser).
    """   
    
    tokens   = TOKENS
    literals = LITERALS

    precedence = (
        ('left',     'OP_OR'),
        ('left',     'OP_AND'),
        ('right',    'OP_NOT'),
        ('nonassoc', 'OP_EQ', 'OP_NE', 'OP_LT', 'OP_LE', 'OP_GT', 'OP_GE'),
        ('left',     '+', '-'),
        ('left',     '*', '/'),
        ('right',    'UMINUS', 'UPLUS'),
        ('right',    'POWER'),
    )

    def __init__(self) -> None:
        self._errors: list[ParserError] = []
        self._parser = yacc.yacc(module=self)

    # --- Programa --------------------------------------------------
    def p_program_single(self, p):
        """program : program_unit"""
        p[0] = Program(units=[p[1]], lineno=p[1].lineno)

    def p_program_multi(self, p):
        """program : program program_unit"""
        p[1].units.append(p[2])
        p[0] = p[1]

    # --- Unidades de programa --------------------------------------
    def p_program_unit(self, p):
        '''program_unit : main_program
                        | function_subprogram
                        | subroutine_subprogram'''
        p[0] = p[1]

    # --- Programa principal ----------------------------------------
    def p_main_program(self, p):
        """main_program : PROGRAM IDEN NEWLINE body END NEWLINE"""
        p[0] = MainProgram(name=p[2], body=p[4], lineno=p.lineno(1))

    # --- Subprogramas ----------------------------------------------
    def p_function_with_type(self, p):
        """function_subprogram : type_spec FUNCTION IDEN '(' param_list ')' NEWLINE body END NEWLINE"""
        p[0] = FunctionDef(
            name=p[3], params=p[5],
            return_type=p[1], body=p[8],
            lineno=p.lineno(2),
        )

    def p_function_without_type(self, p):
        """function_subprogram : FUNCTION IDEN '(' param_list ')' NEWLINE body END NEWLINE"""
        p[0] = FunctionDef(
            name=p[2], params=p[4],
            return_type=None, body=p[7],
            lineno=p.lineno(1),
        )

    def p_function_with_type_no_params(self, p):
        """function_subprogram : type_spec FUNCTION IDEN '(' ')' NEWLINE body END NEWLINE"""
        p[0] = FunctionDef(
            name=p[3], params=[],
            return_type=p[1], body=p[7],
            lineno=p.lineno(2),
        )

    def p_function_without_type_no_params(self, p):
        """function_subprogram : FUNCTION IDEN '(' ')' NEWLINE body END NEWLINE"""
        p[0] = FunctionDef(
            name=p[2], params=[],
            return_type=None, body=p[6],
            lineno=p.lineno(1),
        )

    def p_subroutine_with_params(self, p):
        """subroutine_subprogram : SUBROUTINE IDEN '(' param_list ')' NEWLINE body END NEWLINE"""
        p[0] = SubroutineDef(
            name=p[2], params=p[4], body=p[7],
            lineno=p.lineno(1),
        )

    def p_subroutine_no_params(self, p):
        """subroutine_subprogram : SUBROUTINE IDEN '(' ')' NEWLINE body END NEWLINE"""
        p[0] = SubroutineDef(
            name=p[2], params=[], body=p[6],
            lineno=p.lineno(1),
        )

    # param_list: lista de nomes dos parâmetros formais
    def p_param_list_single(self, p):
        """param_list : IDEN"""
        p[0] = [p[1]]

    def p_param_list_multi(self, p):
        """param_list : param_list ',' IDEN"""
        p[0] = p[1] + [p[3]]

    # --- Body: declarações + instruções ---------------------------
    def p_body(self, p):
        """body : decl_section stmt_section"""
        p[0] = Body(
            declarations=p[1],
            statements=p[2],
            lineno=p[1][0].lineno if p[1] else (p[2][0].lineno if p[2] else 0),
        )

    # decl_section: zero ou mais declarações de tipo
    def p_decl_section_empty(self, p):
        """decl_section : """
        p[0] = []

    def p_decl_section_more(self, p):
        """decl_section : decl_section declaration NEWLINE"""
        p[0] = p[1] + [p[2]]

    # stmt_section: zero ou mais linhas de instrução
    def p_stmt_section_empty(self, p):
        """stmt_section : """
        p[0] = []

    def p_stmt_section_more(self, p):
        """stmt_section : stmt_section stmt_line"""
        p[0] = p[1] + [p[2]]

    # --- Linhas de instrução (com ou sem label) --------------------
    def p_stmt_line_plain(self, p):
        """stmt_line : statement NEWLINE"""
        p[0] = p[1]

    def p_stmt_line_labeled(self, p):
        """stmt_line : LABEL statement NEWLINE"""
        p[0] = LabeledStmt(label=p[1], stmt=p[2], lineno=p.lineno(1))

    # --- Declarações de tipo ---------------------------------------
    def p_declaration(self, p):
        """declaration : type_spec var_decl_list"""
        p[0] = TypeDecl(
            type_name=p[1] if isinstance(p[1], str) else p[1][0],
            char_len=p[1][1] if isinstance(p[1], tuple) else None,
            variables=p[2],
            lineno=p[2][0].lineno,
        )

    # type_spec: devolve string ou tuple
    def p_type_spec_basic(self, p):
        '''type_spec : INTEGER
                     | REAL
                     | LOGICAL
                     | CHARACTER'''
        p[0] = p[1]

    def p_type_spec_character_len(self, p):
        """type_spec : CHARACTER '*' INT_LIT"""
        p[0] = ('CHARACTER', p[3])

    # var_decl_list
    def p_var_decl_list_single(self, p):
        """var_decl_list : var_decl"""
        p[0] = [p[1]]

    def p_var_decl_list_multi(self, p):
        """var_decl_list : var_decl_list ',' var_decl"""
        p[0] = p[1] + [p[3]]

    # var_decl: variável simples ou array unidimensional
    def p_var_decl_scalar(self, p):
        """var_decl : IDEN"""
        p[0] = VarDecl(name=p[1], dimension=0, lineno=p.lineno(1))

    def p_var_decl_array(self, p):
        """var_decl : IDEN '(' INT_LIT ')'"""
        p[0] = VarDecl(name=p[1], dimension=p[3], lineno=p.lineno(1))

    # --- Instruções executáveis ------------------------------------
    def p_statement(self, p):
        '''statement : assignment_stmt
                     | if_stmt
                     | do_stmt
                     | goto_stmt
                     | print_stmt
                     | read_stmt
                     | call_stmt
                     | return_stmt
                     | stop_stmt'''
        p[0] = p[1]

    # --- Atribuição ------------------------------------------------
    def p_assignment_var(self, p):
        """assignment_stmt : variable '=' expr"""
        p[0] = Assign(target=p[1], value=p[3], lineno=p.lineno(2))

    # --- IF --------------------------------------------------------
    def p_if_stmt(self, p):
        """if_stmt : if_then_block"""
        p[0] = p[1]

    def p_if_stmt_logical(self, p):
        """if_stmt : logical_if_stmt"""
        p[0] = p[1]

    # IF-THEN sem ELSE
    def p_if_then_no_else(self, p):
        """if_then_block : IF '(' expr ')' THEN NEWLINE stmt_section ENDIF"""
        p[0] = IfThen(
            condition=p[3],
            then_body=p[7],
            else_body=[],
            lineno=p.lineno(1),
        )

    # IF-THEN-ELSE
    def p_if_then_else(self, p):
        """if_then_block : IF '(' expr ')' THEN NEWLINE stmt_section ELSE NEWLINE stmt_section ENDIF"""
        p[0] = IfThen(
            condition=p[3],
            then_body=p[7],
            else_body=p[10],
            lineno=p.lineno(1),
        )

    # IF lógico (sem THEN)
    def p_logical_if(self, p):
        """logical_if_stmt : IF '(' expr ')' statement"""
        p[0] = LogicalIf(condition=p[3], stmt=p[5], lineno=p.lineno(1))

    # --- DO --------------------------------------------------------
    def p_do_loop(self, p):
        """do_stmt : DO INT_LIT IDEN '=' expr ',' expr NEWLINE stmt_section LABEL CONTINUE"""
        p[0] = DoLoop(
            label=p[2], var=p[3],
            start=p[5], stop=p[7], step=None,
            body=p[9],
            lineno=p.lineno(1),
        )

    def p_do_loop_step(self, p):
        """do_stmt : DO INT_LIT IDEN '=' expr ',' expr ',' expr NEWLINE stmt_section LABEL CONTINUE"""
        p[0] = DoLoop(
            label=p[2], var=p[3],
            start=p[5], stop=p[7], step=p[9],
            body=p[11],
            lineno=p.lineno(1),
        )

    # --- GOTO ------------------------------------------------------
    def p_goto(self, p):
        """goto_stmt : GOTO INT_LIT"""
        p[0] = Goto(label=p[2], lineno=p.lineno(1))

    # --- PRINT -----------------------------------------------------
    def p_print_stmt(self, p):
        """print_stmt : PRINT '*' ',' io_list"""
        p[0] = PrintStmt(items=p[4], lineno=p.lineno(1))

    # --- READ ------------------------------------------------------
    def p_read_stmt(self, p):
        """read_stmt : READ '*' ',' io_list"""
        p[0] = ReadStmt(targets=p[4], lineno=p.lineno(1))

    # io_list: lista de itens de I/O
    def p_io_list_single(self, p):
        """io_list : io_item"""
        p[0] = [p[1]]

    def p_io_list_multi(self, p):
        """io_list : io_list ',' io_item"""
        p[0] = p[1] + [p[3]]

    def p_io_item(self, p):
        """io_item : expr"""
        p[0] = p[1]

    # --- CALL / RETURN / STOP --------------------------------------
    def p_call_with_args(self, p):
        """call_stmt : CALL IDEN '(' expr_list ')'"""
        p[0] = CallStmt(name=p[2], args=p[4], lineno=p.lineno(1))

    def p_call_no_args(self, p):
        """call_stmt : CALL IDEN '(' ')'"""
        p[0] = CallStmt(name=p[2], args=[], lineno=p.lineno(1))

    def p_return_stmt(self, p):
        """return_stmt : RETURN"""
        p[0] = ReturnStmt(lineno=p.lineno(1))

    def p_stop_stmt(self, p):
        """stop_stmt : STOP"""
        p[0] = StopStmt(lineno=p.lineno(1))

    # --- Expressões ------------------------------------------------

    def p_expr_logical_binop(self, p):
        '''expr : expr OP_AND expr
                | expr OP_OR expr'''
        p[0] = LogicalBinOp(left=p[1], op=p[2], right=p[3], lineno=p.lineno(2))

    def p_expr_logical_unary(self, p):
        '''expr : OP_NOT expr'''
        p[0] = LogicalUnaryOp(op=p[1], operand=p[2], lineno=p.lineno(1))

    def p_expr_relational_binop(self, p):
        '''expr : expr OP_EQ expr
                | expr OP_NE expr
                | expr OP_LT expr
                | expr OP_LE expr
                | expr OP_GT expr
                | expr OP_GE expr'''
        p[0] = RelationalBinOp(left=p[1], op=p[2], right=p[3], lineno=p.lineno(2))

    def p_expr_arithmetic_binop(self, p):
        '''expr : expr '+' expr
                | expr '-' expr
                | expr '*' expr
                | expr '/' expr
                | expr POWER expr'''
        p[0] = ArithmeticBinOp(left=p[1], op=p[2], right=p[3], lineno=p.lineno(2))

    def p_expr_arithmetic_unary(self, p):
        '''expr : '-' expr %prec UMINUS
                | '+' expr %prec UPLUS'''
        p[0] = ArithmeticUnaryOp(op=p[1], operand=p[2], lineno=p.lineno(1))

    # Agrupamento
    def p_expr_paren(self, p):
        """expr : '(' expr ')'"""
        p[0] = p[2]

    # Literais
    def p_expr_int_lit(self, p):
        """expr : INT_LIT"""
        p[0] = IntLit(value=p[1], lineno=p.lineno(1))

    def p_expr_real_lit(self, p):
        """expr : REAL_LIT"""
        p[0] = RealLit(value=p[1], lineno=p.lineno(1))

    def p_expr_string_lit(self, p):
        """expr : STRING_LIT"""
        p[0] = StringLit(value=p[1], lineno=p.lineno(1))

    def p_expr_bool_lit(self, p):
        '''expr : TRUE
                | FALSE'''
        p[0] = BoolLit(value=p[1], lineno=p.lineno(1))

    # Variável e chamada de função (na posição de expressão)
    def p_expr_variable_or_func(self, p):
        '''expr : variable
                | func_call'''
        p[0] = p[1]
        
    # --- Variáveis -------------------------------------------------
    def p_variable_simple(self, p):
        """variable : IDEN"""
        p[0] = Var(name=p[1], lineno=p.lineno(1))

    def p_variable_array(self, p):
        """variable : IDEN '(' expr_list ')'"""
        p[0] = VarOrFuncCall(name=p[1], args=p[3], lineno=p.lineno(1))

    def p_variable_func_no_params(self, p):
        """variable : IDEN '(' ')'"""
        p[0] = VarOrFuncCall(name=p[1], args=[], lineno=p.lineno(1))

    def p_expr_list_single(self, p):
        """expr_list : expr"""
        p[0] = [p[1]]

    def p_expr_list_multi(self, p):
        """expr_list : expr_list ',' expr"""
        p[0] = p[1] + [p[3]]

    # --- Chamadas de função ----------------------------------------
    def p_func_call_mod(self, p):
        """func_call : MOD '(' expr ',' expr ')'"""
        p[0] = FuncCall(name='MOD', args=[p[3], p[5]], lineno=p.lineno(1))

    def p_func_call_sqrt(self, p):
        """func_call : SQRT '(' expr ')'"""
        p[0] = FuncCall(name='SQRT', args=[p[3]], lineno=p.lineno(1))

    def p_func_call_max(self, p):
        """func_call : MAX '(' expr_list ')'"""
        p[0] = FuncCall(name='MAX', args=p[3], lineno=p.lineno(1))

    def p_func_call_min(self, p):
        """func_call : MIN '(' expr_list ')'"""
        p[0] = FuncCall(name='MIN', args=p[3], lineno=p.lineno(1))

    # --- Erros -----------------------------------------------------
    def p_error(self, p):
        if p is None:
            self._errors.append(ParserError(
                message="Fim de ficheiro inesperado",
                line=0,
            ))
        else:
            self._errors.append(ParserError(
                message=f"Token inesperado '{p.value}' (tipo: {p.type})",
                line=p.lineno,
            ))
            # Descarta tokens até ao final da linha para tentar continuar a análise
            while True:
                tok = self._parser.token()
                if tok is None or tok.type == 'NEWLINE':
                    break
            self._parser.errok()

    @property
    def errors(self) -> list[ParserError]:
        return list(self._errors)

    @property
    def has_errors(self) -> bool:
        return len(self._errors) > 0

    def parse(self, source: str) -> Program | None:
        self._errors = []
        lexer  = Lexer()
        result = self._parser.parse(
            input=source,
            lexer=lexer,
        )
        
        for err in lexer.errors:
            self._errors.append(ParserError(
                message=f"[Léxico] {err.message}",
                line=err.line,
            ))
        return result

# --- Visitor -------------------------------------------------------
class ASTVisitor:
    """
    Class para percorrer a AST criada pelo parser.
    """

    def visit(self, node: Node):
        return node.accept(self)

    def generic_visit(self, node: Node):
        """
        Visita por defeito: percorre todos os filhos.
        """
        for child in self._children(node):
            if isinstance(child, Node):
                self.visit(child)
            elif isinstance(child, list):
                for item in child:
                    if isinstance(item, Node):
                        self.visit(item)

    def _children(self, node: Node):
        """
        Devolve os valores dos campos do dataclass.
        """
        from dataclasses import fields
        return [getattr(node, f.name) for f in fields(node)]

# --- Pretty-printer da AST -----------------------------------------
class ASTPrinter(ASTVisitor):
    def __init__(self):
        self._indent = 0

    def _pr(self, text: str):
        print("  " * self._indent + text)

    def generic_visit(self, node: Node):
        self._pr(f"{type(node).__name__}  (linha {node.lineno})")
        self._indent += 1
        super().generic_visit(node)
        self._indent -= 1

    # Nós folha
    def visit_Var(self, node):
        self._pr(f"Var({node.name})")

    def visit_IntLit(self, node):
        self._pr(f"IntLit({node.value})")

    def visit_RealLit(self, node):
        self._pr(f"RealLit({node.value})")

    def visit_StringLit(self, node):
        self._pr(f"StringLit({node.value!r})")

    def visit_BoolLit(self, node):
        self._pr(f"BoolLit({node.value})")

    def visit_ArithmeticBinOp(self, node):
        self._pr(f"ArithmeticBinOp({node.op})")
        self._indent += 1
        self.visit(node.left)
        self.visit(node.right)
        self._indent -= 1

    def visit_LogicalBinOp(self, node):
        self._pr(f"LogicalBinOp({node.op})")
        self._indent += 1
        self.visit(node.left)
        self.visit(node.right)
        self._indent -= 1

    def visit_RelationalBinOp(self, node):
        self._pr(f"RelationalBinOp({node.op})")
        self._indent += 1
        self.visit(node.left)
        self.visit(node.right)
        self._indent -= 1

    def visit_ArithmeticUnaryOp(self, node):
        self._pr(f"ArithmeticUnaryOp({node.op})")
        self._indent += 1
        self.visit(node.operand)
        self._indent -= 1

    def visit_LogicalUnaryOp(self, node):
        self._pr(f"LogicalUnaryOp({node.op})")
        self._indent += 1
        self.visit(node.operand)
        self._indent -= 1

    def visit_FuncCall(self, node):
        self._pr(f"FuncCall({node.name})")
        self._indent += 1
        for arg in node.args:
            self.visit(arg)
        self._indent -= 1

    def visit_VarOrFuncCall(self, node):
        self._pr(f"VarOrFuncCall({node.name})")
        self._indent += 1
        for arg in node.args:
            self.visit(arg)
        self._indent -= 1