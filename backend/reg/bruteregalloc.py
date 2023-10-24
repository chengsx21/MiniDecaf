import random

from backend.dataflow.basicblock import BasicBlock, BlockKind
from backend.dataflow.cfg import CFG
from backend.dataflow.loc import Loc
from backend.reg.regalloc import RegAlloc
from backend.riscv.riscvasmemitter import RiscvAsmEmitter
from backend.subroutineemitter import SubroutineEmitter
from backend.subroutineinfo import SubroutineInfo
from utils.riscv import Riscv
from utils.tac.reg import Reg
from utils.tac.temp import Temp
from utils.tac.tacop import InstrKind
from utils.tac.tacinstr import TACInstr

"""
BruteRegAlloc: one kind of RegAlloc

bindings: map from temp.index to Reg

we don't need to take care of GlobalTemp here
because we can remove all the GlobalTemp in selectInstr process

1. accept: 根据每个函数的 CFG 进行寄存器分配，寄存器分配结束后生成相应汇编代码
2. bind: 将一个 Temp 与寄存器绑定
3. unbind: 将一个 Temp 与相应寄存器解绑定
4. localAlloc: 根据数据流对一个 BasicBlock 内的指令进行寄存器分配
5. allocForLoc: 每一条指令进行寄存器分配
6. allocRegFor: 根据数据流决定为当前 Temp 分配哪一个寄存器
"""

class BruteRegAlloc(RegAlloc):
    def __init__(self, emitter: RiscvAsmEmitter) -> None:
        super().__init__(emitter)
        self.bindings = {}
        self.maxNumParams = 8
        for reg in emitter.allocatableRegs:
            # reg.used == True 表示寄存器曾被分配, 包含一个数值
            reg.used = False

    def accept(self, graph: CFG, info: SubroutineInfo) -> None:
        self.functionParams = []
        self.callerSavedRegs = {}
        subEmitter = self.emitter.emitSubroutine(info)

        # 为参数分配寄存器
        for index in range(min(info.numArgs, self.maxNumParams)):
            self.bind(Temp(index), Riscv.ArgRegs[index])
            subEmitter.emitStoreToStack(Riscv.ArgRegs[index])

        for (index, bb) in enumerate(graph.iterator()):
            if bb.label is not None:
                subEmitter.emitLabel(bb.label)
            if graph.reachable(index):
                self.localAlloc(bb, subEmitter)
        subEmitter.emitEnd()

    def bind(self, temp: Temp, reg: Reg):
        reg.used = True
        self.bindings[temp.index] = reg
        reg.occupied = True
        reg.temp = temp

    def unbind(self, temp: Temp):
        if temp.index in self.bindings:
            self.bindings[temp.index].occupied = False
            self.bindings.pop(temp.index)

    def callerParamCount(self):
        return len(self.functionParams)

    def localAlloc(self, bb: BasicBlock, subEmitter: SubroutineEmitter):
        self.bindings.clear()
        for reg in self.emitter.allocatableRegs:
            reg.occupied = False

        # in step9, you may need to think about how to store callersave regs here
        for loc in bb.allSeq():
            subEmitter.emitComment(str(loc.instr))

            self.allocForLoc(loc, subEmitter)

        for tempindex in bb.liveOut:
            if tempindex in self.bindings:
                subEmitter.emitStoreToStack(self.bindings.get(tempindex))

        if (not bb.isEmpty()) and (bb.kind is not BlockKind.CONTINUOUS):
            self.allocForLoc(bb.locs[len(bb.locs) - 1], subEmitter)

    def allocForLoc(self, loc: Loc, subEmitter: SubroutineEmitter):
        instr = loc.instr
        srcRegs: list[Reg] = []
        dstRegs: list[Reg] = []

        for i in range(len(instr.srcs)):
            temp = instr.srcs[i]
            if isinstance(temp, Reg):
                srcRegs.append(temp)
            else:
                srcRegs.append(self.allocRegFor(temp, True, loc.liveIn, subEmitter))

        for i in range(len(instr.dsts)):
            temp = instr.dsts[i]
            if isinstance(temp, Reg):
                dstRegs.append(temp)
            else:
                dstRegs.append(self.allocRegFor(temp, False, loc.liveIn, subEmitter))

        if instr.kind == InstrKind.PARAM:
            self.allocForParam(instr, srcRegs, subEmitter)
        elif instr.kind == InstrKind.CALL:
            self.allocForCall(instr, srcRegs, dstRegs, subEmitter)
        else:
            subEmitter.emitNative(instr.toNative(dstRegs, srcRegs))

    def allocForParam(self, instr: TACInstr, srcRegs: list[Reg], subEmitter: SubroutineEmitter):
        # 保存前八个参数到寄存器中
        if self.callerParamCount() < self.maxNumParams:
            reg = Riscv.ArgRegs[self.callerParamCount()]
            # 将寄存器解绑, 稍后恢复
            if reg.occupied:
                subEmitter.emitStoreToStack(reg)
                self.callerSavedRegs[reg] = reg.temp
                self.unbind(reg.temp)
            subEmitter.emitReg(reg, srcRegs[0])
        self.functionParams.append(instr.srcs[0])

    def allocForCall(self, instr: TACInstr, srcRegs: list[Reg], dstRegs: list[Reg], subEmitter: SubroutineEmitter):
        # 调用前保存 caller-saved 寄存器
        for reg in Riscv.CallerSaved:
            if reg.occupied:
                subEmitter.emitStoreToStack(reg)
                self.callerSavedRegs[reg] = reg.temp
                self.unbind(reg.temp)

        # 保存多余的参数到栈中
        if self.callerParamCount() > self.maxNumParams:
            for (index, temp) in enumerate(self.functionParams[self.maxNumParams:][::-1]):
                subEmitter.emitStoreParamToStack(temp, index)
            subEmitter.emitNative(instr.toNative(dstRegs, srcRegs))
            subEmitter.emitRestoreStackPointer(4 * (self.callerParamCount() - self.maxNumParams))
        else:
            subEmitter.emitNative(instr.toNative(dstRegs, srcRegs))
        self.functionParams = []

        # 调用后恢复 caller-saved 寄存器
        for reg, temp in self.callerSavedRegs.items():
            self.bind(temp, reg)
            subEmitter.emitLoadFromStack(reg, temp)
        self.callerSavedRegs = {}

    def allocRegFor(self, temp: Temp, isRead: bool, live: set[int], subEmitter: SubroutineEmitter):
        if temp.index in self.bindings:
            return self.bindings[temp.index]

        for reg in self.emitter.allocatableRegs:
            if (not reg.occupied) or (not reg.temp.index in live):
                subEmitter.emitComment(
                    "  allocate {} to {}  (read: {}):".format(
                        str(temp), str(reg), str(isRead)
                    )
                )
                if isRead:
                    subEmitter.emitLoadFromStack(reg, temp)
                if reg.occupied:
                    self.unbind(reg.temp)
                self.bind(temp, reg)
                return reg

        reg = self.emitter.allocatableRegs[
            random.randint(0, len(self.emitter.allocatableRegs) - 1)
        ]
        subEmitter.emitStoreToStack(reg)
        subEmitter.emitComment("  spill {} ({})".format(str(reg), str(reg.temp)))
        self.unbind(reg.temp)
        self.bind(temp, reg)
        subEmitter.emitComment(
            "  allocate {} to {} (read: {})".format(str(temp), str(reg), str(isRead))
        )
        if isRead:
            subEmitter.emitLoadFromStack(reg, temp)
        return reg
