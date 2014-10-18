import sys

from lexer import Lexer
from parser import Parser


if __name__ == '__main__':
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'fibonacci.k'

    for token in Lexer(filepath).lex():
        print token

    for node in Parser(filepath).parse():
        print node
