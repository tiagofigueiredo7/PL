      PROGRAM ARRAYOPS
      INTEGER NUMS(5), I, MINVAL, MAXVAL, SOMA
      REAL MEDIA
      SOMA = 0
      PRINT *, 'Escreva 5 numeros inteiros: '
      DO 10 I = 1, 5
        READ *, NUMS(I)
        SOMA = SOMA + NUMS(I)
   10 CONTINUE
      MINVAL = NUMS(1)
      MAXVAL = NUMS(1)
      DO 20 I = 2, 5
        IF (NUMS(I) .LT. MINVAL) MINVAL = NUMS(I)
        IF (NUMS(I) .GT. MAXVAL) MAXVAL = NUMS(I)
   20 CONTINUE
      MEDIA = SOMA / 5.0
      PRINT *, 'Min:', MINVAL,
     +         ' Max:', MAXVAL
      PRINT *, 'Media:', MEDIA
      IF (MINVAL .EQ. MAXVAL) GOTO 99
      PRINT *, 'O array nao e constante'
   99 CONTINUE
      STOP
      END
