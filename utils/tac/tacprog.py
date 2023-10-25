from typing import Any, Optional, Union, Tuple, Dict

from .tacfunc import TACFunc


# A TAC program consists of several TAC functions.
class TACProg:
    def __init__(self, funcs: list[TACFunc], globalVars: Dict[str, int]) -> None:
        self.funcs = funcs
        self.globalVars = globalVars
        # print(self.globalVars)

    def printTo(self) -> None:
        for func in self.funcs:
            func.printTo()
