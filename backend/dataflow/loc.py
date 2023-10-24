from utils.tac.tacinstr import TACInstr

"""
Loc: line of code
"""


class Loc:
    def __init__(self, instr: TACInstr) -> None:
        self.instr = instr
        # liveIn: set of temps that are live before this loc
        self.liveIn: set[int] = set()
        # liveOut: set of temps that are live after this loc
        self.liveOut: set[int] = set()
