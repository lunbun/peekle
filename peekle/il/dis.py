import pickle
import pickletools
from typing import IO
from . import il

class Disassembler:
    dispatch = {}

    def __init__(self, obj: bytes | bytearray | IO[bytes]):
        self.obj = obj
        self.program = il.Program()
        self.memo = {}
        self.stack = []
        self.metastack = []

    def _popMark(self):
        s = self.stack
        self.stack = self.metastack.pop()
        return s

    def _disassembleMark(self, op, arg):
        self.metastack.append(self.stack)
        self.stack = []
    dispatch[pickle.MARK[0]] = _disassembleMark

    def _disassembleStop(self, op, arg):
        self.program.appendInsn(il.InsnType.STOP, self.stack.pop())
        return True
    dispatch[pickle.STOP[0]] = _disassembleStop
    
    def _disassemblePop(self, op, arg):
        self.stack.pop()
    dispatch[pickle.POP[0]] = _disassemblePop

    def _disassemblePopMark(self, op, arg):
        self._popMark()
    dispatch[pickle.POP_MARK[0]] = _disassemblePopMark

    def _disassembleDup(self, op, arg):
        self.stack.append(self.stack[-1])
    dispatch[pickle.DUP[0]] = _disassembleDup

    def _disassembleConstant(self, op, arg):
        self.stack.append(il.ConstantValue(arg))
    dispatch[pickle.FLOAT[0]] = _disassembleConstant
    dispatch[pickle.INT[0]] = _disassembleConstant
    dispatch[pickle.BININT[0]] = _disassembleConstant
    dispatch[pickle.BININT1[0]] = _disassembleConstant
    dispatch[pickle.LONG[0]] = _disassembleConstant
    dispatch[pickle.BININT2[0]] = _disassembleConstant
    dispatch[pickle.NONE[0]] = _disassembleConstant
    dispatch[pickle.STRING[0]] = _disassembleConstant
    dispatch[pickle.BINSTRING[0]] = _disassembleConstant
    dispatch[pickle.SHORT_BINSTRING[0]] = _disassembleConstant
    dispatch[pickle.UNICODE[0]] = _disassembleConstant
    dispatch[pickle.BINUNICODE[0]] = _disassembleConstant
    dispatch[pickle.NEWTRUE[0]] = _disassembleConstant
    dispatch[pickle.NEWFALSE[0]] = _disassembleConstant
    dispatch[pickle.LONG1[0]] = _disassembleConstant
    dispatch[pickle.LONG4[0]] = _disassembleConstant
    dispatch[pickle.BINBYTES[0]] = _disassembleConstant
    dispatch[pickle.SHORT_BINBYTES[0]] = _disassembleConstant
    dispatch[pickle.SHORT_BINUNICODE[0]] = _disassembleConstant
    dispatch[pickle.BINUNICODE8[0]] = _disassembleConstant
    dispatch[pickle.BINBYTES8[0]] = _disassembleConstant
    dispatch[pickle.BYTEARRAY8[0]] = _disassembleConstant
    dispatch[pickle.BINFLOAT[0]] = _disassembleConstant

    def _disassembleReduce(self, op, arg):
        args = self.stack.pop()
        func = self.stack.pop()
        res = self.program.appendVarInsn(il.InsnType.CALL, func, args)
        self.stack.append(res)
    dispatch[pickle.REDUCE[0]] = _disassembleReduce

    def _disassembleBuild(self, op, arg):
        args = self.stack.pop()
        obj = self.stack[-1]
        self.program.appendInsn(il.InsnType.BUILD, obj, args)
    dispatch[pickle.BUILD[0]] = _disassembleBuild

    def _disassembleGlobal(self, op, arg):
        module, name = arg.split(' ')
        self.stack.append(il.ConstantGlobal(module, name))
    dispatch[pickle.GLOBAL[0]] = _disassembleGlobal

    def _disassembleDict(self, op, arg):
        s = self._popMark()
        p = []
        for i in range(0, len(s), 2):
            p.append((s[i], s[i + 1]))
        res = self.program.appendVarInsn(il.InsnType.MUTABLE_CONSTANT, il.ConstantDict(p))
        self.stack.append(res)
    dispatch[pickle.DICT[0]] = _disassembleDict

    def _disassembleEmptyDict(self, op, arg):
        res = self.program.appendVarInsn(il.InsnType.MUTABLE_CONSTANT, il.ConstantDict([]))
        self.stack.append(res)
    dispatch[pickle.EMPTY_DICT[0]] = _disassembleEmptyDict

    def _disassembleAppends(self, op, arg):
        s = self._popMark()
        l = self.stack[-1]
        self.program.appendInsn(il.InsnType.EXTEND, l, il.ConstantList(s))
    dispatch[pickle.APPENDS[0]] = _disassembleAppends

    def _disassmbleGet(self, op, arg):
        self.stack.append(self.memo[arg])
    dispatch[pickle.GET[0]] = _disassmbleGet
    dispatch[pickle.BINGET[0]] = _disassmbleGet
    dispatch[pickle.LONG_BINGET[0]] = _disassmbleGet

    def _disassembleList(self, op, arg):
        s = self._popMark()
        res = self.program.appendVarInsn(il.InsnType.MUTABLE_CONSTANT, il.ConstantList(s))
        self.stack.append(res)
    dispatch[pickle.LIST[0]] = _disassembleList

    def _disassembleEmptyList(self, op, arg):
        res = self.program.appendVarInsn(il.InsnType.MUTABLE_CONSTANT, il.ConstantList([]))
        self.stack.append(res)
    dispatch[pickle.EMPTY_LIST[0]] = _disassembleEmptyList

    def _disassemblePut(self, op, arg):
        self.memo[arg] = self.stack[-1]
    dispatch[pickle.PUT[0]] = _disassemblePut

    def _disassembleSetItem(self, op, arg):
        value = self.stack.pop()
        key = self.stack.pop()
        d = self.stack[-1]
        self.program.appendInsn(il.InsnType.SET_ITEM, d, key, value)
    dispatch[pickle.SETITEM[0]] = _disassembleSetItem

    def _disassembleTuple(self, op, arg):
        s = self._popMark()
        self.stack.append(il.ConstantTuple(s))
    dispatch[pickle.TUPLE[0]] = _disassembleTuple

    def _disassembleEmptyTuple(self, op, arg):
        self.stack.append(il.ConstantTuple([]))
    dispatch[pickle.EMPTY_TUPLE[0]] = _disassembleEmptyTuple

    def _disassembleSetItems(self, op, arg):
        s = self._popMark()
        d = self.stack[-1]
        for i in range(0, len(s), 2):
            self.program.appendInsn(il.InsnType.SET_ITEM, d, s[i], s[i + 1])
    dispatch[pickle.SETITEMS[0]] = _disassembleSetItems

    def _disassembleNewObj(self, op, arg):
        args = self.stack.pop()
        cls = self.stack.pop()
        res = self.program.appendVarInsn(il.InsnType.CALL, cls, args)
        self.stack.append(res)
    dispatch[pickle.NEWOBJ[0]] = _disassembleNewObj

    def _disassembleTuple1(self, op, arg):
        a = self.stack.pop()
        self.stack.append(il.ConstantTuple([a]))
    dispatch[pickle.TUPLE1[0]] = _disassembleTuple1

    def _disassembleTuple2(self, op, arg):
        b = self.stack.pop()
        a = self.stack.pop()
        self.stack.append(il.ConstantTuple([a, b]))
    dispatch[pickle.TUPLE2[0]] = _disassembleTuple2

    def _disassembleTuple3(self, op, arg):
        c = self.stack.pop()
        b = self.stack.pop()
        a = self.stack.pop()
        self.stack.append(il.ConstantTuple([a, b, c]))
    dispatch[pickle.TUPLE3[0]] = _disassembleTuple3

    def _disassembleEmptySet(self, op, arg):
        res = self.program.appendVarInsn(il.InsnType.MUTABLE_CONSTANT, il.ConstantSet([]))
        self.stack.append(res)
    dispatch[pickle.EMPTY_SET[0]] = _disassembleEmptySet

    def _disassembleFrozenSet(self, op, arg):
        s = self._popMark()
        res = self.program.appendVarInsn(il.InsnType.MUTABLE_CONSTANT, il.ConstantFrozenSet(s))
        self.stack.append(res)
    dispatch[pickle.FROZENSET[0]] = _disassembleFrozenSet

    def _disassembleStackGlobal(self, op, arg):
        name = self.stack.pop()
        module = self.stack.pop()
        res = self.program.appendVarInsn(il.InsnType.GLOBAL, module, name)
        self.stack.append(res)
    dispatch[pickle.STACK_GLOBAL[0]] = _disassembleStackGlobal

    def _disassembleMemoize(self, op, arg):
        self.memo[len(self.memo)] = self.stack[-1]
    dispatch[pickle.MEMOIZE[0]] = _disassembleMemoize

    def _disassembleIgnored(self, op, arg):
        pass
    dispatch[pickle.PROTO[0]] = _disassembleIgnored
    dispatch[pickle.FRAME[0]] = _disassembleIgnored

    def disassemble(self):
        try:
            for opcode, arg, pos in pickletools.genops(self.obj):
                op = ord(opcode.code)
                if op not in self.dispatch:
                    raise ValueError(f'Unknown or unimplemented opcode: {op} {opcode.name} at {pos} ({repr(opcode.code)})')

                shouldStop = self.dispatch[op](self, op, arg)
                if shouldStop:
                    break
        except Exception as e:
            self.program.appendInsn(il.InsnType.POISON, il.ConstantValue(str(e)))
            self.program.poison = True

        return self.program
