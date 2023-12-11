from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import singledispatch
from parser import Parser

import common
from interpreter import Interpreter
from resolver import Resolver
from scanner import Scanner


def _run_file(path: str) -> None:
    with open(path, 'r') as f:
        data = f.read()
    _run(data)
    if common.had_error:
        sys.exit(65)
    if common.had_runtime_error:
        sys.exit(70)


def _run_prompt() -> None:
    while True:
        print('> ', end='')
        line = input()
        if not line:
            break
        _run(line)
        common.had_error = False


interpreter = Interpreter()


def _run(source: str) -> None:
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)
    statements = parser.parse()
    if common.had_error:
        return
    resolver = Resolver(interpreter)
    resolver.resolve(statements)
    if common.had_error:
        return
    interpreter.interpret(statements)


def main() -> None:
    if len(sys.argv) > 2:
        print('Usage: lox [script]')
        sys.exit(64)
    elif len(sys.argv) == 2:
        _run_file(sys.argv[1])
    else:
        _run_prompt()


if __name__ == '__main__':
    main()
