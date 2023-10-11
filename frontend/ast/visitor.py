"""
Module that defines the base type of visitor.
"""


from __future__ import annotations

from typing import Callable, Protocol, Sequence, TypeVar

from .node import *
from .tree import *

T = TypeVar("T", covariant=True)
U = TypeVar("U", covariant=True)


#! 工厂函数, visitor 表示访问者对象, ctx 表示上下文信息.
def accept(visitor: Visitor[T, U], ctx: T) -> Callable[[Node], Optional[U]]:
    return lambda node: node.accept(visitor, ctx)


class Visitor(Protocol[T, U]):  # type: ignore
    def visitOther(self, node: Node, ctx: T) -> None:
        return None

    def visitNULL(self, that: NullType, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitProgram(self, that: Program, ctx: T) -> Optional[Sequence[Optional[U]]]:
        return self.visitOther(that, ctx)

    def visitBlock(self, that: Block, ctx: T) -> Optional[Sequence[Optional[U]]]:
        return self.visitOther(that, ctx)

    def visitFunction(self, that: Function, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitParameter(self, that: Parameter, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)
    
    def visitParameterList(self, that: ParameterList, ctx: T) -> Optional[Sequence[Optional[U]]]:
        return self.visitOther(that, ctx)

    def visitIf(self, that: If, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitCall(self, that: Call, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitReturn(self, that: Return, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitWhile(self, that: While, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitFor(self, that: For, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitBreak(self, that: Break, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)
    
    def visitContinue(self, that: Continue, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitDeclaration(self, that: Declaration, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitExpressionList(self, that: ExpressionList, ctx: T) -> Optional[Sequence[Optional[U]]]:
        return self.visitOther(that, ctx)

    def visitUnary(self, that: Unary, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitBinary(self, that: Binary, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    #! Note that the default behavior is `visitBinary`, not `visitOther`    
    def visitAssignment(self, that: Assignment, ctx: T) -> Optional[U]:
        return self.visitBinary(that, ctx)

    def visitCondExpr(self, that: ConditionExpression, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitIdentifier(self, that: Identifier, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitIntLiteral(self, that: IntLiteral, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)

    def visitTInt(self, that: TInt, ctx: T) -> Optional[U]:
        return self.visitOther(that, ctx)


class RecursiveVisitor(Visitor[T, U]):
    def visitOther(self, node: Node, ctx: T) -> Optional[Sequence[Optional[U]]]:
        ret = tuple(map(accept(self, ctx), node))
        return ret if ret and ret.count(None) == len(ret) else None
