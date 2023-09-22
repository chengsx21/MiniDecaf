from typing import Protocol, TypeVar

from frontend.ast.node import Node
from frontend.ast.tree import *
from frontend.ast.visitor import Visitor
from frontend.scope.globalscope import GlobalScope
from frontend.scope.scope import Scope
from frontend.type.array import ArrayType
from utils.error import *

"""
The typer phase: type check abstract syntax tree.
"""


class Typer(Visitor[Scope, None]):
    def __init__(self) -> None:
        pass

    # Entry of this phase
    def transform(self, program: Program) -> Program:
        return program
