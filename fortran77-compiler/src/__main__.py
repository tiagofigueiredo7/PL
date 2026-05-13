import argparse
import os

from lexer.lexer import Lexer
from lexer.preprocessor import Preprocessor
from parser import Parser, ASTPrinter
from semantic import SemanticAnalyser
from translate import Translator

_DIVIDER      = "=" * 30
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEST_CODE    = os.path.join(_PROJECT_ROOT, 'test', 'code')


def _banner(title: str) -> None:
    print(_DIVIDER)
    print(f"=> {title}")
    print(_DIVIDER)


def _resolve_path(arg: str) -> str:
    if os.path.exists(arg):
        return arg
    candidate = os.path.join(_TEST_CODE, arg)
    if os.path.exists(candidate):
        return candidate
    candidate_ext = os.path.join(_TEST_CODE, arg + '.f77')
    if os.path.exists(candidate_ext):
        return candidate_ext
    return arg


def _read_source(filepath: str) -> str | None:
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Erro: Ficheiro '{filepath}' não encontrado.")
        return None


def _vm_output_path(source_path: str) -> str:
    stem   = os.path.splitext(os.path.basename(source_path))[0]
    vm_dir = os.path.join(_PROJECT_ROOT, 'test', 'vm')
    os.makedirs(vm_dir, exist_ok=True)
    return os.path.join(vm_dir, f'{stem}.ewvm')


def _run_lexer(src: str) -> Lexer | None:
    lexer = Lexer()
    lexer.input(src)
    if lexer.errors:
        print("Erros léxicos:")
        for err in lexer.errors:
            print(err)
        return None
    return lexer


def _run_parser(src: str) -> object | None:
    parser = Parser()
    ast    = parser.parse(src)
    if parser.has_errors or ast is None:
        print("Erros sintácticos:")
        for err in parser.errors:
            print(err)
        return None
    return ast


def _run_semantic(ast) -> bool:
    analyser = SemanticAnalyser()
    errors   = analyser.analyse(ast)
    if analyser.has_errors:
        print("Erros semânticos:")
        for err in errors:
            print(err)
        return False
    return True


def mode_preprocess(filepath: str) -> None:
    _banner("Modo Pré-processamento")
    src = _read_source(filepath)
    if src is None:
        return
    preprocessor = Preprocessor(src)
    preprocessor.process()
    preprocessor.dump()


def mode_lexer(filepath: str) -> None:
    _banner("Modo Lexer")
    src = _read_source(filepath)
    if src is None:
        return
    lexer = Lexer()
    lexer.input(src)
    for token in lexer:
        print(token)
    for err in lexer.errors:
        print(err)


def mode_parser(filepath: str) -> None:
    _banner("Modo Parser")
    src = _read_source(filepath)
    if src is None:
        return
    if _run_lexer(src) is None:
        return
    ast = _run_parser(src)
    if ast is None:
        return
    ASTPrinter().visit(ast)


def mode_semantic(filepath: str) -> None:
    _banner("Modo Semântico")
    src = _read_source(filepath)
    if src is None:
        return
    if _run_lexer(src) is None:
        return
    ast = _run_parser(src)
    if ast is None:
        return
    if _run_semantic(ast):
        print("Análise semântica concluída sem erros.")


def mode_translate(filepath: str) -> None:
    _banner("Modo Tradução")
    src = _read_source(filepath)
    if src is None:
        return
    if _run_lexer(src) is None:
        return
    ast = _run_parser(src)
    if ast is None:
        return
    if not _run_semantic(ast):
        return
    code     = Translator().translate(ast)
    out_path = _vm_output_path(filepath)
    print(code)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"\n=> Código EWVM guardado em: {out_path}")


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="Compilador de Fortran 77")
    arg_parser.add_argument("file",help="Path para o ficheiro Fortran 77",
    )
    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument("-pp", "--preprocess", action="store_true", help="Executa apenas o pré-processamento")
    group.add_argument("-l",  "--lexer",      action="store_true", help="Executa o lexer")
    group.add_argument("-p",  "--parser",     action="store_true", help="Executa o lexer e o parser")
    group.add_argument("-s",  "--semantic",   action="store_true", help="Executa o lexer, parser e a análise semântica")
    group.add_argument("-t",  "--translate",  action="store_true", help="Executa a tradução completa")

    args     = arg_parser.parse_args()
    filepath = _resolve_path(args.file)

    if args.preprocess:
        mode_preprocess(filepath)
    elif args.lexer:
        mode_lexer(filepath)
    elif args.parser:
        mode_parser(filepath)
    elif args.semantic:
        mode_semantic(filepath)
    else:
        mode_translate(filepath)


if __name__ == '__main__':
    main()
