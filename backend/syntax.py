"""A restricted Wolfram-style grammar. Input is never executed as Python."""
from dataclasses import dataclass
import re
import json
from pathlib import Path

CHARACTERS = json.loads(Path(__file__).with_name('characters.json').read_text(encoding='utf-8'))
NAMED_CHARACTERS = {name: character for name, character, *_ in CHARACTERS}


class InputError(ValueError):
    pass


@dataclass(frozen=True)
class Node:
    kind: str
    value: str = ""
    args: tuple = ()


TOKEN = re.compile(r'\s+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|[^\W\d]\w*(?:`\w+)*|"(?:[^"\\]|\\.)*"|==|!=|<=|>=|->|&&|\|\||[°+\-*/^=<>!;,\[\]{}()\']', re.UNICODE)


class Parser:
    def __init__(self, source):
        if len(source) > 24000:
            raise InputError("Input exceeds 24,000 characters")
        def normalize(part):
            if part.startswith('"'):
                return part
            part = re.sub(r'\\\[([A-Za-z]+)\]', lambda m: NAMED_CHARACTERS.get(m.group(1), m.group(0)), part)
            part = re.sub(r'([^\W\d])([₀₁₂₃₄₅₆₇₈₉]+)', lambda m: m.group(1)+'_'+m.group(2).translate(str.maketrans('₀₁₂₃₄₅₆₇₈₉','0123456789')), part)
            part = part.translate(str.maketrans({"π": "Pi", "∞": "Infinity", "×": "*", "·": "*", "⋅": "*", "÷": "/", "−": "-", "≤": "<=", "≥": ">=", "≠": "!=", "→": "->", "∧": "&&", "∨": "||", "ⅈ": "I", "ⅉ": "I", "ⅇ": "E", "ℯ": "E"}))
            # The editor keeps classroom-panel glyphs visible. Bracketed glyphs
            # are the compact source spelling for the corresponding WL call.
            part = re.sub(r'∫(?=\s*\[)', 'Integrate', part)
            part = re.sub(r'∑(?=\s*\[)', 'Sum', part)
            part = re.sub(r'∏(?=\s*\[)', 'Product', part)
            part = re.sub(r'√(?=\s*\[)', 'Sqrt', part)
            return part
        source = "".join(normalize(part) for part in re.split(r'("(?:[^"\\]|\\.)*")', source))
        self.tokens = []
        cursor = 0
        nesting = 0
        operators = {'=', '->', '||', '&&', '==', '!=', '<', '>', '<=', '>=', '+', '-', '*', '/', '^', ',', ';'}
        for match in TOKEN.finditer(source):
            if match.start() != cursor:
                raise InputError(f"Unexpected character at position {cursor + 1}")
            cursor = match.end()
            token = match.group()
            if token.isspace():
                if '\n' in token and nesting == 0 and self.tokens and self.tokens[-1] not in (operators - {';'}) | {'\n'}:
                    self.tokens.append('\n')
                continue
            if token in operators - {'+', '-'} and self.tokens and self.tokens[-1] == '\n':
                self.tokens.pop()
            self.tokens.append(token)
            if token in ('[', '{', '('):
                nesting += 1
            elif token in (']', '}', ')'):
                nesting -= 1
        if cursor != len(source):
            raise InputError(f"Unexpected character at position {cursor + 1}")
        if self.tokens and self.tokens[-1] == '\n':
            self.tokens.pop()
        self.tokens.append("<end>")
        self.i = 0
        self.depth = 0

    def peek(self):
        return self.tokens[self.i]

    def take(self, expected=None):
        token = self.peek()
        if expected and token != expected:
            raise InputError(f"Expected {expected}, found {token}")
        self.i += 1
        return token

    def parse(self):
        lines = []
        while True:
            statements = [self.expr()]
            while self.peek() == ";":
                self.take()
                if self.peek() in ("<end>", '\n'):
                    statements.append(Node("null"))
                    break
                statements.append(self.expr())
            lines.append(statements[0] if len(statements) == 1 else Node("sequence", args=tuple(statements)))
            if self.peek() != '\n':
                break
            self.take()
        self.take("<end>")
        return lines[0] if len(lines) == 1 else Node('program', args=tuple(lines))

    def expr(self, minimum=0):
        self.depth += 1
        if self.depth > 120:
            raise InputError("Expression nesting exceeds 120 levels")
        token = self.take()
        if token in ("+", "-"):
            left = Node("unary", token, (self.expr(35),))
        elif token == "(":
            left = Node("group", args=(self.compound(')'),))
            self.take(")")
        elif token == "{":
            left = Node("list", args=tuple(self.arguments("}")))
        elif token == '[':
            left = Node('call', args=(Node('number', '1'), self.expr()))
            self.take(']')
        elif token.startswith('"'):
            try:
                left = Node("string", json.loads(token))
            except json.JSONDecodeError:
                raise InputError("Invalid string escape") from None
        elif re.fullmatch(r'(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?', token):
            left = Node("number", token)
        elif re.fullmatch(r'[^\W\d]\w*(?:`\w+)*', token, re.UNICODE):
            left = Node("symbol", token)
        else:
            raise InputError(f"Expected expression, found {token}")
        binding = {"=": 3, "->": 5, "||": 7, "&&": 8, "==": 10, "!=": 10,
                   "<": 10, ">": 10, "<=": 10, ">=": 10, "+": 20, "-": 20,
                   "*": 30, "/": 30, "^": 40}
        while True:
            token = self.peek()
            if token == "[":
                if 60 < minimum:
                    break
                self.take()
                left = Node("call", args=(left, *self.arguments("]")))
                continue
            if token in ("!", "'", "°"):
                if 60 < minimum:
                    break
                self.take()
                left = Node("postfix", token, (left,))
                continue
            implicit = token == "(" or bool(re.fullmatch(r'[^\W\d]\w*|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?', token, re.UNICODE))
            precedence = 30 if implicit else binding.get(token, -1)
            if precedence < minimum:
                break
            if not implicit:
                self.take()
            operation = "*" if implicit else token
            right = self.expr(precedence if operation in ("^", "=", "->") else precedence + 1)
            left = Node("binary", operation, (left, right))
        self.depth -= 1
        return left

    def arguments(self, closing):
        args = []
        if self.peek() != closing:
            args.append(self.compound(closing))
            while self.peek() == ",":
                self.take()
                args.append(self.compound(closing))
        self.take(closing)
        return args

    def compound(self, closing):
        statements = [self.expr()]
        while self.peek() == ';':
            self.take()
            if self.peek() in (closing, ','):
                statements.append(Node('null'))
                break
            statements.append(self.expr())
        return statements[0] if len(statements) == 1 else Node('sequence', args=tuple(statements))


def parse(source):
    return Parser(source).parse()
