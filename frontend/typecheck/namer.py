from typing import Protocol, TypeVar, cast

from frontend.ast.node import Node, NullType
from frontend.ast.tree import *
from frontend.ast.visitor import RecursiveVisitor, Visitor
from frontend.scope.globalscope import GlobalScope
from frontend.scope.scope import Scope, ScopeKind
from frontend.scope.scopestack import ScopeStack
from frontend.symbol.funcsymbol import FuncSymbol
from frontend.symbol.symbol import Symbol
from frontend.symbol.varsymbol import VarSymbol
from frontend.type.array import ArrayType
from frontend.type.type import DecafType
from utils.error import *
from utils.riscv import MAX_INT

"""
The namer phase: resolve all symbols defined in the abstract 
syntax tree and store them in symbol tables (i.e. scopes).
"""


class Namer(Visitor[ScopeStack, None]):
    def __init__(self) -> None:
        self.arrays = []

    # Entry of this phase
    def transform(self, program: Program) -> Program:
        program.globalScope = GlobalScope
        ctx = ScopeStack(program.globalScope)

        program.accept(self, ctx)
        return program

    def visitProgram(self, program: Program, ctx: ScopeStack) -> None:
        #! Check if the 'main' function is missing
        if not program.hasMainFunc():
            raise DecafNoMainFuncError()

        for func in program.children:
            func.accept(self, ctx)

    def visitFunction(self, func: Function, ctx: ScopeStack) -> None:
        if GlobalScope.lookup(func.ident.value):
            raise DecafDeclConflictError(func.ident.value)
        symbol = FuncSymbol(func.ident.value, func.ret_t.type, GlobalScope)
        for param in func.params.children:
            symbol.addParaType(param.var_t)
        GlobalScope.declare(symbol)
        func.setattr('symbol', symbol)

        ctx.open()
        self.arrays = []
        func.params.accept(self, ctx)
        for child in func.body.children:
            child.accept(self, ctx)
        func.arrays = self.arrays
        ctx.close()

    def visitBlock(self, block: Block, ctx: ScopeStack) -> None:
        ctx.open()
        for child in block:
            child.accept(self, ctx)
        ctx.close()

    def visitParameter(self, param: Parameter, ctx: ScopeStack) -> None:
        if ctx.lookup(param.ident.value):
            raise DecafDeclConflictError(param.ident.value)
        symbol = VarSymbol(param.ident.value, param.var_t.type)
        ctx.declare(symbol)
        param.setattr("symbol", symbol)

    def visitParameterList(self, params: ParameterList, ctx: ScopeStack) -> None:
        for param in params.children:
            param.accept(self, ctx)

    def visitExpressionList(self, exprs: ExpressionList, ctx: ScopeStack) -> None:
        for expr in exprs.children:
            expr.accept(self, ctx)

    def visitCall(self, call: Call, ctx: ScopeStack) -> None:
        if ctx.lookup(call.ident.value):
            raise DecafBadFuncCallError(call.ident.value)

        func = GlobalScope.lookup(call.ident.value)
        if not func or not func.isFunc:
            raise DecafUndefinedFuncError(call.ident.value)
        if func.parameterNum != len(call.args):
            raise DecafBadFuncCallError(call.ident.value)

        call.ident.setattr('symbol', func)
        for arg in call.args:
            arg.accept(self, ctx)

    def visitReturn(self, stmt: Return, ctx: ScopeStack) -> None:
        stmt.expr.accept(self, ctx)

    def visitFor(self, stmt: For, ctx: ScopeStack) -> None:
        ctx.open()
        stmt.init.accept(self, ctx)
        stmt.cond.accept(self, ctx)
        stmt.update.accept(self, ctx)
        #! check the validity of `Break` or `Continue`
        ctx.enterLoop()
        stmt.body.accept(self, ctx)
        ctx.exitLoop()
        ctx.close()

    def visitIf(self, stmt: If, ctx: ScopeStack) -> None:
        stmt.cond.accept(self, ctx)
        stmt.then.accept(self, ctx)

        # check if the else branch exists
        if not stmt.otherwise is NULL:
            stmt.otherwise.accept(self, ctx)

    def visitWhile(self, stmt: While, ctx: ScopeStack) -> None:
        stmt.cond.accept(self, ctx)
        ctx.enterLoop()
        stmt.body.accept(self, ctx)
        ctx.exitLoop()

    def visitBreak(self, stmt: Break, ctx: ScopeStack) -> None:
        if not ctx.insideLoop():
            raise DecafBreakOutsideLoopError()
        ctx.exitLoop()

    def visitContinue(self, stmt: Continue, ctx: ScopeStack) -> None:
        if not ctx.insideLoop():
            raise DecafContinueOutsideLoopError()

    def visitDeclaration(self, decl: Declaration, ctx: ScopeStack) -> None:
        #! decl.ident.value 是变量名字符串
        if ctx.lookup(decl.ident.value):
            raise DecafDeclConflictError(decl.ident.value)
        if decl.init_dim:
            decl_type = ArrayType.multidim(decl.var_t.type, *[dim.value for dim in decl.init_dim])
            symbol = VarSymbol(decl.ident.value, decl_type)
            self.arrays.append(symbol)
        else:
            decl_type = decl.var_t.type
            symbol = VarSymbol(decl.ident.value, decl_type)
        if ctx.isGlobalScope():
            symbol.isGlobal = True
            if decl.init_expr:
                symbol.initValue = decl.init_expr.value
        ctx.declare(symbol)
        decl.setattr("symbol", symbol)
        if decl.init_expr:
            decl.init_expr.accept(self, ctx)

    def visitIndexExpr(self, expr: IndexExpr, ctx: ScopeStack) -> None:
        if isinstance(expr.base, Identifier) and not ctx.lookupOverStack(expr.base.value):
            raise DecafUndefinedVarError(expr.base.value)
        expr.base.accept(self, ctx)
        expr.index.accept(self, ctx)
        #! 根据 base 类型设置 expr 的类型
        if isinstance(expr.base, Identifier):
            expr.setattr('type', expr.base.getattr('symbol').type.indexed)
        else:
            expr.setattr('type', expr.base.getattr('type').indexed)

    def visitAssignment(self, expr: Assignment, ctx: ScopeStack) -> None:
        self.visitBinary(expr, ctx)

    def visitUnary(self, expr: Unary, ctx: ScopeStack) -> None:
        expr.operand.accept(self, ctx)

    def visitBinary(self, expr: Binary, ctx: ScopeStack) -> None:
        expr.lhs.accept(self, ctx)
        expr.rhs.accept(self, ctx)

    def visitCondExpr(self, expr: ConditionExpression, ctx: ScopeStack) -> None:
        expr.cond.accept(self, ctx)
        expr.then.accept(self, ctx)
        expr.otherwise.accept(self, ctx)

    def visitIdentifier(self, ident: Identifier, ctx: ScopeStack) -> None:
        symbol = ctx.lookupOverStack(ident.value)
        if not symbol:
            raise DecafUndefinedVarError(ident.value)
        ident.setattr("symbol", symbol)

    def visitIntLiteral(self, expr: IntLiteral, ctx: ScopeStack) -> None:
        value = expr.value
        if value > MAX_INT:
            raise DecafBadIntValueError(value)
