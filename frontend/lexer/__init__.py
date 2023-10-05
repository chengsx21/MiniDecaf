from __future__ import annotations

from typing import Iterator, Protocol, Union

import frontend.ast.node as node
from utils.error import DecafLexError

from . import lex

# * replace the '.ply-lexer' by '.xxx' to use your own-defined lexer, where 'xxx' is the module/package name of it
# * note that your lexer should be iterable, and should have the method 'input' in order to accept the input source file
from .ply_lexer import lexer as ply_lexer


class LexToken(Protocol):
    '''
        词法分析器生成的词法单元
    '''
    def __init__(self) -> None:
        self.type: str
        self.value: Union[str, node.Node] # 字符串或 AST 节点
        self.lineno: int # 源文件行号
        self.lexpos: int # 源文件位置
        self.lexer: Lexer

    def __str__(self) -> str:
        ...

    def __repr__(self) -> str:
        ...


class Lexer(Protocol):
    '''
        描述词法分析器本身
    '''
    def __init__(self) -> None:
        self.lexdata: str # 词法分析器的输入源代码
        self.lexpos: int
        self.lineno: int

        self.error_stack: list[DecafLexError] # 存储词法分析错误的列表

    def input(self, s: str) -> None:
        '''
            输入源代码传递给词法分析器
        '''
        ...

    def token(self) -> LexToken:
        '''
            生成下一个词法单元
        '''
        ...

    def __iter__(self) -> Iterator[LexToken]:
        ...

    def __next__(self) -> LexToken:
        ...


lexer: Lexer = ply_lexer

__all__ = [
    "lexer",
    "lex",
    "LexToken",
    "Lexer",
    "ply_lexer",
]
