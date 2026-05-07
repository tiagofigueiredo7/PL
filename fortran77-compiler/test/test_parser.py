import os
import sys

current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
src_dir = os.path.abspath(os.path.join(parent_dir, 'src'))

sys.path.insert(0, parent_dir)
sys.path.insert(0, src_dir)

from src.parser import (
    Parser, Node, 
    Program, MainProgram, FunctionDef, 
    PrintStmt, Assign, Var, IntLit, BoolLit,
    ArithmeticBinOp, LogicalBinOp, RelationalBinOp, ArithmeticUnaryOp, LogicalUnaryOp, 
    IfThen, DoLoop, Goto
)


"""
Funções auxiliares para os testes.
"""

def get_ast(src: str):
    parser = Parser()
    ast = parser.parse(src)
    return ast, parser._errors

def find_node(node: Node, node_type: type) -> bool:
    """Procura recursivamente por um tipo de nó na AST"""
    if isinstance(node, node_type):
        return True
    
    if isinstance(node, list):
        return any(find_node(n, node_type) for n in node)
        
    if hasattr(node, '__dict__'):
        for key, value in vars(node).items():
            if isinstance(value, (Node, list)):
                if find_node(value, node_type):
                    return True
    return False

"""
Exemplos do professor.
"""

CODE_DIR = os.path.join(os.path.dirname(__file__), 'code')

F77_FILES = ['helloworld.f77', 'fatorial.f77', 'isprime.f77', 'listsum.f77', 'conversor.f77']

src_code = []

for file in F77_FILES:
    with open(os.path.join(CODE_DIR, file), 'r') as f:
        src_code.append(f.read())
        
src_hello, src_fatorial, src_isprime, src_listsum, src_conversor = src_code

"""
Testar se os exemplos do professor não têm erros sintáticos.
"""

def test_hello_no_errors():
    ast, errors = get_ast(src_hello)
    assert len(errors) == 0
    assert ast is not None

def test_fatorial_no_errors():
    ast, errors = get_ast(src_fatorial)
    assert len(errors) == 0
    assert ast is not None

def test_isprime_no_errors():
    ast, errors = get_ast(src_isprime)
    assert len(errors) == 0
    assert ast is not None

def test_listsum_no_errors():
    ast, errors = get_ast(src_listsum)
    assert len(errors) == 0
    assert ast is not None

def test_conversor_no_errors():
    ast, errors = get_ast(src_conversor)
    assert len(errors) == 0
    assert ast is not None

"""
Testar o parsing correto da estrutura do programa.
"""

def test_program_structure_hello():
    ast, errors = get_ast(src_hello)
    assert isinstance(ast, Program)
    assert len(ast.units) >= 1
    
    main_prog = ast.units[0]
    assert isinstance(main_prog, MainProgram)
    assert main_prog.name == "HELLO"

def test_function_structure_conversor():
    ast, errors = get_ast(src_conversor)
    assert isinstance(ast, Program)
    
    # conversor.f77 deve ter o MainProgram e uma FunctionDef
    has_function = find_node(ast, FunctionDef)
    assert has_function

"""
Testar o parsing correto de statements (instruções).
"""

def test_print_stmt_in_hello():
    ast, _ = get_ast(src_hello)
    assert find_node(ast, PrintStmt)

def test_assignment_in_fatorial():
    ast, _ = get_ast(src_fatorial)
    assert find_node(ast, Assign)

def test_if_then_else_in_isprime():
    ast, _ = get_ast(src_isprime)
    assert find_node(ast, IfThen)

def test_do_loop_in_fatorial():
    ast, _ = get_ast(src_fatorial)
    assert find_node(ast, DoLoop)

def test_goto_in_isprime():
    ast, _ = get_ast(src_isprime)
    assert find_node(ast, Goto)

"""
Testar o parsing de pequenas expressões isoladas
"""

def test_parse_simple_assignment():
    src = "      PROGRAM TEST\n      X = 1\n      END\n"
    ast, errors = get_ast(src)
    assert len(errors) == 0
    
    main_prog = ast.units[0]
    assign_stmt = main_prog.body.statements[0]
    
    assert isinstance(assign_stmt, Assign)
    assert isinstance(assign_stmt.target, Var)
    assert assign_stmt.target.name == 'X'
    assert isinstance(assign_stmt.value, IntLit)
    assert assign_stmt.value.value == 1

def test_parse_arithmetic_binary_operation():
    src = "      PROGRAM TEST\n      X = A + B\n      END\n"
    ast, errors = get_ast(src)
    
    main_prog = ast.units[0]
    assign_stmt = main_prog.body.statements[0]
    
    assert isinstance(assign_stmt.value, ArithmeticBinOp)
    assert assign_stmt.value.op == '+'
    assert isinstance(assign_stmt.value.left, Var)
    assert assign_stmt.value.left.name == 'A'

def test_parse_logical_binary_operation():
    src = "      PROGRAM TEST\n      X = .TRUE. .AND. .FALSE.\n      END\n"
    ast, errors = get_ast(src)
    assert len(errors) == 0
    assign_stmt = ast.units[0].body.statements[0]
    assert isinstance(assign_stmt.value, LogicalBinOp)
    assert assign_stmt.value.op == '.AND.'
    assert isinstance(assign_stmt.value.left, BoolLit)
    assert assign_stmt.value.left.value == True
    assert isinstance(assign_stmt.value.right, BoolLit)
    assert assign_stmt.value.right.value == False

def test_parse_relational_binary_operation():
    src = "      PROGRAM TEST\n      X = A .LT. B\n      END\n"
    ast, errors = get_ast(src)
    assert len(errors) == 0
    assign_stmt = ast.units[0].body.statements[0]
    assert isinstance(assign_stmt.value, RelationalBinOp)
    assert assign_stmt.value.op == '.LT.'
    assert isinstance(assign_stmt.value.left, Var)
    assert assign_stmt.value.left.name == 'A'

def test_parse_arithmetic_unary_operation():
    src = "      PROGRAM TEST\n      X = -A\n      END\n"
    ast, errors = get_ast(src)
    assert len(errors) == 0
    assign_stmt = ast.units[0].body.statements[0]
    assert isinstance(assign_stmt.value, ArithmeticUnaryOp)
    assert assign_stmt.value.op == '-'
    assert isinstance(assign_stmt.value.operand, Var)
    assert assign_stmt.value.operand.name == 'A'

def test_parse_logical_unary_operation():
    src = "      PROGRAM TEST\n      X = .NOT. .TRUE.\n      END\n"
    ast, errors = get_ast(src)
    assert len(errors) == 0
    assign_stmt = ast.units[0].body.statements[0]
    assert isinstance(assign_stmt.value, LogicalUnaryOp)
    assert assign_stmt.value.op == '.NOT.'
    assert isinstance(assign_stmt.value.operand, BoolLit)
    assert assign_stmt.value.operand.value == True

"""
Testar se erros de sintaxe são devidamente apanhados.
"""

def test_syntax_error_missing_operand():
    src = "      PROGRAM ERRO\n      X = + \n      END\n"
    ast, errors = get_ast(src)
    assert len(errors) > 0

def test_syntax_error_unclosed_paren():
    src = "      PROGRAM ERRO\n      X = (A + B\n      END\n"
    ast, errors = get_ast(src)
    assert len(errors) > 0
