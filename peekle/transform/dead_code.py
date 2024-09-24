from .transform import TransformPass
from .. import il
from . import analysis

class DeadCodePass(TransformPass):
    def __init__(self):
        super().__init__('Dead Code Elimination')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            if insn.hasUses():
                continue

            if not analysis.hasSideEffects(insn):
                it.removeInsn()
                modified = True
                continue

            if isinstance(insn, il.VariableInsn):
                insn2 = il.Insn(insn.op, insn.args)
                it.replaceInsn(insn2)
                modified = True
        return modified
