from ast import BinaryOperator, Call, Function, If, Number, Prototype, Variable

from lexer import Lexer

from tokens import Char as CharToken
from tokens import Identifier as IdentifierToken
from tokens import Number as NumberToken
from tokens import Def, EOF, Extern
from tokens import If as IfToken, Else as ElseToken, Then as ThenToken


class Parser(object):
    """
    Provide a simple token buffer. Parser.current is the current token the
    parser is looking at. Parser.Next() reads another token from the lexer and
    updates Parser.current with its results.
    """

    precedence = {'<': 10,
                  '<=': 10,
                  '>': 10,
                  '>=': 10,
                  '+': 20,
                  '-': 20,
                  '*': 40,
                  '/': 40}

    def __init__(self, filepath):
        self.stream = Lexer(filepath).lex()
        self.current = self.stream.next()

    def next(self):
        self.current = self.stream.next()

    def current_token_precedence(self):
        if isinstance(self.current, CharToken):
            return self.precedence.get(self.current.value, -1)
        else:
            return -1

    def parse_number(self):
        """
        numberexpr ::= number
        """
        expression = Number(self.current.value)
        self.next()
        return expression

    def parse_paren(self):
        """
        parenexpr ::= '(' expression ')'
        """
        self.next()
        expression = self.parse_expression()

        if self.current != ')':
            raise RuntimeError("Expected ')'!")

        self.next()
        return expression

    def parse_identifier(self):
        """
        # identifierexpr ::= identifier |
                             identifier '(' expression? (',' expression)* ')'
        """
        name = self.current.name
        self.next()

        if self.current != '(':
            return Variable(name)

        self.next()

        if self.current != ')':
            args = []

            while True:
                expression = self.parse_expression()
                args.append(expression)

                if self.current == ')':
                    break

                if self.current != ',':
                    error = "Expected ')' or ',' in argument list"
                    raise RuntimeError(error)

                self.next()

        self.next()
        return Call(name, args)

    def parse_primary(self):
        """
        primaryexpr ::= identifierexpr | numberexpr | parenexpr
        """
        if isinstance(self.current, IdentifierToken):
            return self.parse_identifier()

        elif self.current == IfToken:
            return self.parse_if()

        elif isinstance(self.current, NumberToken):
            return self.parse_number()

        elif self.current == '(':
            return self.parse_paren()

        else:
            raise RuntimeError('Unknown token when expecting an expression.')

    def parse_expression(self):
        """
        expression ::= primary binoprhs
        """
        left = self.parse_primary()
        return self.parse_binop_right(left, 0)

    def parse_binop_right(self, left, min_precedence):
        """
        binoprhs ::= (operator primary)*
        """
        while True:  # If this is a binary operator, find its precedence.
            precedence = self.current_token_precedence()

            # If this is a binary operator that binds at least as tightly as
            # the current one, consume it; otherwise we are done.
            if precedence < min_precedence:
                return left

            binop = self.current.value
            self.next()

            # Parse the primary expression after the binary operator.
            right = self.parse_primary()

            # If binary_operator binds less tightly with right than the
            # operator after right, let the pending operator take right as its
            # left.
            next_precedence = self.current_token_precedence()

            if precedence < next_precedence:
                right = self.parse_binop_right(right, precedence + 1)

            left = BinaryOperator(binop, left, right)

    def parse_prototype(self):
        """
        # prototype ::= id '(' id* ')'
        """
        if not isinstance(self.current, IdentifierToken):
            raise RuntimeError('Expected function name in prototype.')

        name = self.current.name
        self.next()

        if self.current != '(':
            raise RuntimeError("Expected '(' in prototype.")

        self.next()

        if self.current == ')':
            self.next()
            return Prototype(name, [])

        args = []
        while isinstance(self.current, IdentifierToken):
            args.append(self.current.name)
            self.next()

        if self.current != ')':
            raise RuntimeError("Expected ')' in prototype.")

        self.next()
        return Prototype(name, args)

    def parse_definition(self):
        """
        # definition ::= 'def' prototype expression
        """
        self.next()
        prototype = self.parse_prototype()
        body = self.parse_expression()
        return Function(prototype, body)

    def parse_extern(self):
        """
        external ::= 'extern' prototype
        """
        self.next()
        return self.parse_prototype()

    def parse_toplevel(self):
        """
        toplevelexpr ::= expression
        """
        prototype = Prototype('', [])
        return Function(prototype, self.parse_expression())

    def parse_if(self):
        """
        ifexpr ::= 'if' expression 'then' expression 'else' expression
        """
        self.next()
        condition = self.parse_expression()

        if self.current != ThenToken:
            raise RuntimeError("Expected 'then'.")

        self.next()
        then_branch = self.parse_expression()

        if self.current != ElseToken:
            return If(condition, then_branch)

        self.next()
        else_branch = self.parse_expression()

        return If(condition, then_branch, else_branch)

    def parse(self):
        """
        top ::= definition | external | expression | EOF
        """
        while self.current != EOF:

            if self.current == Def:
                yield self.parse_definition()

            elif self.current == Extern:
                yield self.parse_extern()

            else:
                yield self.parse_expression()
