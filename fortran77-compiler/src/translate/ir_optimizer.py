from .ir import (
    IRInstr,
    IRPushI, IRPushF,
    IRAdd, IRSub, IRMul, IRDiv, IRMod,
    IRFAdd, IRFSub, IRFMul, IRFDiv,
    IREqual, IRNot, IRInf, IRInfEq, IRSup, IRSupEq,
    IRFInf, IRFInfEq, IRFSup, IRFSupEq,
    IRAnd, IROr,
    IRLabel, IRJump, IRJZ, IRPushA, IRReturn, IRStop,
    IRProgram,
)

class IROptimizer:
    def optimize(self, program: IRProgram) -> IRProgram:
        # Identifica labels referenciados por PUSHA em outras unidades para protegê-los da eliminação de labels órfãos
        global_pusha: set[str] = {
            instr.label
            for unit in program.units
            for instr in unit.instrs
            if isinstance(instr, IRPushA)
        }

        for unit in program.units:
            unit.instrs = self._run_to_fixpoint(unit.instrs, global_pusha)
        return program

    def _run_to_fixpoint(self, instrs: list[IRInstr],
                         protected: set[str] | None = None) -> list[IRInstr]:
        """Aplica as passagens em ciclo até que nenhuma produza alterações."""
        if protected is None:
            protected = set()
        for _ in range(20):   # limite de segurança contra ciclos infinitos
            new, changed = self._peephole(instrs)
            new = self._dead_code(new)
            new = self._trivial_jumps(new)
            new = self._unused_labels(new, protected)
            if not changed and new == instrs:
                break
            instrs = new
        return instrs

    def _peephole(self, instrs: list[IRInstr]) -> tuple[list[IRInstr], bool]:
        result:  list[IRInstr] = []
        changed: bool          = False
        i = 0
        while i < len(instrs):
            # Tenta padrão de 3 instruções (dois literais + operação binária)
            if i + 2 < len(instrs):
                folded = self._fold3(instrs[i], instrs[i + 1], instrs[i + 2])
                if folded is not None:
                    result.extend(folded)
                    i += 3
                    changed = True
                    continue

            # Tenta padrão de 2 instruções (literal + NOT)
            if i + 1 < len(instrs):
                folded = self._fold2(instrs[i], instrs[i + 1])
                if folded is not None:
                    result.extend(folded)
                    i += 2
                    changed = True
                    continue

            result.append(instrs[i])
            i += 1
        return result, changed

    def _fold3(self, a: IRInstr, b: IRInstr, c: IRInstr) -> list[IRInstr] | None:
        # Obtém valores inteiros ou reais dos dois operandos
        va = self._const_int(a)
        vb = self._const_int(b)
        fa = self._const_float(a)
        fb = self._const_float(b)

        # --- Operações inteiras ---
        if va is not None and vb is not None:
            r = self._eval_int(va, c, vb)
            if r is not None:
                return [IRPushI(r)]

        # --- Operações reais ---
        # Promove inteiros a reais se necessário
        fa2 = float(va) if (fa is None and va is not None) else fa
        fb2 = float(vb) if (fb is None and vb is not None) else fb
        if fa2 is not None and fb2 is not None:
            r = self._eval_float(fa2, c, fb2)
            if r is not None:
                return [IRPushF(r)]

        return None

    def _fold2(self, a: IRInstr, b: IRInstr) -> list[IRInstr] | None:
        """Tenta dobrar: PUSHI n; NOT → PUSHI (n==0)."""
        v = self._const_int(a)
        if v is not None and isinstance(b, IRNot):
            return [IRPushI(1 if v == 0 else 0)]
        return None

    def _eval_int(self, m: int, op: IRInstr, n: int) -> int | None:
        if isinstance(op, IRAdd):    return m + n
        if isinstance(op, IRSub):    return m - n   # m - n (m abaixo, n topo)
        if isinstance(op, IRMul):    return m * n
        if isinstance(op, IRDiv):    return m // n if n != 0 else None
        if isinstance(op, IRMod):    return m % n  if n != 0 else None
        if isinstance(op, IREqual):  return int(m == n)
        if isinstance(op, IRInf):    return int(m < n)
        if isinstance(op, IRInfEq):  return int(m <= n)
        if isinstance(op, IRSup):    return int(m > n)
        if isinstance(op, IRSupEq):  return int(m >= n)
        if isinstance(op, IRAnd):    return int(bool(m) and bool(n))
        if isinstance(op, IROr):     return int(bool(m) or  bool(n))
        return None

    def _eval_float(self, m: float, op: IRInstr, n: float) -> float | None:
        if isinstance(op, IRFAdd):   return m + n
        if isinstance(op, IRFSub):   return m - n
        if isinstance(op, IRFMul):   return m * n
        if isinstance(op, IRFDiv):   return m / n if n != 0.0 else None
        if isinstance(op, IRFInf):   return float(m < n)
        if isinstance(op, IRFInfEq): return float(m <= n)
        if isinstance(op, IRFSup):   return float(m > n)
        if isinstance(op, IRFSupEq): return float(m >= n)
        if isinstance(op, IREqual):  return float(m == n)
        return None

    @staticmethod
    def _const_int(instr: IRInstr) -> int | None:
        return instr.val if isinstance(instr, IRPushI) else None

    @staticmethod
    def _const_float(instr: IRInstr) -> float | None:
        return instr.val if isinstance(instr, IRPushF) else None

    def _dead_code(self, instrs: list[IRInstr]) -> list[IRInstr]:
        """
        Remove instruções inacessíveis após saltos/RETURN/STOP até ao próximo label.
        """
        result = []
        skip   = False
        for instr in instrs:
            if isinstance(instr, IRLabel):
                skip = False                  # label reactiva o fluxo
            if not skip:
                result.append(instr)
            if isinstance(instr, (IRJump, IRReturn, IRStop)):
                skip = True
        return result

    def _unused_labels(self, instrs: list[IRInstr],
                       protected: set[str]) -> list[IRInstr]:
        """
        Remove labels que não são alvo de nenhum salto, PUSHA local, ou referência.
        """
        # Referências locais: JUMPs e PUSHAs dentro desta unidade
        local_refs: set[str] = set(protected)
        for instr in instrs:
            if isinstance(instr, IRJump):  local_refs.add(instr.label)
            if isinstance(instr, IRJZ):    local_refs.add(instr.label)
            if isinstance(instr, IRPushA): local_refs.add(instr.label)
        return [
            instr for instr in instrs
            if not (isinstance(instr, IRLabel) and instr.name not in local_refs)
        ]

    def _trivial_jumps(self, instrs: list[IRInstr]) -> list[IRInstr]:
        changed = True
        while changed:
            changed = False
            result  = []
            i = 0
            while i < len(instrs):
                if (i + 1 < len(instrs)
                        and isinstance(instrs[i], IRJump)
                        and isinstance(instrs[i + 1], IRLabel)
                        and instrs[i].label == instrs[i + 1].name):
                    # Salta o JUMP; o label fica
                    changed = True
                    i += 1   # não incrementa de 2 → label é emitido normalmente
                else:
                    result.append(instrs[i])
                    i += 1
            instrs = result
        return instrs
