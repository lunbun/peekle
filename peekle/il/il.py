from __future__ import annotations
from typing import cast
from enum import Enum

# An SSA IL value.
class Value:
    @staticmethod
    def computeDefs(values: list[Value]) -> set[VariableInsn]:
        defs = set()
        for value in values:
            defs.update(value.valueDefs())
        return defs

    def stringifyValue(self) -> str:
        raise NotImplementedError()
    
    # Returns a list of variable definitions that this value depends on.
    def valueDefs(self) -> set[VariableInsn]:
        return set()
    
    def replaceVarInsn(self, old: VariableInsn, new: Value):
        pass

class ConstantValue(Value):
    def __init__(self, value):
        self.value = value

    def stringifyValue(self):
        if isinstance(self.value, str):
            return repr(self.value)
        else:
            return str(self.value)
        
class ConstantTuple(Value):
    def __init__(self, values: list[Value]):
        self.values = values

    def stringifyValue(self):
        return f'({", ".join(map(lambda value: value.stringifyValue(), self.values))})'
    
    def valueDefs(self):
        return Value.computeDefs(self.values)
    
    def replaceVarInsn(self, old: VariableInsn, new: Value):
        for i, value in enumerate(self.values):
            if value is old:
                self.values[i] = new
            else:
                value.replaceVarInsn(old, new)
    
class ConstantList(Value):
    def __init__(self, values: list[Value]):
        self.values = values

    def stringifyValue(self):
        return f'[{", ".join(map(lambda value: value.stringifyValue(), self.values))}]'
    
    def valueDefs(self):
        return Value.computeDefs(self.values)
    
    def replaceVarInsn(self, old: VariableInsn, new: Value):
        for i, value in enumerate(self.values):
            if value is old:
                self.values[i] = new
            else:
                value.replaceVarInsn(old, new)
    
class ConstantDict(Value):
    def __init__(self, values: list[tuple[Value, Value]]):
        self.values = values

    def stringifyValue(self):
        return f'{{{", ".join(map(lambda pair: f"{pair[0].stringifyValue()}: {pair[1].stringifyValue()}", self.values))}}}'

    def valueDefs(self):
        defs = Value.computeDefs(key for key, value in self.values)
        defs.update(Value.computeDefs(value for key, value in self.values))
        return defs
    
    def replaceVarInsn(self, old: VariableInsn, new: Value):
        for i, (key, value) in enumerate(self.values):
            if key is old:
                self.values[i] = (new, value)
            else:
                key.replaceVarInsn(old, new)
            if value is old:
                self.values[i] = (key, new)
            else:
                value.replaceVarInsn(old, new)
    
class ConstantSet(Value):
    def __init__(self, values: list[Value]):
        self.values = values

    def stringifyValue(self):
        return f'set({", ".join(map(lambda value: value.stringifyValue(), self.values))})'
    
    def valueDefs(self):
        return Value.computeDefs(self.values)
    
    def replaceVarInsn(self, old: VariableInsn, new: Value):
        for i, value in enumerate(self.values):
            if value is old:
                self.values[i] = new
            else:
                value.replaceVarInsn(old, new)

class ConstantFrozenSet(Value):
    def __init__(self, values: list[Value]):
        self.values = values

    def stringifyValue(self):
        return f'frozenset({", ".join(map(lambda value: value.stringifyValue(), self.values))})'
    
    def valueDefs(self):
        return Value.computeDefs(self.values)
    
    def replaceVarInsn(self, old: VariableInsn, new: Value):
        for i, value in enumerate(self.values):
            if value is old:
                self.values[i] = new
            else:
                value.replaceVarInsn(old, new)
    
class ConstantGlobal(Value):
    def __init__(self, module: str, name: str | None):
        self.module = module
        self.name = name

    def stringifyValue(self):
        return f'{self.module}.{self.name}' if self.name is not None else self.module

class InsnType(Enum):
    STOP = 0
    CALL = 1
    GLOBAL = 2
    GET_ATTR = 3
    SET_ATTR = 4
    GET_ITEM = 5
    SET_ITEM = 6
    LOCAL = 7
    MUTABLE_CONSTANT = 8
    BUILD = 9

    LEN = 10
    EXTEND = 11

    EQUALS = 12
    NOT_EQUALS = 13
    LESS_THAN = 14
    LESS_EQUALS = 15
    GREATER_THAN = 16
    GREATER_EQUALS = 17
    
    ADD = 18
    SUB = 19
    MUL = 20
    FLOOR_DIV = 21
    TRUE_DIV = 22
    MOD = 23
    POW = 24

    BITWISE_AND = 25
    BITWISE_OR = 26
    BITWISE_XOR = 27
    LSHIFT = 28
    RSHIFT = 29

    POISON = 255

