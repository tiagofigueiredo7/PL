from dataclasses import dataclass

@dataclass
class Node:
    """
    Classe pai para todos os nós da AST.
    """
    lineno: int # numero da linha

    def accept(self, visitor):
        """
        Devolve que método o visitor deve usar para visitar o nó.
        Caso o nó tenha um método específico usa "method",
        caso contrário usa "generic_visit".
        """
        method = 'visit_' + type(self).__name__
        visit  = getattr(visitor, method, visitor.generic_visit)
        return visit(self) # Executa a função com o próprio nó como argumento

# --- Body -------------------------------------------------------------------
@dataclass
class Body(Node):
    """
    Sequência de declarações seguida de sequência de instruções.
    """
    declarations: list[Node]   # TypeDecl
    statements:   list[Node]   # instruções executáveis (podem ter label)
    
@dataclass
class VarDecl(Node):
    """
    Um único item na lista de declaração.
    Ex:  N        ->  VarDecl('N', 0)
         NUMS(5)  -> VarDecl('NUMS', 5)
    """
    name:       str
    dimension:  int    # 0 se escalar, >= 1 se array

# ---- Nós de estrutura do programa ------------------------------------------
@dataclass
class Program(Node):
    """
    Estrutura geral do código. Pode conter várias unidades
    (mains, funções, subrotinas).
    Ex:  PROGRAM MAIN ... END
         INTEGER FUNCTION F(...) ... END
    """
    units: list[Node]  # lista de MainProgram | FunctionDef | SubroutineDef

@dataclass
class MainProgram(Node):
    """
    PROGRAM <name> NEWLINE
      <body>
    END NEWLINE
    """
    name:  str
    body:  Body

@dataclass
class FunctionDef(Node):
    """
    [<type_spec>] FUNCTION <name>(<params>) NEWLINE
      <body>
    END NEWLINE
    """
    name:      str
    params:    list[str]           # nomes dos parametros
    return_type: str | None        # 'INTEGER', 'REAL', etc. ou None (implícito)
    body:      Body

@dataclass
class SubroutineDef(Node):
    """
    SUBROUTINE <name>([<params>]) NEWLINE
      <body>
    END NEWLINE
    """
    name:   str
    params: list[str]          # nomes dos parametros
    body:   Body

# --- Declarações de tipos ------------------------------------------------
@dataclass
class TypeDecl(Node):
    """
    INTEGER N, I, FAT
    INTEGER NUMS(5)
    CHARACTER*10 NAME
    """
    type_name: str             # 'INTEGER' | 'REAL' | 'LOGICAL' | 'CHARACTER'
    char_len:  int | None      # só para CHARACTER*N; None para outros tipos
    variables: list[VarDecl]

# --- Linhas com labels ------------------------------------------------------
@dataclass
class LabeledStmt(Node):
    """
    Ex:  10 CONTINUE  →  LabeledStmt(label=10, stmt=Continue())
         20 IF (...)  →  LabeledStmt(label=20, stmt=IfThen(...))
    """
    label: int
    stmt:  Node

# --- Instruções executáveis -------------------------------------------------
@dataclass
class Assign(Node):
    """
    <variable> = <expr>
    Cobre variáveis simples e elementos de array.
    Ex:  FAT = FAT * I
         NUMS(I) = 0
    """
    target: Node    # Var | VarOrFuncCall
    value:  Node    # qualquer expressão

@dataclass
class IfThen(Node):
    """
    IF (<cond>) THEN
      <then_body>
    [ELSE
      <else_body>]
    ENDIF
    """
    condition: Node
    then_body: list[Node]
    else_body: list[Node]   # lista vazia se não houver ELSE


@dataclass
class LogicalIf(Node):
    """
    IF (<expr>) <stmt>
    """
    condition: Node
    stmt:      Node


@dataclass
class DoLoop(Node):
    """
    DO <label> <var> = <start>, <stop> [, <step>]
      <body>
    <label> CONTINUE
    """
    label:    int
    var:      str     # nome da variável de controlo
    start:    Node
    stop:     Node
    step:     Node | None   # None -> step implícito de 1
    body:     list[Node]


@dataclass
class Goto(Node):
    """
    GOTO <label>
    """
    label: int


@dataclass
class Continue(Node):
    """
    CONTINUE  (marcador de fim de DO loop)
    """
    pass


@dataclass
class PrintStmt(Node):
    """
    PRINT *, <io_list>
    """
    items: list[Node] # lista de expressões a imprimir


@dataclass
class ReadStmt(Node):
    """
    READ *, <io_list>
    """
    targets: list[Node] # lista de variáveis ou elementos de array a ler


@dataclass
class CallStmt(Node):
    """
    CALL <name>([<args>])
    """
    name: str
    args: list[Node]


@dataclass
class ReturnStmt(Node):
    """
    RETURN
    """
    pass


@dataclass
class StopStmt(Node):
    """
    STOP
    """
    pass

# --- Expressões ---------------------------------------------------------------
@dataclass
class ArithmeticBinOp(Node):
    left:  Node
    op:    str
    right: Node


@dataclass
class LogicalBinOp(Node):
    left:  Node
    op:    str
    right: Node


@dataclass
class RelationalBinOp(Node):
    left:  Node
    op:    str
    right: Node


@dataclass
class ArithmeticUnaryOp(Node):
    op:      str
    operand: Node


@dataclass
class LogicalUnaryOp(Node):
    op:      str
    operand: Node


@dataclass
class FuncCall(Node):
    """
    Chamada de função: <name>(<args>)
    Inclui funções intrínsecas (MOD, SQRT, MAX, MIN).
    """
    name: str
    args: list[Node]

# --- Variáveis e literais ---------------------------------------------------
@dataclass
class Var(Node):
    """
    Referência a uma variável simples. Ex: N, FAT, ISPRIM
    """
    name: str


@dataclass
class VarOrFuncCall(Node):
    """
    Acesso a elemento de array OU chamada a função de utilizador.
        Ex:  NUMS(I)  -> VarOrFuncCall(name='NUMS', args=[Var('I')])
            F(X, Y)   -> VarOrFuncCall(name='F', args=[Var('X'), Var('Y')])
    """
    name: str
    args: list[Node]


@dataclass
class IntLit(Node):
    """
    Literal inteiro. Ex: 42, 0, 1
    """
    value: int


@dataclass
class RealLit(Node):
    """
    Literal real. Ex: 3.14, 1.5E-3
    """
    value: float


@dataclass
class StringLit(Node):
    """
    Literal de string. Ex: 'Ola, Mundo!'
    """
    value: str


@dataclass
class BoolLit(Node):
    """
    Literal lógico. Ex: .TRUE., .FALSE.
    """
    value: bool