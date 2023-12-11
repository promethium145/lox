import enum
from functools import singledispatch
from typing import Union

had_error = False
had_runtime_error = False


@enum.unique
class TokenType(enum.Enum):
    # Single character tokens.
    LEFT_PAREN = enum.auto()
    RIGHT_PAREN = enum.auto()
    LEFT_BRACE = enum.auto()
    RIGHT_BRACE = enum.auto()
    COMMA = enum.auto()
    DOT = enum.auto()
    MINUS = enum.auto()
    PLUS = enum.auto()
    SEMICOLON = enum.auto()
    SLASH = enum.auto()
    STAR = enum.auto()

    # One or two character tokens.
    BANG = enum.auto()
    BANG_EQUAL = enum.auto()
    EQUAL = enum.auto()
    EQUAL_EQUAL = enum.auto()
    GREATER = enum.auto()
    GREATER_EQUAL = enum.auto()
    LESS = enum.auto()
    LESS_EQUAL = enum.auto()

    # Literals.
    IDENTIFIER = enum.auto()
    STRING = enum.auto()
    NUMBER = enum.auto()

    # Keywords.
    AND = enum.auto()
    CLASS = enum.auto()
    ELSE = enum.auto()
    FALSE = enum.auto()
    FUN = enum.auto()
    FOR = enum.auto()
    IF = enum.auto()
    NIL = enum.auto()
    OR = enum.auto()
    PRINT = enum.auto()
    RETURN = enum.auto()
    SUPER = enum.auto()
    THIS = enum.auto()
    TRUE = enum.auto()
    VAR = enum.auto()
    WHILE = enum.auto()

    EOF = enum.auto()


KEYWORDS = {k: getattr(TokenType, k.upper()) for k in (
    'and',
    'class',
    'else',
    'false',
    'for',
    'fun',
    'if',
    'nil',
    'or',
    'print',
    'return',
    'super',
    'this',
    'true',
    'var',
    'while'
)}


class Token:

    def __init__(self, token_type: TokenType, lexeme: str,
                 literal: Union[None, str, float], line: int):
        self.token_type = token_type
        self.lexeme = lexeme
        self.literal = literal
        self.line = line

    def __str__(self) -> str:
        return f'{self.token_type} {self.lexeme} {self.literal}'


class LoxRuntimeError(RuntimeError):

    def __init__(self, token: Token, msg: str):
        self.token = token
        self.msg = msg
        super().__init__(msg)


@singledispatch
def error(arg, msg):
    raise NotImplemented('invalid call to generic error fn')


@error.register
def _(line: int, msg: str) -> None:
    report(line, '', msg)


@error.register
def _(token: Token, msg: str) -> None:
    if token.token_type == TokenType.EOF:
        report(token.line, ' at end', msg)
    else:
        report(token.line, ' at "' + token.lexeme + '"', msg)


def runtime_error(err: LoxRuntimeError) -> None:
    print(f'{str(err)}\n[line {err.token.line}]')
    global had_runtime_error
    had_runtime_error = True


def report(line: int, where: str, msg: str) -> None:
    print(f'[line {line}] Error{where}: {msg}')
    global had_error
    had_error = True
