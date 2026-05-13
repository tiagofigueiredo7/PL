import os
import sys

current_dir = os.path.dirname(__file__)
parent_dir  = os.path.abspath(os.path.join(current_dir, '..'))
src_dir     = os.path.abspath(os.path.join(parent_dir, 'src'))

sys.path.insert(0, parent_dir)
sys.path.insert(0, src_dir)

from src.parser import Parser

for _src_key in ['src.parser', 'src.parser.parser', 'src.parser.ast']:
    _bare_key = _src_key[4:]
    sys.modules.setdefault(_bare_key, sys.modules[_src_key])

from src.semantic import SemanticAnalyser, SemanticError

"""
Funções auxiliares para os testes.
"""

CODE_DIR = os.path.join(os.path.dirname(__file__), 'code')
F77_FILES = ['helloworld.f77', 'fatorial.f77', 'isprime.f77', 'listsum.f77', 'conversor.f77']

src_code = []
for file in F77_FILES:
    with open(os.path.join(CODE_DIR, file), 'r') as f:
        src_code.append(f.read())

src_hello, src_fatorial, src_isprime, src_listsum, src_conversor = src_code


def analyse(src: str) -> list[SemanticError]:
    """Parse + análise semântica com instâncias frescas; devolve lista de erros."""
    parser = Parser()
    ast = parser.parse(src)
    assert ast is not None, f"Parse inesperadamente falhou: {parser.errors}"
    sa = SemanticAnalyser()
    return sa.analyse(ast)


def has_error(errors: list[SemanticError], keyword: str) -> bool:
    return any(keyword.lower() in str(e).lower() for e in errors)


"""
Exemplos do professor.
"""

def test_hello_no_semantic_errors():
    assert analyse(src_hello) == []

def test_fatorial_no_semantic_errors():
    assert analyse(src_fatorial) == []

def test_isprime_no_semantic_errors():
    assert analyse(src_isprime) == []

def test_listsum_no_semantic_errors():
    assert analyse(src_listsum) == []

def test_conversor_no_semantic_errors():
    assert analyse(src_conversor) == []

"""
Variáveis declaradas / não declaradas.
"""

def test_undeclared_variable_in_assignment():
    src = "      PROGRAM TEST\n      N = 5\n      END\n"
    errors = analyse(src)
    assert len(errors) > 0
    assert has_error(errors, "N")

def test_undeclared_variable_in_expression():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = N + GHOST\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "GHOST")

def test_declared_variable_no_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = 5\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_duplicate_variable_declaration():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      INTEGER N\n"
        "      N = 1\n"
        "      END\n"
    )
    errors = analyse(src)
    assert len(errors) > 0
    assert has_error(errors, "declarada mais do que uma vez")


"""
Tipo da condição dos IFs.
"""

def test_if_then_condition_must_be_logical():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = 5\n"
        "      IF (N) THEN\n"
        "        N = 1\n"
        "      ENDIF\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "LOGICAL")

def test_if_then_condition_logical_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      LOGICAL FLAG\n"
        "      N = 5\n"
        "      FLAG = .TRUE.\n"
        "      IF (FLAG) THEN\n"
        "        N = 1\n"
        "      ENDIF\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_if_then_condition_relational_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = 5\n"
        "      IF (N .GT. 3) THEN\n"
        "        N = 1\n"
        "      ENDIF\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_logical_if_condition_integer_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = 5\n"
        "      IF (N) N = 1\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "LOGICAL")


"""
Compatibilidade de tipos nas atribuições.
"""

def test_assign_integer_real_implicit_conversion_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      REAL X\n"
        "      X = 1.5\n"
        "      N = X\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_assign_char_to_integer_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = 'HELLO'\n"
        "      END\n"
    )
    errors = analyse(src)
    assert len(errors) > 0
    assert has_error(errors, "incompat")

def test_assign_logical_to_integer_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = .TRUE.\n"
        "      END\n"
    )
    errors = analyse(src)
    assert len(errors) > 0

def test_assign_integer_to_logical_error():
    src = (
        "      PROGRAM TEST\n"
        "      LOGICAL FLAG\n"
        "      FLAG = 1\n"
        "      END\n"
    )
    errors = analyse(src)
    assert len(errors) > 0


"""
Operações aritméticas e lógicas.
"""