class Insn:
    def __init__(self, op: InsnType, args: list[Value]):
        self.op = op
        self.args = args
        self.prev: Insn | None = None
        self.next: Insn | None = None
        self.defs = Value.computeDefs(args)
    
    def stringifyInsn(self):
        return f'{self.op.name.lower()} {", ".join(map(lambda arg: arg.stringifyValue(), self.args))}'
    
    def hasUses(self):
        return False
    
    def replaceVarInsn(self, old: VariableInsn, new: Value):
        for i, arg in enumerate(self.args):
            if arg is old:
                self.args[i] = new
            else:
                arg.replaceVarInsn(old, new)
        self.defs = Value.computeDefs(self.args)

    def __iter__(self):
        insn = self
        while insn is not None:
            yield insn
            insn = insn.next

class VariableInsn(Insn, Value):
    def __init__(self, op: InsnType, args: list[Value], name: str):
        super().__init__(op, args)
        self.name = name
        self.uses: set[Insn] = set()

    def stringifyValue(self):
        return self.name

    def stringifyInsn(self):
        return f'{self.name} = {self.op.name.lower()} {", ".join(map(lambda arg: arg.stringifyValue(), self.args))}'
    
    def hasUses(self):
        return len(self.uses) > 0
    
    def valueDefs(self):
        return {self}

class Program:
    def __init__(self):
        self.begin = None
        self.end = None
        self.poison = False
        self.variableCount = 0

    def insertInsn(self, insn: Insn, after: Insn):
        if insn.prev is not None or insn.next is not None:
            raise ValueError('Cannot insert an instruction that is already in a program')

        if after is None:
            insn.next = self.begin
            if self.begin is not None:
                self.begin.prev = insn

            self.begin = insn
            if self.end is None:
                self.end = insn
        else:
            insn.next = after.next
            if after.next is not None:
                after.next.prev = insn

            after.next = insn
            if after is self.end:
                self.end = insn
        insn.prev = after

        for def_ in insn.defs:
            def_.uses.add(insn)

    def removeInsn(self, insn: Insn, skipUseCheck: bool = False):
        if insn.prev is None and insn.next is None:
            raise ValueError('Cannot remove an instruction that is not in a program')
        if not skipUseCheck and insn.hasUses():
            raise ValueError('Cannot remove a variable instruction if it has uses')

        if insn.prev is None:
            self.begin = insn.next
        else:
            insn.prev.next = insn.next

        if insn.next is None:
            self.end = insn.prev
        else:
            insn.next.prev = insn.prev

        insn.prev = None
        insn.next = None

        for def_ in insn.defs:
            def_.uses.remove(insn)

    # Replaces an instruction with a new value.
    def replaceInsn(self, old: Insn, new: Insn | Value, treatVariableAsValue: bool = False):
        if not treatVariableAsValue and isinstance(new, Insn):
            if old.hasUses():
                if not isinstance(new, VariableInsn):
                    raise ValueError('Cannot replace a variable instruction with a non-variable instruction if it has uses')
                
                old = cast(VariableInsn, old)
                for use in old.uses:
                    use.replaceVarInsn(old, new)
                new.uses = old.uses
                old.uses = set()

            after = old.prev
            self.removeInsn(old)
            self.insertInsn(new, after)
        elif treatVariableAsValue or isinstance(new, Value):
            if isinstance(old, VariableInsn):
                for use in old.uses:
                    use.replaceVarInsn(old, new)
                    for def_ in old.defs:
                        def_.uses.add(use)
                old.uses = set()

            self.removeInsn(old)
        else:
            raise NotImplementedError()
        
    def createVarInsn(self, op: InsnType, *args: Value):
        insn = VariableInsn(op, list(args), f'v{self.variableCount}')
        self.variableCount += 1
        return insn
        
    # Creates a new Insn that appends it to the program.
    def appendInsn(self, op: InsnType, *args: Value):
        self.insertInsn(Insn(op, list(args)), self.end)

    # Creates a new VariableInsn and appends it to the program.
    def appendVarInsn(self, op: InsnType, *args: Value):
        insn = self.createVarInsn(op, *args)
        self.insertInsn(insn, self.end)
        return insn
        
    def __iter__(self):
        return Program.Iterator(self)

    def __str__(self):
        return '\n'.join(map(lambda insn: insn.stringifyInsn(), self))
    
    class Iterator:
        def __init__(self, program: Program):
            self.program = program
            self.current = None

        def __next__(self) -> Insn:
            self.current = self.program.begin if self.current is None else self.current.next
            if self.current is None:
                raise StopIteration()
            return self.current
        
        def __iter__(self):
            return self
        
        # Remove the current instruction in an iterator-safe way.
        def removeInsn(self):
            target = self.current
            self.current = self.current.prev
            self.program.removeInsn(target)

        # Replace the current instruction in an iterator-safe way.
        def replaceInsn(self, insn: Insn | Value, treatVariableAsValue: bool = False):
            target = self.current
            if isinstance(insn, Insn):
                self.current = insn
            else:
                self.current = self.current.prev
            self.program.replaceInsn(target, insn, treatVariableAsValue=treatVariableAsValue)

        # Move the current instruction to a new location in an iterator-safe way.
        def moveInsn(self, after: Insn):
            target = self.current
            self.current = self.current.prev
            self.program.removeInsn(target, skipUseCheck=True)
            self.program.insertInsn(target, after)
