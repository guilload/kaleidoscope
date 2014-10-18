from tokens import Char, EOF, Identifier, KEYWORDS, Number


class Lexer(object):
    def __init__(self, filepath):
        self.stream = open(filepath)
        self.current = ''

    def __del__(self):
        self.stream.close()

    def lex(self):
        self.current = self.stream.read(1)

        while self.current:

            if self.current == '#':
                token = self.lex_comment()

            elif self.current.isalpha():
                token = self.lex_identifier()

            elif self.current.isdigit():
                token = self.lex_number()

            elif self.current.isspace():
                token = self.lex_whitespace()

            else:
                token = Char(self.current)
                self.current = self.stream.read(1)

            if token:
                yield token

        yield EOF

    def lex_comment(self):
        self.current = self.stream.read(1)

        while self.current and self.current != '\n':
            self.current = self.stream.read(1)

        return None

    def lex_identifier(self):
        chars = [self.current]
        self.current = self.stream.read(1)

        while self.current.isalnum():
            chars.append(self.current)
            self.current = self.stream.read(1)

        string = ''.join(chars)
        return KEYWORDS.get(string, Identifier(string))

    def lex_number(self):
        chars = [self.current]
        self.current = self.stream.read(1)
        dot = True

        while self.current.isdigit() or (dot and self.current == '.'):
            chars.append(self.current)
            self.current = self.stream.read(1)

            if self.current == '.':
                dot = False

        string = ''.join(chars)
        return Number(string)

    def lex_whitespace(self):
        self.current = self.stream.read(1)

        while self.current.isspace():
            self.current = self.stream.read(1)

        return None
