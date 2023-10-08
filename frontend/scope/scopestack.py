from typing import Optional

from frontend.symbol.symbol import Symbol

from .scope import Scope

from utils.error import ScopeOverflowError

class ScopeStack:
    def __init__(self, globalScope: Scope) -> None:
        self.globalScope = globalScope
        self.scopeStack = [globalScope]
        self.scopeDepth = 512

    def open(self, scope: Scope) -> None:
        if len(self.scopeStack) < self.scopeDepth:
            self.scopeStack.append(scope)
        else:
            raise ScopeOverflowError

    def close(self) -> None:
        self.scopeStack.pop()

    def top(self) -> Scope:
        if self.scopeStack:
            return self.scopeStack[len(self.scopeStack) - 1]
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
