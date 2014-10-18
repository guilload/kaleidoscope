class Expression(object):
    """
    Base class for all expression nodes.
    """
    pass


class Number(Expression):
    """
    Expression class for numeric literals like '1.0'.
    """
    def __init__(self, value):
        self.value = value


class Variable(Expression):
    """
    Expression class for referencing a variable, like 'a'.
    """
    def __init__(self, name):
        self.name = name


class BinaryOperator(Expression):
    """
    Expression class for a binary operator.
    """
    def __init__(self, operator, left, right):
        self.operator = operator
        self.left = left
        self.right = right


class Call(Expression):
    """
    Expression class for function calls.
    """
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args


class If(Expression):
    """
    Expression class for if / then / else.
    """
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch


class Prototype(object):
    """
    This class represents the "prototype" for a function, which captures its
    name, and its argument names (thus implicitly the number of arguments the
    function takes).
    """
    def __init__(self, name, args):
        self.name = name
        self.args = args


class Function(object):
    """
    This class represents a function definition itself.
    """
    def __init__(self, prototype, body):
        self.prototype = prototype
        self.body = body
