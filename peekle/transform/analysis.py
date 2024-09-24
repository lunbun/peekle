import sys
import builtins
from .. import il
import functools

# (insn, expected # args)
GLOBAL_CALL_MAP = {
    getattr: (il.InsnType.GET_ATTR, 2),
    setattr: (il.InsnType.SET_ATTR, 3),
}

# (insn, expected # args)
INSTANCE_DUNDER_MAP = {
    '__getitem__': (il.InsnType.GET_ITEM, 1),
    '__setitem__': (il.InsnType.SET_ITEM, 2),
    '__len__': (il.InsnType.LEN, 0),
    '__eq__': (il.InsnType.EQUALS, 1),
    '__ne__': (il.InsnType.NOT_EQUALS, 1),
    '__lt__': (il.InsnType.LESS_THAN, 1),
    '__le__': (il.InsnType.LESS_EQUALS, 1),
    '__gt__': (il.InsnType.GREATER_THAN, 1),
    '__ge__': (il.InsnType.GREATER_EQUALS, 1),
    '__add__': (il.InsnType.ADD, 1),
    '__sub__': (il.InsnType.SUB, 1),
    '__mul__': (il.InsnType.MUL, 1),
    '__floordiv__': (il.InsnType.FLOOR_DIV, 1),
    '__truediv__': (il.InsnType.TRUE_DIV, 1),
    '__mod__': (il.InsnType.MOD, 1),
    '__pow__': (il.InsnType.POW, 1),
    '__and__': (il.InsnType.BITWISE_AND, 1),
    '__or__': (il.InsnType.BITWISE_OR, 1),
    '__xor__': (il.InsnType.BITWISE_XOR, 1),
    '__lshift__': (il.InsnType.LSHIFT, 1),
    '__rshift__': (il.InsnType.RSHIFT, 1),
}
for cls in [int, float, complex, str, bytes, bytearray, list, tuple, dict, set, frozenset]:
    for name, (op, nargs) in INSTANCE_DUNDER_MAP.items():
        if hasattr(cls, name):
            GLOBAL_CALL_MAP[getattr(cls, name)] = (op, nargs + 1)

SIDE_EFFECT_INSNS = set([
    il.InsnType.STOP,
    il.InsnType.SET_ATTR,
    il.InsnType.SET_ITEM,
    il.InsnType.BUILD,
    il.InsnType.EXTEND,
    il.InsnType.POISON
])

SIDE_EFFECT_FREE_CALLS = set([
    __import__,
    range,
    abs,
    bin,
    chr,
    copyright,
    credits,
    dir,
    getattr,
    globals,
    hasattr,
    hash,
    help,
    hex,
    id,
    len,
    license,
    locals,
    map,
    max,
    min,
    oct,
    round,
    functools.partial
])

BUILTIN_CALLS = set()
for name in dir(builtins):
    obj = getattr(builtins, name)
    if callable(obj):
        BUILTIN_CALLS.add(obj)

def getPathAttribute(obj, name: str):
    try:
        for attr in name.split('.'):
            obj = getattr(obj, attr)
        return obj
    except AttributeError:
        return None
    
def getGlobal(global_: il.ConstantGlobal):
    if global_.module not in sys.modules:
        return None
    
    obj = sys.modules[global_.module]
    if global_.name is not None:
        obj = getPathAttribute(obj, global_.name)
    return obj

def isConstantCall(insn: il.Insn):
    return insn.op == il.InsnType.CALL and isinstance(insn.args[0], il.ConstantGlobal) and \
        isinstance(insn.args[1], il.ConstantTuple)

def maybeGetConstantCallee(insn: il.Insn):
    if isConstantCall(insn):
        return getGlobal(insn.args[0])
    return None

def hasSideEffects(insn: il.Insn):
    if insn.op in SIDE_EFFECT_INSNS:
        return True
    
    if insn.op == il.InsnType.CALL:
        if not isConstantCall(insn):
            return True
        
        callee = getGlobal(insn.args[0])
        if callee is None:
            return True
        
        return callee not in SIDE_EFFECT_FREE_CALLS

    return False
