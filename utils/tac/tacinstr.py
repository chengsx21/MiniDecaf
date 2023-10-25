from enum import Enum, auto, unique
from typing import Any, Optional, Union

from utils.label.label import Label
from utils.tac.nativeinstr import NativeInstr
from utils.tac.reg import Reg

from .tacop import *
from .tacvisitor import TACVisitor
from .temp import Temp


class TACInstr:
    def __init__(
        self,
        kind: InstrKind,
        dsts: list[Temp],
        srcs: list[Temp],
        label: Optional[Label],
    ) -> None:
        self.kind = kind
        self.dsts = dsts.copy()
        self.srcs = srcs.copy()
        self.label = label

    def getRead(self) -> list[int]:
        return [src.index for src in self.srcs]

    def getWritten(self) -> list[int]:
        return [dst.index for dst in self.dsts]

    def isLabel(self) -> bool:
        return self.kind is InstrKind.LABEL

    def isSequential(self) -> bool:
        return self.kind == InstrKind.SEQ

    def isReturn(self) -> bool:
        return self.kind == InstrKind.RET

    #! 将 TACInstr 转换为 NativeInstr, 用于输出汇编指令
    def toNative(self, dstRegs: list[Reg], srcRegs: list[Reg]) -> NativeInstr:
        oldDsts = dstRegs
        oldSrcs = srcRegs
        self.dsts = dstRegs
        self.srcs = srcRegs
        instrString = self.__str__()
        newInstr = NativeInstr(self.kind, dstRegs, srcRegs, self.label, instrString)
        self.dsts = oldDsts
        self.srcs = oldSrcs
        return newInstr

    def accept(self, v: TACVisitor) -> None:
        pass


# Assignment instruction.
class Assign(TACInstr):
    def __init__(self, dst: Temp, src: Temp) -> None:
        super().__init__(InstrKind.SEQ, [dst], [src], None)
        self.dst = dst
        self.src = src

    def __str__(self) -> str:
        return "%s = %s" % (self.dst, self.src)

    def accept(self, v: TACVisitor) -> None:
        v.visitAssign(self)


# Loading an immediate 32-bit constant.
class LoadImm4(TACInstr):
    def __init__(self, dst: Temp, value: int) -> None:
        super().__init__(InstrKind.SEQ, [dst], [], None)
        self.dst = dst
        self.value = value

    def __str__(self) -> str:
        return "%s = %d" % (self.dst, self.value)

    def accept(self, v: TACVisitor) -> None:
        v.visitLoadImm4(self)


# Unary operations.
class Unary(TACInstr):
    def __init__(self, op: TacUnaryOp, dst: Temp, operand: Temp) -> None:
        super().__init__(InstrKind.SEQ, [dst], [operand], None)
        self.op = op
        self.dst = dst
        self.operand = operand

    def __str__(self) -> str:
        opStr = {
            TacUnaryOp.NEG: "-",
            TacUnaryOp.BIT_NOT: "~",
            TacUnaryOp.LOGIC_NOT: "!",
        }[self.op]
        return "%s = %s %s" % (self.dst, opStr, self.operand)

    def accept(self, v: TACVisitor) -> None:
        v.visitUnary(self)


# Binary Operations.
class Binary(TACInstr):
    def __init__(self, op: TacBinaryOp, dst: Temp, lhs: Temp, rhs: Temp) -> None:
        super().__init__(InstrKind.SEQ, [dst], [lhs, rhs], None)
        self.op = op
        self.dst = dst
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self) -> str:
        opStr = {
            TacBinaryOp.ADD: "+",
            TacBinaryOp.SUB: "-",
            TacBinaryOp.MUL: "*",
            TacBinaryOp.DIV: "/",
            TacBinaryOp.MOD: "%",
            TacBinaryOp.EQU: "==",
            TacBinaryOp.NEQ: "!=",
            TacBinaryOp.SLT: "<",
            TacBinaryOp.LEQ: "<=",
            TacBinaryOp.SGT: ">",
            TacBinaryOp.GEQ: ">=",
            TacBinaryOp.LAND: "&&",
            TacBinaryOp.LOR: "||",
        }[self.op]
        return "%s = (%s %s %s)" % (self.dst, self.lhs, opStr, self.rhs)

    def accept(self, v: TACVisitor) -> None:
        v.visitBinary(self)


