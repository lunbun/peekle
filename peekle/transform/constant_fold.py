from typing import cast
from .transform import TransformPass
from .. import il
from . import analysis

class ConstantValuePass(TransformPass):
    def __init__(self):
        super().__init__('Constant Value Folding')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            if not isinstance(insn, il.VariableInsn) or len(insn.args) != 2 or \
                not all(isinstance(arg, il.ConstantValue) for arg in insn.args):
                continue

            a, b = cast(il.ConstantValue, insn.args[0]).value, cast(il.ConstantValue, insn.args[1]).value
            if insn.op == il.InsnType.EQUALS:
                new = a == b
            elif insn.op == il.InsnType.NOT_EQUALS:
                new = a != b
            elif insn.op == il.InsnType.LESS_THAN:
                new = a < b
            elif insn.op == il.InsnType.LESS_EQUALS:
                new = a <= b
            elif insn.op == il.InsnType.GREATER_THAN:
                new = a > b
            elif insn.op == il.InsnType.GREATER_EQUALS:
                new = a >= b
            elif insn.op == il.InsnType.ADD:
                new = a + b
            elif insn.op == il.InsnType.SUB:
                new = a - b
            elif insn.op == il.InsnType.MUL:
                new = a * b
            elif insn.op == il.InsnType.FLOOR_DIV:
                new = a // b
            elif insn.op == il.InsnType.TRUE_DIV:
                new = a / b
            elif insn.op == il.InsnType.MOD:
                new = a % b
            elif insn.op == il.InsnType.POW:
                new = a ** b
            elif insn.op == il.InsnType.BITWISE_AND:
                new = a & b
            elif insn.op == il.InsnType.BITWISE_OR:
                new = a | b
            elif insn.op == il.InsnType.BITWISE_XOR:
                new = a ^ b
            elif insn.op == il.InsnType.LSHIFT:
                new = a << b
            elif insn.op == il.InsnType.RSHIFT:
                new = a >> b
            else:
                continue

            it.replaceInsn(il.ConstantValue(new))
            modified = True
        return modified

class ConstantGlobalPass(TransformPass):
    def __init__(self):
        super().__init__('Constant Global Folding')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            if not isinstance(insn, il.VariableInsn):
                continue

            if insn.op == il.InsnType.GLOBAL:
                if not isinstance(insn.args[0], il.ConstantValue):
                    continue
                module = insn.args[0].value

                name = None
                if len(insn.args) > 1:
                    if not isinstance(insn.args[1], il.ConstantValue):
                        continue
                    name = insn.args[1].value
                
                it.replaceInsn(il.ConstantGlobal(module, name))
                modified = True
        return modified
    
class ConstantGetItemPass(TransformPass):
    def __init__(self):
        super().__init__('Constant Get Item Folding')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            if insn.op != il.InsnType.GET_ITEM or not isinstance(insn, il.VariableInsn) or \
                not isinstance(insn.args[1], il.ConstantValue) or \
                not any(isinstance(insn.args[0], x) for x in [il.ConstantTuple, il.ConstantList, il.ConstantDict]):
                continue

            v = insn.args[0].values[cast(il.ConstantValue, insn.args[1]).value]
            it.replaceInsn(v, treatVariableAsValue=True)
            modified = True
        return modified
    
# Inlines mutable constants if they are not mutated and have a single use
class InlineMutableConstantPass(TransformPass):
    def __init__(self):
        super().__init__('Inline Mutable Constants')

    def run(self, program: il.Program) -> bool:
        modified = False
        it = iter(program)
        for insn in it:
            if insn.op != il.InsnType.MUTABLE_CONSTANT or not isinstance(insn, il.VariableInsn) or \
                len(insn.uses) != 1:
                continue

            it.replaceInsn(insn.args[0])
        return modified
