from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from common import Token

_T = TypeVar('_T')


class Expr(abc.ABC):

    @abc.abstractmethod
    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        pass


@dataclass(frozen=True)
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_binary_expr(self)


@dataclass(frozen=True)
class Grouping(Expr):
    expression: Expr

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_grouping_expr(self)


@dataclass(frozen=True)
class Literal(Expr):
    value: Any

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_literal_expr(self)


@dataclass(frozen=True)
class Unary(Expr):
    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_unary_expr(self)


@dataclass(frozen=True)
class Variable(Expr):
    name: Token

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_variable_expr(self)


@dataclass(frozen=True)
class Assign(Expr):
    name: Token
    value: Expr

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_assign_expr(self)


@dataclass(frozen=True)
class Call(Expr):
    callee: Expr
    paren: Token
    arguments: list[Expr]

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_call_expr(self)


@dataclass(frozen=True)
class Logical(Expr):
    left: Expr
    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_logical_expr(self)


@dataclass(frozen=True)
class Get(Expr):
    obj: Expr
    name: Token

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_get_expr(self)


@dataclass(frozen=True)
class Set(Expr):
    obj: Expr
    name: Token
    value: Expr

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_set_expr(self)


@dataclass(frozen=True)
class This(Expr):
    keyword: Token

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_this_expr(self)


@dataclass(frozen=True)
class Super(Expr):
    keyword: Token
    method: Token

    def accept(self, visitor: ExprVisitor[_T]) -> _T:
        return visitor.visit_super_expr(self)


class ExprVisitor(Generic[_T], abc.ABC):

    @abc.abstractmethod
    def visit_binary_expr(self, expr: Binary) -> _T:
        pass

    @abc.abstractmethod
    def visit_grouping_expr(self, expr: Grouping) -> _T:
        pass

    @abc.abstractmethod
    def visit_literal_expr(self, expr: Literal) -> _T:
        pass

    @abc.abstractmethod
    def visit_variable_expr(self, expr: Variable) -> _T:
        pass

    @abc.abstractmethod
    def visit_unary_expr(self, expr: Unary) -> _T:
        pass

    @abc.abstractmethod
    def visit_assign_expr(self, expr: Assign) -> _T:
        pass

    @abc.abstractmethod
    def visit_logical_expr(self, expr: Logical) -> _T:
        pass

    @abc.abstractmethod
    def visit_call_expr(self, expr: Call) -> _T:
        pass

    @abc.abstractmethod
    def visit_get_expr(self, expr: Get) -> _T:
        pass

    @abc.abstractmethod
    def visit_set_expr(self, expr: Set) -> _T:
        pass

    @abc.abstractmethod
    def visit_this_expr(self, expr: This) -> _T:
        pass

    @abc.abstractmethod
    def visit_super_expr(self, expr: Super) -> _T:
        pass
