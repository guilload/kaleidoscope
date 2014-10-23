import ast
import tokens


class Parser(object):
    """
    Provide a simple token buffer. Parser.current is the current token the
    parser is looking at. Parser.Next() reads another token from the lexer and
    updates Parser.current with its results.
    """

    precedence = {'=': 2,
                  '<': 10,
                  '<=': 10,
                  '>': 10,
                  '>=': 10,
                  '+': 20,
                  '-': 20,
                  '*': 40,
                  '/': 40}

    def __init__(self, stream):
        self.current = None
        self.stream = stream

    def next(self):
        self.current = self.stream.next()

    def current_token_precedence(self):
        if isinstance(self.current, tokens.Char):
            return self.precedence.get(self.current.value, -1)
        else:
            return -1

    def parse_number(self):
        """
        numberexpr ::= number
        """
        expression = ast.Number(self.current.value)
        self.next()
        return expression

    def parse_paren(self):
        """
        parenexpr ::= '(' expression ')'
        """
        self.next()
        expression = self.parse_expression()

        if self.current != ')':
            raise SyntaxError("Expected ')'!")

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
            return ast.Variable(name)
        self.next()

        args = []

        if self.current != ')':
            while True:
                expression = self.parse_expression()
                args.append(expression)

                if self.current == ')':
                    break

                if self.current != ',':
                    error = "Expected ')' or ',' in argument list"
                    raise SyntaxError(error)

                self.next()

        self.next()
        return ast.Call(name, args)

    def parse_primary(self):
        """
        primaryexpr ::= identifierexpr | numberexpr | parenexpr
        """
        if isinstance(self.current, tokens.Identifier):
            return self.parse_identifier()

        elif self.current == tokens.If:
            return self.parse_if()

        elif self.current == tokens.For:
            return self.parse_for()

        elif isinstance(self.current, tokens.Number):
            return self.parse_number()

        elif self.current == tokens.Var:
            return self.parse_var()

        elif self.current == '(':
            return self.parse_paren()

        else:
            error = "Unknown token '{}' when expecting an expression."
            raise SyntaxError(error.format(self.current))

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

            left = ast.BinaryOperator(binop, left, right)

    def parse_prototype(self):
        """
        # prototype ::= id '(' id* ')'
        """
        if not isinstance(self.current, tokens.Identifier):
            raise SyntaxError('Expected function name in prototype.')

        name = self.current.name
        self.next()

        if self.current != '(':
            raise SyntaxError("Expected '(' in prototype.")

        self.next()

        if self.current == ')':
            self.next()
            return ast.Prototype(name, [])

        args = []
        while isinstance(self.current, tokens.Identifier):
            args.append(self.current.name)
            self.next()

        if self.current != ')':
            raise SyntaxError("Expected ')' in prototype.")

        self.next()
        return ast.Prototype(name, args)

    def parse_definition(self):
        """
        # definition ::= 'def' prototype expression
        """
        self.next()
        prototype = self.parse_prototype()
        body = self.parse_expression()
        return ast.Function(prototype, body)

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
        prototype = ast.Prototype('', [])
        return ast.Function(prototype, self.parse_expression())

    def parse_if(self):
        """
        ifexpr ::= 'if' expression 'then' expression 'else' expression
        """
        self.next()
        condition = self.parse_expression()

        if self.current != tokens.Then:
            raise SyntaxError("Expected 'then'.")

        self.next()
        then_branch = self.parse_expression()

        if self.current != tokens.Else:
            return ast.If(condition, then_branch)

        self.next()
        else_branch = self.parse_expression()

        return ast.If(condition, then_branch, else_branch)

    def parse_for(self):
        self.next()

        if not isinstance(self.current, tokens.Identifier):
            raise SyntaxError('Expected identifier after for.')

        variable = self.current.name
        self.next()

        if self.current != '=':
            raise SyntaxError('Expected "=" after for variable.')
        self.next()

        start = self.parse_expression()

        if self.current != ',':
            raise SyntaxError('Expected "," after for start value.')
        self.next()

        end = self.parse_expression()

        # The step value is optional.
        if self.current == ',':
            self.next()
            step = self.parse_expression()
        else:
            step = None

        if self.current != tokens.In:
            raise SyntaxError('Expected "in" after for variable specification.')
        self.next()

        body = self.parse_expression()
        return ast.For(variable, start, end, step, body)

    def parse_var(self):
        self.next()
        variables = {}

        # At least one variable name is required.
        if not isinstance(self.current, tokens.Identifier):
            raise RuntimeError('Expected identifier after "var".')

            # The first part of this code parses the list of identifier/expr
            # pairs into the local variables list.

        while True:
            name = self.current.name
            self.next()

            # Read the optional initializer.
            if self.current == '=':
                self.next()
                variables[name] = self.parse_expression()
            else:
                variables[name] = None

            # End of var list, exit loop.
            if self.current != ',':
                break

            self.next()

            if not isinstance(self.current, tokens.Identifier):
                msg = 'Expected identifier after "," in a var expression.'
                raise SyntaxError(msg)

        # Once all the variables are parsed, we then parse the body and create
        # the AST node:

        # At this point, we have to have 'in'.
        if self.current != tokens.In:
            raise SyntaxError('Expected "in" keyword after "var".')
        self.next()

        body = self.parse_expression()
        return ast.Var(variables, body)

    def parse(self):
        """
        top ::= definition | external | expression | EOF
        """
        self.next()

        while self.current != tokens.EOF:

            if self.current == tokens.Def:
                yield False, self.parse_definition()

            elif self.current == tokens.Extern:
                yield False, self.parse_extern()

            elif self.current == tokens.If:
                yield False, self.parse_if()

            elif self.current == tokens.Var:
                yield False, self.parse_var()

            else:
                yield True, self.parse_toplevel()
