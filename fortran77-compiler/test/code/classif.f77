      PROGRAM CLASSIF
      INTEGER N
      LOGICAL ISPOS, ISNEG, ISEVEN
      PRINT *, 'Escreva um valor inteiro: '
      READ *, N
      ISPOS = N .GT. 0
      ISNEG = N .LT. 0
      ISEVEN = MOD(N, 2) .EQ. 0
      IF (ISPOS) THEN
        PRINT *, N, ' e positivo'
      ELSE
        IF (ISNEG) THEN
          PRINT *, N, ' e negativo'
        ELSE
          PRINT *, N, ' e zero'
        ENDIF
      ENDIF
      IF (ISEVEN) PRINT *, N, ' e par'
      IF (.NOT. ISEVEN) PRINT *, N, ' e impar'
      END
