"""Safe arithmetic expression evaluator.

Supports integers, floats, ``+ - * /``, unary ``+``/``-`` and parentheses.
Implemented as a tokenizer + recursive-descent parser; never uses eval/exec.
Anything else raises ValueError.
"""

import re
from typing import List, Tuple

_TOKEN_RE = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|(\S))")

Token = Tuple[str, str]  # (kind, text); kind in {"num", "op"}


def _tokenize(expr: str) -> List[Token]:
    tokens = []  # type: List[Token]
    pos = 0
    n = len(expr)
    while pos < n:
        m = _TOKEN_RE.match(expr, pos)
        if m is None:  # only trailing whitespace remains
            break
        pos = m.end()
        num, other = m.group(1), m.group(2)
        if num is not None:
            tokens.append(("num", num))
        elif other in "+-*/()":
            tokens.append(("op", other))
        else:
            raise ValueError("invalid character: %r" % other)
    return tokens


class _Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.i = 0

    def _peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _take(self) -> Token:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def parse(self) -> float:
        if not self.tokens:
            raise ValueError("empty expression")
        value = self._expr()
        if self._peek() is not None:
            raise ValueError("unexpected token: %r" % (self._peek()[1],))
        return value

    # expr := term (('+' | '-') term)*
    def _expr(self) -> float:
        value = self._term()
        while self._peek() in (("op", "+"), ("op", "-")):
            op = self._take()[1]
            rhs = self._term()
            value = value + rhs if op == "+" else value - rhs
        return value

    # term := factor (('*' | '/') factor)*
    def _term(self) -> float:
        value = self._factor()
        while self._peek() in (("op", "*"), ("op", "/")):
            op = self._take()[1]
            rhs = self._factor()
            if op == "*":
                value = value * rhs
            else:
                if rhs == 0:
                    raise ValueError("division by zero")
                value = value / rhs
        return value

    # factor := ('+' | '-') factor | number | '(' expr ')'
    def _factor(self) -> float:
        tok = self._peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        kind, text = tok
        if kind == "num":
            self._take()
            return float(text)
        if text in ("+", "-"):
            self._take()
            operand = self._factor()
            return operand if text == "+" else -operand
        if text == "(":
            self._take()
            value = self._expr()
            if self._peek() != ("op", ")"):
                raise ValueError("missing closing parenthesis")
            self._take()
            return value
        raise ValueError("unexpected token: %r" % text)


def evaluate(expr: str) -> float:
    """Evaluate an arithmetic expression and return a float."""
    if not isinstance(expr, str):
        raise ValueError("expression must be a string")
    return float(_Parser(_tokenize(expr)).parse())