def test_arithmetic_on_logical_operand_error():
    src = (
        "      PROGRAM TEST\n"
        "      LOGICAL FLAG\n"
        "      INTEGER N\n"
        "      FLAG = .TRUE.\n"
        "      N = FLAG + 1\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "num")

def test_unary_minus_numeric_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = -5\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_unary_not_logical_ok():
    src = (
        "      PROGRAM TEST\n"
        "      LOGICAL FLAG\n"
        "      FLAG = .NOT. .TRUE.\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_unary_not_on_integer_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      LOGICAL FLAG\n"
        "      N = 5\n"
        "      FLAG = .NOT. N\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "LOGICAL")

def test_logical_and_requires_logical_operands():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      LOGICAL R\n"
        "      N = 1\n"
        "      R = N .AND. .TRUE.\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "LOGICAL")


"""
Operações relacionais.
"""

def test_relational_int_int_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N, M\n"
        "      LOGICAL R\n"
        "      N = 1\n"
        "      M = 2\n"
        "      R = N .LT. M\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_relational_char_char_ok():
    src = (
        "      PROGRAM TEST\n"
        "      CHARACTER*5 A, B\n"
        "      LOGICAL R\n"
        "      A = 'AB'\n"
        "      B = 'CD'\n"
        "      R = A .EQ. B\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_relational_mixed_numeric_char_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      LOGICAL R\n"
        "      N = 1\n"
        "      R = N .EQ. 'A'\n"
        "      END\n"
    )
    errors = analyse(src)
    assert len(errors) > 0


"""
DO loops.
"""

def test_do_loop_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER I, S\n"
        "      S = 0\n"
        "      DO 10 I = 1, 5\n"
        "        S = S + I\n"
        "   10 CONTINUE\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_do_loop_with_step_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER I, S\n"
        "      S = 0\n"
        "      DO 10 I = 1, 10, 2\n"
        "        S = S + I\n"
        "   10 CONTINUE\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_do_loop_undeclared_control_var():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER S\n"
        "      S = 0\n"
        "      DO 10 I = 1, 5\n"
        "        S = S + 1\n"
        "   10 CONTINUE\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "I") or has_error(errors, "declarada")

def test_do_loop_logical_control_var_error():
    src = (
        "      PROGRAM TEST\n"
        "      LOGICAL FLAG\n"
        "      FLAG = .TRUE.\n"
        "      DO 10 FLAG = 1, 5\n"
        "   10 CONTINUE\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "INTEGER ou REAL")

def test_do_loop_modify_control_var_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER I\n"
        "      DO 10 I = 1, 5\n"
        "        I = 2\n"
        "   10 CONTINUE\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "controlo")

def test_do_loop_nested_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER I, J, S\n"
        "      S = 0\n"
        "      DO 20 I = 1, 3\n"
        "        DO 10 J = 1, 3\n"
        "          S = S + I + J\n"
        "   10   CONTINUE\n"
        "   20 CONTINUE\n"
        "      END\n"
    )
    assert analyse(src) == []


"""
Labels e GOTO.
"""

def test_goto_undefined_label_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N\n"
        "      N = 1\n"
        "      GOTO 999\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "999")

def test_goto_defined_do_label_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER I\n"
        "      DO 10 I = 1, 3\n"
        "        GOTO 10\n"
        "   10 CONTINUE\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_duplicate_label_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER I, J\n"
        "      DO 10 I = 1, 3\n"
        "   10 CONTINUE\n"
        "      DO 10 J = 1, 3\n"
        "   10 CONTINUE\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "definido mais do que uma vez")

def test_standalone_continue_as_goto_target_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER I\n"
        "      I = 5\n"
        "      IF (I .GT. 3) GOTO 99\n"
        "      PRINT *, 'Never'\n"
        "   99 CONTINUE\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_label_only_valid_within_unit():
    """Um label definido numa função não é visível no programa principal."""
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X, F\n"
        "      GOTO 10\n"
        "      END\n"
        "      INTEGER FUNCTION F(N)\n"
        "      INTEGER N\n"
        "   10 F = N\n"
        "      RETURN\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "10")


"""
Arrays.
"""

def test_array_read_write_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER NUMS(5), I\n"
        "      I = 1\n"
        "      NUMS(I) = 0\n"
        "      I = NUMS(1)\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_array_used_as_scalar_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER NUMS(5), N\n"
        "      N = NUMS\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "array") or has_error(errors, "ndice")

def test_scalar_indexed_as_array_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N, M\n"
        "      N = 1\n"
        "      M = N(1)\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "escalar") or has_error(errors, "indexada")

def test_array_non_integer_index_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER NUMS(5)\n"
        "      REAL X\n"
        "      X = 1.5\n"
        "      NUMS(X) = 0\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "INTEGER") or has_error(errors, "ndice")


"""
Funções intrínsecas (MOD, SQRT, MAX, MIN).
"""

def test_mod_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N, M, R\n"
        "      N = 10\n"
        "      M = 3\n"
        "      R = MOD(N, M)\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_mod_non_numeric_argument_error():
    """A arity do MOD é verificada pelo parser (a gramática exige 2 args).
    Este teste verifica o erro semântico quando um argumento não é numérico."""
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER N, R\n"
        "      LOGICAL FLAG\n"
        "      N = 10\n"
        "      FLAG = .TRUE.\n"
        "      R = MOD(N, FLAG)\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "MOD") or has_error(errors, "num")

def test_sqrt_ok():
    src = (
        "      PROGRAM TEST\n"
        "      REAL X, Y\n"
        "      X = 4.0\n"
        "      Y = SQRT(X)\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_max_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER A, B, C\n"
        "      A = 1\n"
        "      B = 2\n"
        "      C = MAX(A, B)\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_max_too_few_args_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER A, C\n"
        "      A = 1\n"
        "      C = MAX(A)\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "MAX") or has_error(errors, "argumento")

def test_min_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER A, B, C\n"
        "      A = 3\n"
        "      B = 7\n"
        "      C = MIN(A, B)\n"
        "      END\n"
    )
    assert analyse(src) == []


"""
Funções de utilizador.
"""

def test_function_return_set_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X, DBL\n"
        "      X = 5\n"
        "      X = DBL(X)\n"
        "      END\n"
        "      INTEGER FUNCTION DBL(N)\n"
        "      INTEGER N\n"
        "      DBL = N * 2\n"
        "      RETURN\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_function_return_never_set_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X, NOOP\n"
        "      X = NOOP(1)\n"
        "      END\n"
        "      INTEGER FUNCTION NOOP(N)\n"
        "      INTEGER N\n"
        "      RETURN\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "retorno") or has_error(errors, "inicializada")

def test_function_arity_mismatch_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X, DBL\n"
        "      X = DBL(1, 2)\n"
        "      END\n"
        "      INTEGER FUNCTION DBL(N)\n"
        "      INTEGER N\n"
        "      DBL = N * 2\n"
        "      RETURN\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "DBL") or has_error(errors, "argumento")

def test_duplicate_subprogram_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X, F\n"
        "      X = F(1)\n"
        "      END\n"
        "      INTEGER FUNCTION F(N)\n"
        "      INTEGER N\n"
        "      F = N\n"
        "      RETURN\n"
        "      END\n"
        "      INTEGER FUNCTION F(N)\n"
        "      INTEGER N\n"
        "      F = N * 2\n"
        "      RETURN\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "F") or has_error(errors, "definido mais do que uma vez")


"""
Subrotinas.
"""

def test_subroutine_call_ok():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X\n"
        "      X = 1\n"
        "      CALL ZERO(X)\n"
        "      END\n"
        "      SUBROUTINE ZERO(N)\n"
        "      INTEGER N\n"
        "      N = 0\n"
        "      RETURN\n"
        "      END\n"
    )
    assert analyse(src) == []

def test_call_undefined_subroutine_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X\n"
        "      X = 1\n"
        "      CALL GHOST(X)\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "GHOST") or has_error(errors, "definida")

def test_call_function_as_subroutine_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X, DBL\n"
        "      X = 1\n"
        "      CALL DBL(X)\n"
        "      END\n"
        "      INTEGER FUNCTION DBL(N)\n"
        "      INTEGER N\n"
        "      DBL = N * 2\n"
        "      RETURN\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "FUNCTION") or has_error(errors, "CALL")

def test_subroutine_arity_mismatch_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X, Y\n"
        "      X = 1\n"
        "      Y = 2\n"
        "      CALL MYSUB(X, Y)\n"
        "      END\n"
        "      SUBROUTINE MYSUB(A)\n"
        "      INTEGER A\n"
        "      A = 0\n"
        "      RETURN\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "MYSUB") or has_error(errors, "argumento")

def test_use_subroutine_as_expression_error():
    src = (
        "      PROGRAM TEST\n"
        "      INTEGER X\n"
        "      X = MYSUB(1)\n"
        "      END\n"
        "      SUBROUTINE MYSUB(A)\n"
        "      INTEGER A\n"
        "      RETURN\n"
        "      END\n"
    )
    errors = analyse(src)
    assert has_error(errors, "SUBROUTINE") or has_error(errors, "express")
