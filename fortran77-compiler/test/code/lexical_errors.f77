C     ERROS LEXICOS:
C     1. Caracter invalido '@' em 'N = @10'
C        O lexer salta '@' e tokeniza o resto (N = 10 fica valido).
C     2. Caracter invalido '#' em 'M = N # 2'
C        O lexer salta '#'; os tokens restantes (N 2) tornam a expressao
C        invalida, gerando tambem um erro de parsing como efeito secundario.
C     3. Caracter invalido '~' em 'PRINT *, ~M'
C        O lexer salta '~'; o PRINT fica sintaticamente correto.
      PROGRAM LEXERRS
      INTEGER N, M
      N = @10
      M = N # 2
      PRINT *, ~M
      END
