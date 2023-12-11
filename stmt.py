from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from common import Token
from expr import Expr, Variable

_T = TypeVar('_T')


class Stmt(abc.ABC):

    @abc.abstractmethod
    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        pass


@dataclass(frozen=True)
class Expression(Stmt):
    expression: Expr

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_expression_stmt(self)


@dataclass(frozen=True)
class Print(Stmt):
    expression: Expr

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_print_stmt(self)


@dataclass(frozen=True)
class Return(Stmt):
    keyword: Token
    value: Optional[Expr]

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_return_stmt(self)


@dataclass(frozen=True)
class Var(Stmt):
    name: Token
    initializer: Optional[Expr]

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_var_stmt(self)


@dataclass(frozen=True)
class Block(Stmt):
    statements: list[Optional[Stmt]]

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_block_stmt(self)


@dataclass(frozen=True)
class If(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_if_stmt(self)


@dataclass(frozen=True)
class While(Stmt):
    condition: Expr
    body: Stmt

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_while_stmt(self)


@dataclass(frozen=True)
class Function(Stmt):
    name: Token
    params: list[Token]
    body: list[Optional[Stmt]]

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_function_stmt(self)


@dataclass(frozen=True)
class Class(Stmt):
    name: Token
    superclass: Optional[Variable]
    methods: list[Function]

    def accept(self, visitor: StmtVisitor[_T]) -> _T:
        return visitor.visit_class_stmt(self)


class StmtVisitor(Generic[_T], abc.ABC):

    @abc.abstractmethod
    def visit_expression_stmt(self, stmt: Expression) -> _T:
        pass

    @abc.abstractmethod
    def visit_print_stmt(self, stmt: Print) -> _T:
        pass

    @abc.abstractmethod
    def visit_var_stmt(self, stmt: Var) -> _T:
        pass

    @abc.abstractmethod
    def visit_if_stmt(self, stmt: If) -> _T:
        pass

    @abc.abstractmethod
    def visit_block_stmt(self, stmt: Block) -> _T:
        pass

    @abc.abstractmethod
    def visit_while_stmt(self, stmt: While) -> _T:
        pass

    @abc.abstractmethod
    def visit_function_stmt(self, stmt: Function) -> _T:
        pass

    @abc.abstractmethod
    def visit_return_stmt(self, stmt: Return) -> _T:
        pass

    @abc.abstractmethod
    def visit_class_stmt(self, stmt: Class) -> _T:
        pass
