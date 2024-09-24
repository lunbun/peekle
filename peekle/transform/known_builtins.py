from typing import cast
from .transform import TransformPass
from .. import il
from . import analysis

# Replaces known global calls with their corresponding instructions.
class GlobalCallPass(TransformPass):
    def __init__(self):
        super().__init__('Global Call Simplification')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            callee = analysis.maybeGetConstantCallee(insn)
            if callee is None or callee not in analysis.GLOBAL_CALL_MAP:
                continue

            replacementInsn, nargs = analysis.GLOBAL_CALL_MAP[callee]
            args = cast(il.ConstantTuple, insn.args[1]).values
            if len(args) != nargs:
                continue

            insn2 = program.createVarInsn(replacementInsn, *args)
            it.replaceInsn(insn2)
            modified = True
        return modified
    
# Replaces known instance dunder calls with their corresponding instructions.
class InstanceDunderPass(TransformPass):
    def __init__(self):
        super().__init__('Instance Dunder Simplification')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            if insn.op != il.InsnType.GET_ATTR or not isinstance(insn, il.VariableInsn) or \
                not isinstance(insn.args[1], il.ConstantValue):
                continue

            name = insn.args[1].value
            if name not in analysis.INSTANCE_DUNDER_MAP:
                continue

            replacementInsn, nargs = analysis.INSTANCE_DUNDER_MAP[name]
            replaceable: list[il.Insn] = []
            for use in insn.uses:
                if use.op != il.InsnType.CALL or use.args[0] is not insn or \
                    not isinstance(use.args[1], il.ConstantTuple) or len(use.args[1].values) != nargs:
                    continue
                replaceable.append(use)

            this = insn.args[0]
            for r in replaceable:
                args = cast(il.ConstantTuple, r.args[1]).values
                insn2 = program.createVarInsn(replacementInsn, this, *args)
                program.replaceInsn(r, insn2)
                modified = True

            if not insn.hasUses():
                it.removeInsn()
                modified = True
        return modified
    
# Replaces import calls with global constants (if possible) or GLOBAL instructions.
class ImportToGlobalPass(TransformPass):
    def __init__(self):
        super().__init__('Import to Global Simplification')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            callee = analysis.maybeGetConstantCallee(insn)
            if callee is not __import__ or not isinstance(insn, il.VariableInsn):
                continue

            module = cast(il.ConstantTuple, insn.args[1]).values[0]
            if isinstance(module, il.ConstantValue):
                value = il.ConstantGlobal(module.value, None)
            else:
                value = program.createVarInsn(il.InsnType.GLOBAL, module)
            it.replaceInsn(value)
            modified = True
        return modified
    
# Replaces constant GET_ATTR insns on constant globals with a single constant global.
class GlobalReductionPass(TransformPass):
    def __init__(self):
        super().__init__('Global Reduction')

    def _reduceGlobal(self, program: il.Program, insn: il.VariableInsn, it: il.Program.Iterator | None = None) -> il.Value:
        if insn.op != il.InsnType.GET_ATTR or not isinstance(insn, il.VariableInsn) or \
                not isinstance(insn.args[0], il.ConstantGlobal) or \
                not isinstance(insn.args[1], il.ConstantValue):
            return False

        global_ = cast(il.ConstantGlobal, insn.args[0])
        if global_.name is None:
            name = insn.args[1].value
        else:
            name = global_.name + '.' + insn.args[1].value

        global_ = il.ConstantGlobal(global_.module, name)
        uses = list(insn.uses)
        if it is None:
            program.replaceInsn(insn, global_)
        else:
            it.replaceInsn(global_)

        for use in uses:
            self._reduceGlobal(program, use)
    
        return True

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            modified |= self._reduceGlobal(program, insn, it)
        return modified

# Replaces GET_ITEM insns on locals() with a local instruction.
class LocalsPass(TransformPass):
    def __init__(self):
        super().__init__('Locals Simplification')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            callee = analysis.maybeGetConstantCallee(insn)
            if callee is not locals or not isinstance(insn, il.VariableInsn):
                continue

            replaceable: list[il.Insn] = []
            for use in insn.uses:
                if use.op != il.InsnType.GET_ITEM or not use.args[0] is insn:
                    continue
                replaceable.append(use)
                
            for r in replaceable:
                insn2 = program.createVarInsn(il.InsnType.LOCAL, r.args[1])
                program.replaceInsn(r, insn2)
                modified = True

            if not insn.hasUses():
                it.removeInsn()
                modified = True
        return modified
