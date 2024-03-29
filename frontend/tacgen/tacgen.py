from typing import Dict

from frontend.ast.node import Optional
from frontend.ast.tree import Function, Optional
from frontend.ast import node
from frontend.ast.tree import *
from frontend.ast.visitor import Visitor
from frontend.symbol.varsymbol import VarSymbol
from frontend.type.array import ArrayType
from utils.label.blocklabel import BlockLabel
from utils.label.funclabel import FuncLabel
from utils.tac import tacop
from utils.tac.temp import Temp
from utils.tac.tacinstr import *
from utils.tac.tacfunc import TACFunc
from utils.tac.tacprog import TACProg
from utils.tac.tacvisitor import TACVisitor

"""
The TAC generation phase: translate the abstract syntax tree into three-address code.
"""


#! 用于生成唯一的标签
class LabelManager:
    """
    A global label manager (just a counter).
    We use this to create unique (block) labels accross functions.
    """

    def __init__(self):
        self.nextTempLabelId = 0

    def freshLabel(self) -> BlockLabel:
        self.nextTempLabelId += 1
        return BlockLabel(str(self.nextTempLabelId))

#! 从一个 AST 函数生成 TAC 指令
class TACFuncEmitter(TACVisitor):
    """
    Translates a minidecaf (AST) function into low-level TAC function.
    """

    def __init__(
        self, 
        entry: FuncLabel, 
        numArgs: int, 
        arrays: Dict[str, VarSymbol], 
        p_arrays: List[VarSymbol], 
        labelManager: LabelManager
    ) -> None:
        self.labelManager = labelManager
        self.func = TACFunc(entry, numArgs, arrays, p_arrays)
        self.visitLabel(entry)
        self.nextTempId = 0

        self.continueLabelStack = []
        self.breakLabelStack = []

    # To get a fresh new temporary variable.
    def freshTemp(self) -> Temp:
        temp = Temp(self.nextTempId)
        self.nextTempId += 1
        return temp

    # To get a fresh new label (for jumping and branching, etc).
    def freshLabel(self) -> Label:
        return self.labelManager.freshLabel()

    # To count how many temporary variables have been used.
    def getUsedTemp(self) -> int:
        return self.nextTempId

    # The following methods can be named 'appendXXX' to add an instruction to the current function.
    def visitAssignment(self, dst: Temp, src: Temp) -> Temp:
        self.func.add(Assign(dst, src))
        return src

    def visitLoad(self, value: Union[int, str]) -> Temp:
        temp = self.freshTemp()
        self.func.add(LoadImm4(temp, value))
        return temp

    def visitUnary(self, op: UnaryOp, operand: Temp) -> Temp:
        temp = self.freshTemp()
        self.func.add(Unary(op, temp, operand))
        return temp

    def visitUnarySelf(self, op: UnaryOp, operand: Temp) -> None:
        self.func.add(Unary(op, operand, operand))

    def visitBinary(self, op: BinaryOp, lhs: Temp, rhs: Temp) -> Temp:
        temp = self.freshTemp()
        self.func.add(Binary(op, temp, lhs, rhs))
        return temp

    def visitBinarySelf(self, op: BinaryOp, lhs: Temp, rhs: Temp) -> None:
        self.func.add(Binary(op, lhs, lhs, rhs))

    def visitBranch(self, target: Label) -> None:
        self.func.add(Branch(target))

    def visitCondBranch(self, op: CondBranchOp, cond: Temp, target: Label) -> None:
        self.func.add(CondBranch(op, cond, target))

    def visitParam(self, value: Temp) -> None:
        self.func.add(Param(value))

    def visitCall(self, label: Label) -> Temp:
        temp = self.freshTemp()
        self.func.add(Call(temp, label))
        return temp

    def visitReturn(self, value: Optional[Temp]) -> None:
        self.func.add(Return(value))

    def visitLabel(self, label: Label) -> None:
        self.func.add(Mark(label))

    def visitLoadAddress(self, symbol: VarSymbol):
        addr = self.freshTemp()
        self.func.add(LoadAddress(symbol, addr))
        return addr

    def visitLoadIntLiteral(self, symbol: VarSymbol, offset: int = 0) -> Temp:
        addr = self.visitLoadAddress(symbol)
        self.func.add(LoadIntLiteral(addr, addr, offset))
        return addr

    def visitLoadByAddress(self, addr: Temp):
        dst = self.freshTemp()
        self.func.add(LoadIntLiteral(dst, addr, 0))
        return dst

    def visitStoreIntLiteral(self, symbol: VarSymbol, value: Temp, offset: int = 0) -> None:
        addr = self.visitLoadAddress(symbol)
        self.func.add(StoreIntLiteral(value, addr, offset))

    def visitStoreByAddress(self, value: Temp, addr: Temp):
        self.func.add(StoreIntLiteral(value, addr, 0))

    def visitMemo(self, content: str) -> None:
        self.func.add(Memo(content))

    def visitRaw(self, instr: TACInstr) -> None:
        self.func.add(instr)

    def visitEnd(self) -> TACFunc:
        if (len(self.func.instrSeq) == 0) or (not self.func.instrSeq[-1].isReturn()):
            self.func.add(Return(None))
        self.func.tempUsed = self.getUsedTemp()
        return self.func

    # To open a new loop (for break/continue statements)
    def openLoop(self, breakLabel: Label, continueLabel: Label) -> None:
        self.breakLabelStack.append(breakLabel)
        self.continueLabelStack.append(continueLabel)

    # To close the current loop.
    def closeLoop(self) -> None:
        self.breakLabelStack.pop()
        self.continueLabelStack.pop()

    # To get the label for 'break' in the current loop.
    def getBreakLabel(self) -> Label:
        return self.breakLabelStack[-1]

    # To get the label for 'continue' in the current loop.
    def getContinueLabel(self) -> Label:
        return self.continueLabelStack[-1]


