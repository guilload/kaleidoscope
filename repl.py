import cStringIO

from context import Context
from lexer import Lexer
from parser import Parser


def read():
    line = raw_input('> ')
    lines = []

    while line:
        lines.append(line)
        line = raw_input('  ')

    return '\n'.join(lines)


def main():
    context = Context('repl')

    while True:
        try:
            raw = read()
        except KeyboardInterrupt:
            break

        stream = cStringIO.StringIO(raw)
        tokens = Lexer(stream).lex()  # returns a generator
        ast = Parser(tokens).parse()  # returns a generator

        for node in ast:
            try:
                print node.code(context)
            except SyntaxError:
                continue


if __name__ == '__main__':
    main()
