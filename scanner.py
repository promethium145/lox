from typing import Union

from common import KEYWORDS, Token, TokenType, error


class Scanner:

    def __init__(self, source: str):
        self.source = source
        self.tokens: list[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1

    def scan_tokens(self) -> list[Token]:
        while not self._is_at_end():
            self.start = self.current
            self._scan_token()
        self.tokens.append(Token(TokenType.EOF, '', None, self.line))
        return self.tokens

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def _scan_token(self) -> None:
        c = self._advance()
        if c == '(':
            self._add_token(TokenType.LEFT_PAREN)
        elif c == ')':
            self._add_token(TokenType.RIGHT_PAREN)
        elif c == '{':
            self._add_token(TokenType.LEFT_BRACE)
        elif c == '}':
            self._add_token(TokenType.RIGHT_BRACE)
        elif c == ',':
            self._add_token(TokenType.COMMA)
        elif c == '.':
            self._add_token(TokenType.DOT)
        elif c == '-':
            self._add_token(TokenType.MINUS)
        elif c == '+':
            self._add_token(TokenType.PLUS)
        elif c == ';':
            self._add_token(TokenType.SEMICOLON)
        elif c == '*':
            self._add_token(TokenType.STAR)
        elif c == '!':
            self._add_token(TokenType.BANG_EQUAL if self._match(
                '=') else TokenType.BANG)
        elif c == '=':
            self._add_token(TokenType.EQUAL_EQUAL if self._match(
                '=') else TokenType.EQUAL)
        elif c == '<':
            self._add_token(TokenType.LESS_EQUAL if self._match(
                '=') else TokenType.LESS)
        elif c == '>':
            self._add_token(TokenType.GREATER_EQUAL if self._match(
                '=') else TokenType.GREATER)
        elif c == '/':
            if self._match('/'):
                while self._peek() != '\n' and not self._is_at_end():
                    self._advance()
            elif self._match('*'):
                self._c_style_comment()
            else:
                self._add_token(TokenType.SLASH)
        elif c in (' ', '\r', '\t'):
            pass
        elif c == '\n':
            self.line += 1
        elif c == '"':
            self._string()
        else:
            if c.isdigit():
                self._number()
            elif c.isalpha():
                self._identifier()
            else:
                error(self.line, 'Unexpected character')

    def _advance(self) -> str:
        c = self.source[self.current]
        self.current += 1
        return c

    def _add_token(self, token_type: TokenType) -> None:
        self._do_add_token(token_type, None)

    def _do_add_token(self, token_type: TokenType,
                      literal: Union[None, str, float]) -> None:
        text = self.source[self.start:self.current]
        self.tokens.append(Token(token_type, text, literal, self.line))

    def _match(self, c: str) -> bool:
        if self._is_at_end():
            return False
        if self.source[self.current] != c:
            return False
        self.current += 1
        return True

    def _peek(self) -> str:
        if self._is_at_end():
            return ''
        return self.source[self.current]

    def _string(self) -> None:
        while self._peek() != '"' and not self._is_at_end():
            if self._peek() == '\n':
                self.line += 1
            self._advance()
        if self._is_at_end():
            error(self.line, 'Unterminated string.')
            return

        # The closing ".
        self._advance()

        # Trim the surrounding quotes.
        val = self.source[self.start + 1:self.current - 1]
        self._do_add_token(TokenType.STRING, val)

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()

        # Look for a fractional part.
        if self._peek() == '.' and self._peek_next().isdigit():
            # Consume the "."
            self._advance()
            while self._peek().isdigit():
                self._advance()

        self._do_add_token(TokenType.NUMBER, float(
            self.source[self.start:self.current]))

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return ''
        return self.source[self.current + 1]

    def _identifier(self) -> None:
        while self._peek().isalnum():
            self._advance()
        text = self.source[self.start:self.current]
        token_type = KEYWORDS.get(text)
        if token_type is None:
            token_type = TokenType.IDENTIFIER
        self._add_token(token_type)

    def _c_style_comment(self) -> None:
        while not self._is_at_end() and not (
                self._peek() == '*' and self._peek_next() == '/'):
            if self._peek() == '\n':
                self.line += 1
            self._advance()
        if self._is_at_end():
            error(self.line, 'Unterminated comment')
            return
        # The closing "*/"
        self._advance()
        self._advance()
