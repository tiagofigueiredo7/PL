C     ERROS DE PARSING:
C     1. Declaracao 'INTEGER M' colocada apos instrucoes executaveis.
C        A gramatica exige body -> decl_section stmt_section; declaracoes
C        devem preceder todas as instrucoes. O token INTEGER e inesperado
C        no contexto de stmt_section.
C     2. Bloco IF-THEN sem ENDIF correspondente.
C        O parser encontra o END do programa antes de fechar o bloco IF,
C        gerando um erro de token inesperado.
      PROGRAM PARSERRS
      INTEGER N
      N = 5
      PRINT *, N
      INTEGER M
      M = N + 1
      IF (M .GT. 3) THEN
        PRINT *, 'M e grande'
      END
