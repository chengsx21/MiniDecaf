from typing import Optional

from frontend.symbol.symbol import Symbol

from .scope import Scope, ScopeKind

from utils.error import ScopeOverflowError

class ScopeStack:
    def __init__(self, globalScope: Scope) -> None:
        self.globalScope = globalScope
        self.scopeStack = [globalScope]
        self.scopeCount = 512
        self.loopCount = 0

    def open(self) -> None:
        if len(self.scopeStack) < self.scopeCount:
            self.scopeStack.append(Scope(ScopeKind.LOCAL))
        else:
            raise ScopeOverflowError

    def close(self) -> None:
        self.scopeStack.pop()

    def top(self) -> Scope:
        if self.scopeStack:
            return self.scopeStack[- 1]
        return self.globalScope

    def isGlobalScope(self) -> bool:
        return self.top().isGlobalScope()

    def declare(self, symbol: Symbol) -> None:
        self.top().declare(symbol)

    def lookup(self, name: str) -> Optional[Symbol]:
        return self.top().lookup(name)
    
    def lookupOverStack(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopeStack):
            if scope.containsKey(name):
                return scope.get(name)
        return None
    
    def enterLoop(self) -> None:
        self.loopCount += 1

    def exitLoop(self) -> None:
        self.loopCount -= 1

    def insideLoop(self) -> None:
        return self.loopCount
