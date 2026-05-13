C     ERROS SEMANTICOS (o ficheiro e sintaticamente valido):
C     1. Linha 13: variavel 'SOMA' usada numa atribuicao sem ser declarada.
C     2. Linha 14: tipos incompativeis: INTEGER (N) recebe LOGICAL (FLAG).
C     3. Linha 16: variavel de controlo 'I' do DO loop modificada dentro.
C     4. Linha 18: GOTO para label 999 que nao existe nesta unidade.
C     5. Linha 20: array 'NUMS' usado sem indice (como variavel escalar).
      PROGRAM SEMERRS
      INTEGER N, I
      LOGICAL FLAG
      INTEGER NUMS(5)
      N = 5
      FLAG = .TRUE.
      SOMA = N + 1
      N = FLAG
      DO 10 I = 1, 5
        I = 2
   10 CONTINUE
      GOTO 999
      NUMS(1) = 42
      N = NUMS
      END
