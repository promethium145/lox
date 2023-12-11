from typing import Optional

from common import Token, TokenType, error
from expr import (Assign, Binary, Call, Expr, Get, Grouping, Literal, Logical,
                  Set, Super, This, Unary, Variable)
from stmt import (Block, Class, Expression, Function, If, Print, Return, Stmt,
                  Var, While)


class ParseError(RuntimeError):
    pass


class Parser:

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> list[Optional[Stmt]]:
        statements: list[Optional[Stmt]] = []
        while not self._is_at_end():
            statements.append(self._declaration())
        return statements

    def _declaration(self) -> Optional[Stmt]:
        try:
            if self._match(TokenType.FUN):
                return self._function('function')
            if self._match(TokenType.VAR):
                return self._var_declaration()
            if self._match(TokenType.CLASS):
                return self._class_declaration()
            return self._statement()
        except ParseError as e:
            self._synchronize()
            return None

    def _class_declaration(self) -> Stmt:
        name = self._consume(TokenType.IDENTIFIER, 'Expect class name.')
        superclass = None
        if self._match(TokenType.LESS):
            self._consume(TokenType.IDENTIFIER, 'Expect superclass name.')
            superclass = Variable(self._previous())
        self._consume(TokenType.LEFT_BRACE, 'Expect "{" before class body.')
        methods: list[Function] = []
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            methods.append(self._function('method'))
        self._consume(TokenType.RIGHT_BRACE, 'Expect "}" after class body.')
        return Class(name, superclass, methods)

    def _function(self, kind: str) -> Function:
        name = self._consume(TokenType.IDENTIFIER, f'Expect {kind} name.')
        self._consume(TokenType.LEFT_PAREN, f'Expect "(" after {kind} name."')
        parameters: list[Token] = []
        if not self._check(TokenType.RIGHT_PAREN):
            while True:
                if len(parameters) >= 255:
                    self._error(
                        self._peek(), 'Can\'t have more than 255 parameters.')
                parameters.append(self._consume(
                    TokenType.IDENTIFIER, 'Expect parameter name.'))
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RIGHT_PAREN,
                      'Expect ")" after parameters.')
        self._consume(TokenType.LEFT_BRACE, f'Expect "{{" before {kind} body.')
        body = self._block()
        return Function(name, parameters, body)

    def _var_declaration(self) -> Var:
        name = self._consume(TokenType.IDENTIFIER, 'Expect variable name.')
        initializer = None
        if self._match(TokenType.EQUAL):
            initializer = self._expression()
        self._consume(TokenType.SEMICOLON,
                      'Expect ";" after variable declaration.')
        return Var(name, initializer)

    def _statement(self) -> Stmt:
        if self._match(TokenType.PRINT):
            return self._print_statement()
        if self._match(TokenType.RETURN):
            return self._return_statement()
        if self._match(TokenType.LEFT_BRACE):
            return Block(self._block())
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.WHILE):
            return self._while_statement()
        if self._match(TokenType.FOR):
            return self._for_statement()
        return self._expression_statement()

    def _print_statement(self) -> Print:
        value = self._expression()
        self._consume(TokenType.SEMICOLON, 'Expect ";" after value.')
        return Print(value)

    def _return_statement(self) -> Return:
        keyword = self._previous()
        if not self._check(TokenType.SEMICOLON):
            value = self._expression()
        else:
            value = None
        self._consume(TokenType.SEMICOLON, 'Expect ";" after return value.')
        return Return(keyword, value)

    def _expression_statement(self) -> Expression:
        expr = self._expression()
        self._consume(TokenType.SEMICOLON, 'Expect ";" after expression.')
        return Expression(expr)

    def _if_statement(self) -> If:
        self._consume(TokenType.LEFT_PAREN, 'Expect "(" after if.')
        condition = self._expression()
        self._consume(TokenType.RIGHT_PAREN, 'Expect ")" after if condition.')
        then_branch = self._statement()
        if self._match(TokenType.ELSE):
            else_branch = self._statement()
        else:
            else_branch = None
        return If(condition, then_branch, else_branch)

    def _while_statement(self) -> While:
        self._consume(TokenType.LEFT_PAREN, 'Expect "(" after while.')
        condition = self._expression()
        self._consume(TokenType.RIGHT_PAREN,
                      'Expect ")" after while condition.')
        body = self._statement()
        return While(condition, body)

    def _for_statement(self) -> Stmt:
        self._consume(TokenType.LEFT_PAREN, 'Expect "(" after for.')
        initializer: Optional[Stmt]
        if self._match(TokenType.SEMICOLON):
            initializer = None
        elif self._match(TokenType.VAR):
            initializer = self._var_declaration()
        else:
            initializer = self._expression_statement()
        if not self._check(TokenType.SEMICOLON):
            condition = self._expression()
        else:
            condition = None
        self._consume(TokenType.SEMICOLON, 'Expect ";" after loop condition.')
        if not self._check(TokenType.RIGHT_PAREN):
            increment = self._expression()
        else:
            increment = None
        self._consume(TokenType.RIGHT_PAREN, 'Expect ")" after for clauses.')
        body = self._statement()

        if increment is not None:
            body = Block([body, Expression(increment)])
        if condition is None:
            condition = Literal(True)
        body = While(condition, body)
        if initializer is not None:
            body = Block([initializer, body])
        return body

    def _block(self) -> list[Optional[Stmt]]:
        statements: list[Optional[Stmt]] = []
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            statements.append(self._declaration())
        self._consume(TokenType.RIGHT_BRACE, 'Expect "}" after block.')
        return statements

    def _expression(self) -> Expr:
        return self._assignment()

    def _assignment(self) -> Expr:
        expr = self._or()
        if self._match(TokenType.EQUAL):
            equals = self._previous()
            value = self._assignment()
            if isinstance(expr, Variable):
                return Assign(expr.name, value)
            elif isinstance(expr, Get):
                return Set(expr.obj, expr.name, value)
            self._error(equals, 'Invalid assignment target.')
        return expr

    def _or(self) -> Expr:
        expr = self._and()
        while self._match(TokenType.OR):
            operator = self._previous()
            right = self._and()
            expr = Logical(expr, operator, right)
        return expr

    def _and(self) -> Expr:
        expr = self._equality()
        while self._match(TokenType.AND):
            operator = self._previous()
            right = self._equality()
            expr = Logical(expr, operator, right)
        return expr

    def _equality(self) -> Expr:
        expr = self._comparison()
        while self._match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            operator: Token = self._previous()
            right: Expr = self._comparison()
            expr = Binary(expr, operator, right)
        return expr

    def _comparison(self) -> Expr:
        expr = self._term()
        while self._match(
                TokenType.GREATER,
                TokenType.GREATER_EQUAL,
                TokenType.LESS,
                TokenType.LESS_EQUAL):
            operator: Token = self._previous()
            right: Expr = self._term()
            expr = Binary(expr, operator, right)
        return expr

    def _term(self) -> Expr:
        expr = self._factor()
        while self._match(TokenType.MINUS, TokenType.PLUS):
            operator = self._previous()
            right = self._factor()
            expr = Binary(expr, operator, right)
        return expr

    def _factor(self) -> Expr:
        expr = self._unary()
        while self._match(TokenType.SLASH, TokenType.STAR):
            operator = self._previous()
            right = self._unary()
            expr = Binary(expr, operator, right)
        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.BANG, TokenType.MINUS):
            operator = self._previous()
            right = self._unary()
            return Unary(operator, right)
        return self._call()

    def _call(self) -> Expr:
        expr = self._primary()
        while True:
            if self._match(TokenType.LEFT_PAREN):
                expr = self._finish_call(expr)
            elif self._match(TokenType.DOT):
                name = self._consume(TokenType.IDENTIFIER,
                                     'Expect property name after ".".')
                expr = Get(expr, name)
            else:
                break
        return expr

    def _finish_call(self, callee: Expr) -> Expr:
        arguments: list[Expr] = []
        if not self._check(TokenType.RIGHT_PAREN):
            while True:
                if len(arguments) >= 255:
                    self._error(
                        self._peek(), 'Can\'t have more than 255 arguments.')
                arguments.append(self._expression())
                if not self._match(TokenType.COMMA):
                    break
        paren = self._consume(TokenType.RIGHT_PAREN,
                              'Expect ")" after arguments.')
        return Call(callee, paren, arguments)

    def _primary(self) -> Expr:
        if self._match(TokenType.FALSE):
            return Literal(False)
        if self._match(TokenType.TRUE):
            return Literal(True)
        if self._match(TokenType.NIL):
            return Literal(None)
        if self._match(TokenType.NUMBER, TokenType.STRING):
            return Literal(self._previous().literal)
        if self._match(TokenType.SUPER):
            keyword = self._previous()
            self._consume(TokenType.DOT, 'Expect "." after "super".')
            method = self._consume(TokenType.IDENTIFIER,
                                   "Expect superclass method name.")
            return Super(keyword, method)
        if self._match(TokenType.THIS):
            return This(self._previous())
        if self._match(TokenType.IDENTIFIER):
            return Variable(self._previous())
        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN,
                          'Expect ")" after expression.')
            return Grouping(expr)
        raise self._error(self._peek(), 'Expect expression.')

    def _match(self, *token_types: TokenType) -> bool:
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self._peek().token_type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().token_type == TokenType.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _consume(self, token_type: TokenType, msg: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise self._error(self._peek(), msg)

    def _error(self, token: Token, msg: str) -> ParseError:
        error(token, msg)
        return ParseError()

    def _synchronize(self) -> None:
        self._advance()
        while not self._is_at_end():
            if self._previous().token_type == TokenType.SEMICOLON:
                return
            if self._peek().token_type in (
                    TokenType.CLASS,
                    TokenType.FUN,
                    TokenType.VAR,
                    TokenType.FOR,
                    TokenType.IF,
                    TokenType.WHILE,
                    TokenType.PRINT,
                    TokenType.RETURN):
                return
            self._advance()
