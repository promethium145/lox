from __future__ import annotations

import time
from typing import Any, Optional

from common import LoxRuntimeError, Token, TokenType, runtime_error
from expr import (Assign, Binary, Call, Expr, ExprVisitor, Get, Grouping,
                  Literal, Logical, Set, Super, This, Unary, Variable)
from stmt import (Block, Class, Expression, Function, If, Print, Return, Stmt,
                  StmtVisitor, Var, While)


class Environment:

    def __init__(self, enclosing: Optional[Environment] = None):
        self.enclosing = enclosing
        self.values: dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def get(self, name: Token) -> Any:
        try:
            return self.values[name.lexeme]
        except KeyError:
            if self.enclosing is not None:
                return self.enclosing.get(name)
            else:
                raise LoxRuntimeError(
                    name, f'Undefined variable {name.lexeme}.')

    def assign(self, name: Token, value: Any) -> None:
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return
        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return
        raise LoxRuntimeError(name, f'Undefined variable "{name.lexeme}".')

    def get_at(self, distance: int, name: str) -> Any:
        return self._ancestor(distance).values.get(name)

    def _ancestor(self, distance: int) -> Environment:
        environment = self
        for i in range(distance):
            assert environment.enclosing is not None
            environment = environment.enclosing
        return environment

    def assign_at(self, distance: int, name: Token, value: Any) -> None:
        self._ancestor(distance).values[name.lexeme] = value


class LoxCallable:

    def call(self, interpreter: Interpreter, arguments: list[Any]) -> Any:
        pass

    def arity(self) -> int:
        pass


class LoxReturn(RuntimeError):

    def __init__(self, value: Any):
        self.value = value
        super().__init__(None)


class LoxFunction(LoxCallable):
    def __init__(
            self,
            declaration: Function,
            closure: Environment,
            is_initializer: bool):
        self.declaration = declaration
        self.closure = closure
        self.is_initializer = is_initializer

    def call(self, interpreter: Interpreter, arguments: list[Any]) -> Any:
        environment = Environment(self.closure)
        for i, param in enumerate(self.declaration.params):
            environment.define(param.lexeme, arguments[i])
        try:
            interpreter._execute_block(self.declaration.body, environment)
        except LoxReturn as r:
            if self.is_initializer:
                return self.closure.get_at(0, 'this')
            return r.value
        if self.is_initializer:
            return self.closure.get_at(0, 'this')
        return None

    def bind(self, instance: LoxInstance) -> LoxFunction:
        environment = Environment(self.closure)
        environment.define('this', instance)
        return LoxFunction(self.declaration, environment, self.is_initializer)

    def arity(self) -> int:
        return len(self.declaration.params)

    def __str__(self) -> str:
        return f'<fn {self.declaration.name.lexeme}>'


class ClockFunction(LoxCallable):

    def arity(self) -> int:
        return 0

    def call(self, interpreter: Interpreter, arguments: list[Any]) -> Any:
        return time.time()


class LoxClass(LoxCallable):

    def __init__(self,
                 name: str,
                 superclass: Optional[LoxClass],
                 methods: dict[str,
                               LoxFunction]):
        self.name = name
        self.superclass = superclass
        self.methods = methods

    def find_method(self, name: str) -> Optional[LoxFunction]:
        if name in self.methods:
            return self.methods[name]
        return None

    def __str__(self) -> str:
        return self.name

    def call(self, interpreter: Interpreter, arguments: list[Any]) -> Any:
        instance = LoxInstance(self)
        initializer = self.find_method('init')
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
        return instance

    def arity(self) -> int:
        initializer = self.find_method('init')
        if initializer is None:
            return 0
        return initializer.arity()


class LoxInstance:

    def __init__(self, klass: LoxClass):
        self.klass = klass
        self.fields: dict[str, Any] = {}

    def __str__(self) -> str:
        return f'{self.klass.name} instance'

    def get(self, name: Token) -> Any:
        if name.lexeme in self.fields:
            return self.fields.get(name.lexeme)
        method = self.klass.find_method(name.lexeme)
        if method is not None:
            return method.bind(self)

        raise LoxRuntimeError(name, f'Undefined property "{name.lexeme}".')

    def set(self, name: Token, value: Any) -> None:
        self.fields[name.lexeme] = value


