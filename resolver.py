import enum
from functools import singledispatchmethod

from common import Token, error
from expr import (Assign, Binary, Call, Expr, ExprVisitor, Get, Grouping,
                  Literal, Logical, Set, Super, This, Unary, Variable)
from interpreter import Interpreter
from stmt import (Block, Class, Expression, Function, If, Print, Return, Stmt,
                  StmtVisitor, Var, While)


class FunctionType(enum.Enum):
    NONE = enum.auto()
    FUNCTION = enum.auto()
    INITIALIZER = enum.auto()
    METHOD = enum.auto()


class ClassType(enum.Enum):
    NONE = enum.auto()
    CLASS = enum.auto()
    SUBCLASS = enum.auto()


class Resolver(StmtVisitor[None], ExprVisitor[None]):

    def __init__(self, interpreter: Interpreter):
        self.interpreter = interpreter
        self.scopes: list[dict[str, bool]] = []
        self.current_function = FunctionType.NONE
        self.current_class = ClassType.NONE

    def visit_block_stmt(self, stmt: Block) -> None:
        self._begin_scope()
        self.resolve(stmt.statements)
        self._end_scope()
        return None

    @singledispatchmethod
    def resolve(self, statements: list[Stmt]) -> None:
        for statement in statements:
            self.resolve(statement)

    @resolve.register
    def _(self, statement: Stmt) -> None:
        statement.accept(self)

    @resolve.register
    def _(self, expr: Expr) -> None:
        expr.accept(self)

    def _begin_scope(self) -> None:
        self.scopes.append(dict())

    def _end_scope(self) -> None:
        self.scopes.pop()

    def visit_var_stmt(self, stmt: Var) -> None:
        self._declare(stmt.name)
        if stmt.initializer is not None:
            self.resolve(stmt.initializer)
        self._define(stmt.name)

    def _declare(self, name: Token) -> None:
        if not self.scopes:
            return
        if name.lexeme in self.scopes[-1]:
            error(name, 'Already a variable with this name in this scope.')
        self.scopes[-1][name.lexeme] = False

    def _define(self, name: Token) -> None:
        if not self.scopes:
            return
        self.scopes[-1][name.lexeme] = True

    def visit_variable_expr(self, expr: Variable) -> None:
        if self.scopes and self.scopes[-1].get(expr.name.lexeme) == False:
            error(expr.name, 'Can\'t read local variable in its own initializer.')
        self._resolve_local(expr, expr.name)

    def _resolve_local(self, expr: Expr, name: Token) -> None:
        for i, s in reversed(list(enumerate(self.scopes))):
            if name.lexeme in s:
                self.interpreter.resolve(expr, len(self.scopes) - 1 - i)
                return

    def visit_assign_expr(self, expr: Assign) -> None:
        self.resolve(expr.value)
        self._resolve_local(expr, expr.name)

    def visit_function_stmt(self, stmt: Function) -> None:
        self._declare(stmt.name)
        self._define(stmt.name)
        self._resolve_function(stmt, FunctionType.FUNCTION)

    def _resolve_function(
            self,
            function: Function,
            function_type: FunctionType) -> None:
        enclosing_function = self.current_function
        self.current_function = function_type
        self._begin_scope()
        for param in function.params:
            self._declare(param)
            self._define(param)
        self.resolve(function.body)
        self._end_scope()
        self.current_function = enclosing_function

    def visit_expression_stmt(self, stmt: Expression) -> None:
        self.resolve(stmt.expression)

    def visit_if_stmt(self, stmt: If) -> None:
        self.resolve(stmt.condition)
        self.resolve(stmt.then_branch)
        if stmt.else_branch:
            self.resolve(stmt.else_branch)

    def visit_print_stmt(self, stmt: Print) -> None:
        self.resolve(stmt.expression)

    def visit_return_stmt(self, stmt: Return) -> None:
        if self.current_function == FunctionType.NONE:
            error(stmt.keyword, 'Can\'t return from top-level code.')
        if stmt.value:
            if self.current_function == FunctionType.INITIALIZER:
                error(
                    stmt.keyword,
                    'Can\'t return a value from an initializer.')
            self.resolve(stmt.value)

    def visit_while_stmt(self, stmt: While) -> None:
        self.resolve(stmt.condition)
        self.resolve(stmt.body)

    def visit_binary_expr(self, expr: Binary) -> None:
        self.resolve(expr.left)
        self.resolve(expr.right)

    def visit_call_expr(self, expr: Call) -> None:
        self.resolve(expr.callee)
        for argument in expr.arguments:
            self.resolve(argument)

    def visit_grouping_expr(self, expr: Grouping) -> None:
        self.resolve(expr.expression)

    def visit_literal_expr(self, expr: Literal) -> None:
        return None

    def visit_logical_expr(self, expr: Logical) -> None:
        self.resolve(expr.left)
        self.resolve(expr.right)

    def visit_unary_expr(self, expr: Unary) -> None:
        self.resolve(expr.right)

    def visit_class_stmt(self, stmt: Class) -> None:
        enclosing_class = self.current_class
        self.current_class = ClassType.CLASS
        self._declare(stmt.name)
        self._define(stmt.name)
        if stmt.superclass is not None and stmt.name.lexeme == stmt.superclass.name.lexeme:
            error(stmt.superclass.name, 'A class can\'t inherit from itself.')
        if stmt.superclass is not None:
            self.current_class = ClassType.SUBCLASS
            self.resolve(stmt.superclass)
        if stmt.superclass is not None:
            self._begin_scope()
            self.scopes[-1]['super'] = True
        self._begin_scope()
        self.scopes[-1]['this'] = True
        for method in stmt.methods:
            declaration = FunctionType.METHOD
            if method.name.lexeme == 'init':
                declaration = FunctionType.INITIALIZER
            self._resolve_function(method, declaration)
        self._end_scope()
        if stmt.superclass is not None:
            self._end_scope()
        self.current_class = enclosing_class

    def visit_get_expr(self, expr: Get) -> None:
        self.resolve(expr.obj)

    def visit_set_expr(self, expr: Set) -> None:
        self.resolve(expr.value)
        self.resolve(expr.obj)

    def visit_this_expr(self, expr: This) -> None:
        if self.current_class == ClassType.NONE:
            error(expr.keyword, 'Can\'t use "this" outside of a class.')
        self._resolve_local(expr, expr.keyword)

    def visit_super_expr(self, expr: Super) -> None:
        if self.current_class == ClassType.NONE:
            error(expr.keyword, 'Can\'t use "super" outside of a class.')
        elif self.current_class != ClassType.SUBCLASS:
            error(
                expr.keyword,
                'Can\'t use "super" in a class with no superclass.')
        self._resolve_local(expr, expr.keyword)
