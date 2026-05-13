      PROGRAM SUBROTINA
      INTEGER N
      PRINT *, 'Escreva um valor inteiro: '
      READ *, N
      CALL PRINTMSG(N)
      CALL DOBRA(N)
      PRINT *, 'N original apos chamadas: ', N
      END

      SUBROUTINE PRINTMSG(X)
      INTEGER X
      PRINT *, 'Valor recebido: ', X
      RETURN
      END

      SUBROUTINE DOBRA(X)
      INTEGER X, D
      D = X * 2
      PRINT *, 'Dobro de ', X, ' = ', D
      RETURN
      END