class Interpreter(ExprVisitor[Any], StmtVisitor[None]):

    def __init__(self):
        self.globals = Environment()
        self.environment = self.globals
        self.globals.define('clock', ClockFunction)
        self.locals: dict[Expr, int] = {}

    def interpret(self, statements: list[Optional[Stmt]]) -> None:
        try:
            for stmt in statements:
                assert stmt is not None
                self._execute(stmt)
        except LoxRuntimeError as e:
            runtime_error(e)

    def _execute(self, stmt: Stmt) -> None:
        stmt.accept(self)

    def resolve(self, expr: Expr, depth: int) -> None:
        self.locals[expr] = depth

    def _stringify(self, obj: Any) -> str:
        if obj is None:
            return 'nil'
        if isinstance(obj, bool):
            return str(obj).lower()
        if isinstance(obj, float):
            text = str(obj)
            if text.endswith('.0'):
                text = text[0:len(text) - 2]
            return text
        return str(obj)

    def visit_expression_stmt(self, stmt: Expression) -> None:
        self._evaluate(stmt.expression)

    def visit_print_stmt(self, stmt: Print) -> None:
        value = self._evaluate(stmt.expression)
        print(self._stringify(value))

    def visit_var_stmt(self, stmt: Var) -> None:
        if stmt.initializer is not None:
            value = self._evaluate(stmt.initializer)
        else:
            value = None
        self.environment.define(stmt.name.lexeme, value)

    def visit_block_stmt(self, stmt: Block) -> None:
        self._execute_block(stmt.statements, Environment(self.environment))

    def visit_class_stmt(self, stmt: Class) -> None:
        superclass = None
        if stmt.superclass is not None:
            superclass = self._evaluate(stmt.superclass)
            if not isinstance(superclass, LoxClass):
                raise LoxRuntimeError(
                    stmt.superclass.name, 'Superclass must be a class.')
        self.environment.define(stmt.name.lexeme, None)
        if stmt.superclass is not None:
            self.environment = Environment(self.environment)
            self.environment.define('super', superclass)
        methods = {}
        for method in stmt.methods:
            function = LoxFunction(
                method, self.environment, method.name.lexeme == 'init')
            methods[method.name.lexeme] = function
        klass = LoxClass(stmt.name.lexeme, superclass, methods)
        if superclass is not None:
            self.environment = self.environment.enclosing
        self.environment.assign(stmt.name, klass)

    def visit_if_stmt(self, stmt: If) -> None:
        if self._is_truthy(self._evaluate(stmt.condition)):
            self._execute(stmt.then_branch)
        elif stmt.else_branch is not None:
            self._execute(stmt.else_branch)

    def visit_while_stmt(self, stmt: While) -> None:
        while self._is_truthy(self._evaluate(stmt.condition)):
            self._execute(stmt.body)

    def visit_function_stmt(self, stmt: Function) -> None:
        function = LoxFunction(stmt, self.environment, False)
        self.environment.define(stmt.name.lexeme, function)
        return None

    def visit_return_stmt(self, stmt: Return) -> None:
        if stmt.value is not None:
            value = self._evaluate(stmt.value)
        else:
            value = None
        raise LoxReturn(value)

    def _execute_block(self,
                       statements: list[Optional[Stmt]],
                       environment: Environment) -> None:
        previous = self.environment
        try:
            self.environment = environment
            for stmt in statements:
                assert stmt is not None
                self._execute(stmt)
        finally:
            self.environment = previous

    def visit_assign_expr(self, expr: Assign) -> Any:
        value = self._evaluate(expr.value)
        distance = self.locals.get(expr)
        if distance is not None:
            self.environment.assign_at(distance, expr.name, value)
        else:
            self.globals.assign(expr.name, value)
        return value

    def visit_variable_expr(self, expr: Variable) -> Any:
        return self._lookup_variable(expr.name, expr)

    def _lookup_variable(self, name: Token, expr: Expr) -> Any:
        distance = self.locals.get(expr)
        if distance is not None:
            return self.environment.get_at(distance, name.lexeme)
        else:
            return self.globals.get(name)

    def visit_literal_expr(self, expr: Literal) -> Any:
        return expr.value

    def visit_grouping_expr(self, expr: Grouping) -> Any:
        return self._evaluate(expr.expression)

    def visit_unary_expr(self, expr: Unary) -> Any:
        right = self._evaluate(expr.right)
        if expr.operator.token_type == TokenType.MINUS:
            self._check_number_operand(expr.operator, right)
            return -right
        if expr.operator.token_type == TokenType.BANG:
            return not self._is_truthy(right)
        # Unreachable
        return None

    def _check_number_operand(self, operator: Token, operand: Any) -> None:
        if isinstance(operand, float):
            return
        raise LoxRuntimeError(operator, 'Operand must be a number.')

    def visit_logical_expr(self, expr: Logical) -> Any:
        left = self._evaluate(expr.left)
        if expr.operator.token_type == TokenType.OR:
            if self._is_truthy(left):
                return left
        else:
            if not self._is_truthy(left):
                return left
        return self._evaluate(expr.right)

    def visit_binary_expr(self, expr: Binary) -> Any:
        left = self._evaluate(expr.left)
        right = self._evaluate(expr.right)

        def _is_tt(t: TokenType) -> bool:
            return expr.operator.token_type == t

        if _is_tt(TokenType.MINUS):
            self._check_number_operands(expr.operator, left, right)
            return left - right
        if _is_tt(TokenType.STAR):
            self._check_number_operands(expr.operator, left, right)
            return left * right
        if _is_tt(TokenType.SLASH):
            self._check_number_operands(expr.operator, left, right)
            if right == 0:
                raise LoxRuntimeError(expr.operator, 'Division by zero error.')
            return left / right
        if _is_tt(TokenType.PLUS):
            if isinstance(left, float) and isinstance(right, float):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise LoxRuntimeError(
                expr.operator, 'Operands must be two numbers or two strings.')
            return left + right
        if _is_tt(TokenType.GREATER):
            self._check_number_operands(expr.operator, left, right)
            return left > right
        if _is_tt(TokenType.GREATER_EQUAL):
            self._check_number_operands(expr.operator, left, right)
            return left >= right
        if _is_tt(TokenType.LESS):
            self._check_number_operands(expr.operator, left, right)
            return left < right
        if _is_tt(TokenType.LESS_EQUAL):
            self._check_number_operands(expr.operator, left, right)
            return left <= right
        if _is_tt(TokenType.BANG_EQUAL):
            self._check_number_operands(expr.operator, left, right)
            return left != right
        if _is_tt(TokenType.EQUAL_EQUAL):
            self._check_number_operands(expr.operator, left, right)
            return left == right

        # Unreachable.
        assert False

    def visit_call_expr(self, expr: Call) -> Any:
        callee = self._evaluate(expr.callee)
        arguments: list[Any] = []
        for argument in expr.arguments:
            arguments.append(self._evaluate(argument))
        if not isinstance(callee, LoxCallable):
            raise LoxRuntimeError(
                expr.paren, 'Can only call functions and classes.')
        if len(arguments) != callee.arity():
            raise LoxRuntimeError(
                expr.paren,
                f'Expected {callee.arity()} arguments but got {len(arguments)}.')
        return callee.call(self, arguments)

    def visit_get_expr(self, expr: Get) -> Any:
        obj = self._evaluate(expr.obj)
        if isinstance(obj, LoxInstance):
            return obj.get(expr.name)
        raise LoxRuntimeError(expr.name, 'Only instances have properties.')

    def visit_set_expr(self, expr: Set) -> Any:
        obj = self._evaluate(expr.obj)
        if not isinstance(obj, LoxInstance):
            raise LoxRuntimeError(expr.name, 'Only instances have fields.')
        value = self._evaluate(expr.value)
        obj.set(expr.name, value)
        return value

    def visit_this_expr(self, expr: This) -> Any:
        return self._lookup_variable(expr.keyword, expr)

    def visit_super_expr(self, expr: Super) -> Any:
        distance = self.locals[expr]
        superclass = self.environment.get_at(distance, 'super')
        obj = self.environment.get_at(distance - 1, 'this')
        method = superclass.find_method(expr.method.lexeme)
        if method is None:
            raise LoxRuntimeError(
                expr.method, f'Undefined property "{expr.method.lexeme}".')
        return method.bind(obj)

    def _check_number_operands(
            self,
            operator: Token,
            left: Any,
            right: Any) -> None:
        if isinstance(left, float) and isinstance(right, float):
            return
        raise LoxRuntimeError(operator, 'Operands must be numbers.')

    def _evaluate(self, expr: Expr) -> Any:
        return expr.accept(self)

    def _is_truthy(self, obj: Any) -> Any:
        if obj is None:
            return False
        if isinstance(obj, bool):
            return bool(obj)
        return True
