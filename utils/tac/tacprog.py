from frontend.ast.tree import *
from typing import Any, Optional, Union, Tuple, Dict

from .tacfunc import TACFunc


# A TAC program consists of several TAC functions.
class TACProg:
    def __init__(self, funcs: list[TACFunc], vars: Dict[str, Declaration]) -> None:
        self.funcs = funcs
        self.vars = vars

    def printTo(self) -> None:
        for func in self.funcs:
            func.printTo()