# Branching instruction.
class Branch(TACInstr):
    def __init__(self, target: Label) -> None:
        super().__init__(InstrKind.JMP, [], [], target)
        self.target = target

    def __str__(self) -> str:
        return "branch %s" % str(self.target)

    def accept(self, v: TACVisitor) -> None:
        v.visitBranch(self)


# Branching with conditions.
class CondBranch(TACInstr):
    def __init__(self, op: CondBranchOp, cond: Temp, target: Label) -> None:
        super().__init__(InstrKind.COND_JMP, [], [cond], target)
        self.op = op
        self.cond = cond
        self.target = target

    def __str__(self) -> str:
        return "if (%s %s) branch %s" % (
            self.cond,
            "== 0" if self.op == CondBranchOp.BEQ else "!= 0",
            str(self.target),
        )

    def accept(self, v: TACVisitor) -> None:
        v.visitCondBranch(self)


# Function parameter.
class Param(TACInstr):
    def __init__(self, param: Temp) -> None:
        super().__init__(InstrKind.PARAM, [], [param], None)
        self.param = param

    def __str__(self) -> str:
        return "PARAM " + str(self.param)

    def accept(self, v: TACVisitor) -> None:
        v.visitParam(self)


# Call instruction.
class Call(TACInstr):
    def __init__(self, param: Temp, label: Label) -> None:
        super().__init__(InstrKind.CALL, [param], [], label)
        self.param = param
        self.label = label

    def __str__(self) -> str:
        return str(self.param) + " = CALL %s" % str(self.label)

    def accept(self, v: TACVisitor) -> None:
        v.visitCall(self)


# Return instruction.
class Return(TACInstr):
    def __init__(self, value: Optional[Temp]) -> None:
        if value is None:
            super().__init__(InstrKind.RET, [], [], None)
        else:
            super().__init__(InstrKind.RET, [], [value], None)
        self.value = value

    def __str__(self) -> str:
        return "return" if (self.value is None) else ("return " + str(self.value))

    def accept(self, v: TACVisitor) -> None:
        v.visitReturn(self)


# Load Address instruction.
class LoadAddress(TACInstr):
    def __init__(self, symbol, dst: Temp):
        super().__init__(InstrKind.SEQ, [dst], [], None)
        self.symbol = symbol

    def __str__(self) -> str:
        return "%s = LOAD_SYMBOL %s" % (self.dsts[0], self.symbol.name)

    def accept(self, v: TACVisitor) -> None:
        return v.visitLoadAddress(self)


# Load Word instruction.
class LoadIntLiteral(TACInstr):
    def __init__(self, dst: Temp, base: Temp, offset: int):
        super().__init__(InstrKind.SEQ, [dst], [base], None)
        self.offset = offset

    def __str__(self) -> str:
        return "%s = LOAD %s, %d" % (self.dsts[0], self.srcs[0], self.offset)

    def accept(self, v: TACVisitor) -> None:
        return v.visitLoadIntLiteral(self)


# Store Word instruction.
class StoreIntLiteral(TACInstr):
    def __init__(self, src: Temp, base: Temp, offset: int):
        super().__init__(InstrKind.SEQ, [], [src, base], None)
        self.offset = offset

    def __str__(self) -> str:
        return "STORE %s %s, %d" % (self.srcs[0], self.srcs[1], self.offset)

    def accept(self, v: TACVisitor) -> None:
        return v.visitStoreIntLiteral(self)


# Annotation (used for debugging).
class Memo(TACInstr):
    def __init__(self, msg: str) -> None:
        super().__init__(InstrKind.SEQ, [], [], None)
        self.msg = msg

    def __str__(self) -> str:
        return "memo '%s'" % self.msg

    def accept(self, v: TACVisitor) -> None:
        v.visitMemo(self)


# Label (function entry or branching target).
class Mark(TACInstr):
    def __init__(self, label: Label) -> None:
        super().__init__(InstrKind.LABEL, [], [], label)

    def __str__(self) -> str:
        return "%s:" % str(self.label)

    def accept(self, v: TACVisitor) -> None:
        v.visitMark(self)
