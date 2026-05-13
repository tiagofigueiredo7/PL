      PROGRAM POTENCIA
      INTEGER B, E, RESULT
      PRINT *, 'Escreva a base e o expoente (inteiros): '
      READ *, B, E
      RESULT = B ** E
      PRINT *, B, ' elevado a ', E, ' = ', RESULT
      IF (RESULT .GT. B ** 2) PRINT *, 'Maior que o quadrado da base'
      END