class TACGen(Visitor[TACFuncEmitter, None]):
    # Entry of this phase
    def transform(self, program: Program) -> TACProg:
        labelManager = LabelManager()
        tacFuncs = []
        tacGlobalVars = program.globalVars()
        for funcName, astFunc in program.functions().items():
            # in step9, you need to use real parameter count
            emitter = TACFuncEmitter(FuncLabel(funcName), len(astFunc.params.children), astFunc.arrays, astFunc.p_arrays, labelManager)
            for child in astFunc.params.children:
                child.accept(self, emitter)
            astFunc.body.accept(self, emitter)
            tacFuncs.append(emitter.visitEnd())
        return TACProg(tacFuncs, tacGlobalVars)

    def visitBlock(self, block: Block, mv: TACFuncEmitter) -> None:
        for child in block:
            child.accept(self, mv)

    def visitParameter(self, param: Parameter, mv: TACFuncEmitter) -> None:
        param.getattr('symbol').temp = mv.freshTemp()

    def visitCall(self, call: Call, mv: TACFuncEmitter) -> None:
        for arg in call.args.children:
            arg.accept(self, mv)
        for arg in call.args.children:
            mv.visitParam(arg.getattr("val"))
        call.setattr('val', mv.visitCall(FuncLabel(call.ident.value)))

    def visitReturn(self, stmt: Return, mv: TACFuncEmitter) -> None:
        stmt.expr.accept(self, mv)
        mv.visitReturn(stmt.expr.getattr("val"))

    def visitBreak(self, stmt: Break, mv: TACFuncEmitter) -> None:
        mv.visitBranch(mv.getBreakLabel())
        
    def visitContinue(self, stmt: Continue, mv: TACFuncEmitter) -> None:
        mv.visitBranch(mv.getContinueLabel())

    def visitIdentifier(self, ident: Identifier, mv: TACFuncEmitter) -> None:
        symbol = ident.getattr('symbol')
        if isinstance(symbol.type, ArrayType):
            if symbol.isGlobal or symbol not in mv.func.p_arrays:
                ident.setattr('addr', mv.visitLoadAddress(symbol))
            else:
                ident.setattr('addr', symbol.temp)
            ident.setattr('val', ident.getattr('addr'))
        elif symbol.isGlobal:
            ident.setattr('val', mv.visitLoadIntLiteral(symbol))
        else:
            ident.setattr('val', symbol.temp)
        # 设置返回值为标识符对应的 temp 寄存器

    def visitDeclaration(self, decl: Declaration, mv: TACFuncEmitter) -> None:
        decl.getattr("symbol").temp = mv.freshTemp()
        if decl.init_expr:
            if isinstance(decl.init_expr, InitList):
                #! 调用 `fill_csx` 函数进行初始化
                symbol = decl.getattr("symbol")
                addr = mv.visitLoadAddress(symbol)
                size = symbol.type.full_indexed.size
                interval = mv.visitLoad(size)
                mv.visitParam(addr)
                mv.visitParam(mv.visitLoad(symbol.type.size // size))               
                mv.visitCall(FuncLabel("fill_csx"))
                #! 依次将初始化列表中的值存入数组中
                for value in decl.init_expr.value:
                    mv.visitStoreByAddress(mv.visitLoad(value), addr)
                    mv.visitBinarySelf(tacop.TacBinaryOp.ADD, addr, interval)
            else:
                #! 对子节点进行 accept
                decl.init_expr.accept(self, mv)
                #! 模仿 `visitAssignment` 函数进行赋值
                decl.setattr(
                    "val", mv.visitAssignment(decl.getattr("symbol").temp, decl.init_expr.getattr("val"))
                )            

    def visitIndexExpr(self, expr: IndexExpr, mv: TACFuncEmitter) -> None:
        expr.base.setattr('slice', True)
        expr.base.accept(self, mv)
        expr.index.accept(self, mv)
        #! 递归计算偏移量
        addr = mv.visitLoad(expr.getattr('type').size)
        mv.visitBinarySelf(tacop.TacBinaryOp.MUL, addr, expr.index.getattr('val'))
        mv.visitBinarySelf(tacop.TacBinaryOp.ADD, addr, expr.base.getattr('addr'))
        expr.setattr('addr', addr)
        #! 递归计算完毕, 计算数组元素值
        if not expr.getattr('slice'):
            expr.setattr('val', mv.visitLoadByAddress(addr))

    def visitAssignment(self, expr: Assignment, mv: TACFuncEmitter) -> None:
        #! 对右值进行 accept
        expr.rhs.accept(self, mv)
        #! 左值是数组元素
        if isinstance(expr.lhs, IndexExpr):
            expr.lhs.setattr('slice', True)
            expr.lhs.accept(self, mv)
            mv.visitStoreByAddress(expr.rhs.getattr('val'), expr.lhs.getattr('addr'))
        #! 左值是全局变量
        elif expr.lhs.getattr('symbol').isGlobal:
            mv.visitStoreIntLiteral(expr.lhs.getattr('symbol'), expr.rhs.getattr("val"))
        else:
            expr.lhs.accept(self, mv)
            #! 设置返回值为赋值指令的返回值, 赋值操作更新左值, 左端项是左值 temp
            mv.visitAssignment(expr.lhs.getattr("symbol").temp, expr.rhs.getattr("val"))
        expr.setattr('val', expr.rhs.getattr("val"))

    def visitIf(self, stmt: If, mv: TACFuncEmitter) -> None:
        stmt.cond.accept(self, mv)

        if stmt.otherwise is NULL:
            skipLabel = mv.freshLabel()
            mv.visitCondBranch(
                tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), skipLabel
            )
            stmt.then.accept(self, mv)
            mv.visitLabel(skipLabel)
        else:
            skipLabel = mv.freshLabel()
            exitLabel = mv.freshLabel()
            mv.visitCondBranch(
                tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), skipLabel
            )
            stmt.then.accept(self, mv)
            mv.visitBranch(exitLabel)
            mv.visitLabel(skipLabel)
            stmt.otherwise.accept(self, mv)
            mv.visitLabel(exitLabel)

    def visitWhile(self, stmt: While, mv: TACFuncEmitter) -> None:
        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        mv.openLoop(breakLabel, loopLabel)

        mv.visitLabel(beginLabel)
        stmt.cond.accept(self, mv)
        mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)

        stmt.body.accept(self, mv)
        mv.visitLabel(loopLabel)
        mv.visitBranch(beginLabel)
        mv.visitLabel(breakLabel)
        mv.closeLoop()

    def visitFor(self, stmt: For, mv: TACFuncEmitter) -> None:
        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        mv.openLoop(breakLabel, loopLabel)

        stmt.init.accept(self, mv)
        mv.visitLabel(beginLabel)
        #! cond 可能为空
        if stmt.cond:
            stmt.cond.accept(self, mv)
            mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)

        stmt.body.accept(self, mv)
        mv.visitLabel(loopLabel)
        stmt.update.accept(self, mv)
        mv.visitBranch(beginLabel)
        mv.visitLabel(breakLabel)
        mv.closeLoop()

    def visitUnary(self, expr: Unary, mv: TACFuncEmitter) -> None:
        expr.operand.accept(self, mv)
        op = {
            node.UnaryOp.Neg: tacop.TacUnaryOp.NEG,
            node.UnaryOp.BitNot: tacop.TacUnaryOp.BIT_NOT,
            node.UnaryOp.LogicNot: tacop.TacUnaryOp.LOGIC_NOT,
            # You can add unary operations here.
        }[expr.op]
        expr.setattr("val", mv.visitUnary(op, expr.operand.getattr("val")))

    def visitBinary(self, expr: Binary, mv: TACFuncEmitter) -> None:
        expr.lhs.accept(self, mv)
        expr.rhs.accept(self, mv)
        op = {
            node.BinaryOp.Add: tacop.TacBinaryOp.ADD,
            node.BinaryOp.Sub: tacop.TacBinaryOp.SUB,
            node.BinaryOp.Mul: tacop.TacBinaryOp.MUL,
            node.BinaryOp.Div: tacop.TacBinaryOp.DIV,
            node.BinaryOp.Mod: tacop.TacBinaryOp.MOD,
            node.BinaryOp.LogicOr: tacop.TacBinaryOp.LOR,
            node.BinaryOp.LogicAnd: tacop.TacBinaryOp.LAND,
            node.BinaryOp.EQ: tacop.TacBinaryOp.EQU,
            node.BinaryOp.NE: tacop.TacBinaryOp.NEQ,
            node.BinaryOp.LT: tacop.TacBinaryOp.SLT,
            node.BinaryOp.GT: tacop.TacBinaryOp.SGT,
            node.BinaryOp.LE: tacop.TacBinaryOp.LEQ,
            node.BinaryOp.GE: tacop.TacBinaryOp.GEQ,
            # You can add binary operations here.
        }[expr.op]
        expr.setattr(
            "val", mv.visitBinary(op, expr.lhs.getattr("val"), expr.rhs.getattr("val"))
        )

    def visitCondExpr(self, expr: ConditionExpression, mv: TACFuncEmitter) -> None:
        expr.cond.accept(self, mv)
        skipLabel = mv.freshLabel()
        exitLabel = mv.freshLabel()
        exprVal = expr.cond.getattr("val")
        mv.visitCondBranch(
            tacop.CondBranchOp.BEQ, exprVal, skipLabel
        )
        expr.then.accept(self, mv)
        mv.visitAssignment(exprVal, expr.then.getattr("val"))
        mv.visitBranch(exitLabel)
        mv.visitLabel(skipLabel)
        expr.otherwise.accept(self, mv)
        mv.visitAssignment(exprVal, expr.otherwise.getattr("val"))
        mv.visitLabel(exitLabel)
        expr.setattr("val", exprVal)

    def visitIntLiteral(self, expr: IntLiteral, mv: TACFuncEmitter) -> None:
        expr.setattr("val", mv.visitLoad(expr.value))
