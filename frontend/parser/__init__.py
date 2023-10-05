from typing import Optional, Protocol, cast

from frontend.ast.tree import Program
from frontend.lexer import Lexer
from utils.error import DecafSyntaxError

from .ply_parser import parser as _parser


class Parser(Protocol):
    '''
        描述 MiniDecaf 编译器的解析器的接口
    '''
    def __init__(self) -> None:
        self.error_stack: list[DecafSyntaxError]

    def parse(self, input: str, lexer: Optional[Lexer] = None) -> Program:
        '''
            将输入源代码解析成程序抽象语法树
        '''
        ...


parser = cast(Parser, _parser)


__all__ = [
    "parser",
]
