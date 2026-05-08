import os
import sys

current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
src_dir = os.path.abspath(os.path.join(parent_dir, 'src'))

sys.path.insert(0, parent_dir)
sys.path.insert(0, src_dir)

from src.parser import Parser
from src.semantic import SemanticAnalyser, SemanticError

def get_semantic_errors(src: str) -> list[SemanticError]:
    parser = Parser()
    ast = parser.parse(src)
    
    if ast is None:
        raise ValueError("AST não foi gerada devido a erros de parsing.")
    
    semantic_analyzer = SemanticAnalyser()
    errors = semantic_analyzer.analyse(ast)
    return errors

"""
Exemplos do professor.
"""
# ../test/code/****

F77_FILES = ['helloworld.f77', 'fatorial.f77', 'isprime.f77', 'listsum.f77', 'conversor.f77']

src_code = []

for file in F77_FILES:
    with open(os.path.join("./code", file), 'r') as f:
        src_code.append(f.read())
        
src_hello, src_fatorial, src_isprime, src_listsum, src_conversor = src_code

def test_hello_no_semantic_errors():
    errors = get_semantic_errors(src_hello)
    assert len(errors) == 0
    
def test_fatorial_no_semantic_errors():
    errors = get_semantic_errors(src_fatorial)
    assert len(errors) == 0

def test_isprime_no_semantic_errors():
    errors = get_semantic_errors(src_isprime)
    assert len(errors) == 0

def test_listsum_no_semantic_errors():
    errors = get_semantic_errors(src_listsum)
    assert len(errors) == 0

def test_conversor_no_semantic_errors():
    errors = get_semantic_errors(src_conversor)
    assert len(errors) == 0