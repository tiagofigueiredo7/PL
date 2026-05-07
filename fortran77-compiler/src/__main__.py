import argparse

from lexer import Lexer, Preprocessor
from parser import Parser, ASTPrinter
from semantic import SemanticAnalyzer

def main():
    arg_parser = argparse.ArgumentParser(description="Compilador de Fortran 77")
    
    arg_parser.add_argument("file", help="Path para o ficheiro Fortran 77")

    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument("-pp", "--preprocess", action="store_true", help="Executa apenas o pré-processamento")
    group.add_argument("-l", "--lexer", action="store_true", help="Executa o lexer")
    group.add_argument("-p", "--parser", action="store_true", help="Executa o lexer e depois o parser")
    group.add_argument("-s", "--semantic", action="store_true", help="Executa o lexer, parser e a análise semântica")
    group.add_argument("-t", "--translate", action="store_true", help="Executa a tradução completa")

    args = arg_parser.parse_args()

    if not (args.lexer or args.parser or args.semantic): # Por default temos a tradução completa
        args.translate = True
    
    # --- Modo Pré-processamento -------------------------------------
    if args.preprocess:
        print("=" * 30)
        print("=> Modo Pré-processamento...")
        print("=" * 30)
        print()
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                src = f.read()
                
            preprocessor = Preprocessor(src)
            preprocessor.process() #* Faz o pré-processamento do códifo e gera as linhas lógicas *#
            
            preprocessor.dump() #? Imprime as linhas lógicas geradas ?#

        except FileNotFoundError:
            print(f"Erro: O ficheiro '{args.file}' não foi encontrado.")
            
    # --- Modo Lexer ------------------------------------------------
    elif args.lexer:
        print("=" * 25)
        print("=> Modo Lexer...")
        print("=" * 25)
        
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                src = f.read()
                
            lexer = Lexer()
            lexer.input(src) #* Faz o pré-processamento do códifo e corre o tokenize *#
            
            for token in lexer:
                print(token) #? Imprime os tokens que foram analisados ?#
                
            for error in lexer.errors:
                print(error) #! Imprime os erros do lexer, caso existam !#

        except FileNotFoundError:
            print(f"Erro: O ficheiro '{args.file}' não foi encontrado.")
        
    # --- Modo Parser -----------------------------------------------
    elif args.parser:
        print("=" * 25)
        print("=> Modo Parser...")
        print("=" * 25)
        
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                src = f.read()

            parser = Parser()
            ast = parser.parse(src) #* Cria a Abstract Syntax Tree (AST) depois de fazer o parsing *#
            
            if ast:
                printer = ASTPrinter()
                printer.visit(ast) #? Imprime a AST ?#
            else:
                print("Erro: AST não foi gerada devido a erros de parsing.")
                for error in parser.errors:
                    print(error) #! Imprime os erros de parsing, caso existam !#

        except FileNotFoundError:
            print(f"Erro: O ficheiro '{args.file}' não foi encontrado.")
    
    # --- Modo Semantic ---------------------------------------------
    elif args.semantic:
        print("=" * 25)
        print("=> Modo Semantic...")
        print("=" * 25)
        
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                src = f.read()

            parser = Parser()
            ast = parser.parse(src) #* Cria a Abstract Syntax Tree (AST) depois de fazer o parsing *#
            
            if ast:
                semantic_analyzer = SemanticAnalyzer()
                errors = semantic_analyzer.analyse(ast)
                
                if semantic_analyzer.has_errors:
                    print("Erros Semânticos encontrados:")
                    for error in errors:
                        print(error) #! Imprime os erros da análise semântica !#
                else:
                    print("A análise semântica não encontrou erros.")
            else:
                print("Erro: AST não foi gerada devido a erros de parsing.")
                for error in parser.errors:
                    print(error) #! Imprime os erros de parsing, caso existam !#

        except FileNotFoundError:
            print(f"Erro: O ficheiro '{args.file}' não foi encontrado.")
            
    # --- Modo Translate --------------------------------------------   
    elif args.translate:
        print("=" * 25)
        print("=> Modo Translate...")
        print("=" * 25)
        # TODO: Executar toda a pipeline (Lexer, Parser, Semântica e Tradutor)

if __name__ == '__main__':
    main()