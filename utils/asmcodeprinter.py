from utils.label.label import Label
from utils.tac.nativeinstr import NativeInstr
from utils.tac.tacinstr import TACInstr


class AsmCodePrinter:
    INDENTS = "    "
    COMMENT_PROMPT = "#"

    def __init__(self) -> None:
        self.buffer = ""

    def printf(self, fmt: str, **args):
        self.buffer += self.INDENTS + fmt.format(**args)

    def println(self, fmt: str, **args):
        self.buffer += self.INDENTS + fmt.format(**args) + "\n"

    def printLabel(self, label: Label):
        self.buffer += str(label.name) + ":\n"

    def printGlobalVar(self, symbol: str, value: int):
        self.buffer += ".globl " + symbol + "\n" + symbol + ":\n" + self.INDENTS + ".word " + str(value) + "\n"

    def printGlobalArray(self, symbol: str, value: int):
        self.buffer += ".globl " + symbol + "\n" + symbol + ":\n" + self.INDENTS + ".space " + str(value) + "\n"

    def printInstr(self, instr: NativeInstr):
        if instr.isLabel():
            self.buffer += str(instr.label) + ":"
        else:
            self.buffer += self.INDENTS + str(instr)
        self.buffer += "\n"

    def printComment(self, comment: str):
        self.buffer += self.INDENTS + self.COMMENT_PROMPT + " " + comment + "\n"

    def close(self) -> str:
        return self.buffer
