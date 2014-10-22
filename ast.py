from llvm.core import Builder, Constant, FCMP_ONE, FCMP_ULT, Type
from llvm.core import Function as Func


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

    def code(self, _):
        return Constant.real(Type.double(), self.value)


class Variable(Expression):
    """
    Expression class for referencing a variable, like 'a'.
    """
    def __init__(self, name):
        self.name = name

    def code(self, context):
        try:
            return context.scope[self.name]
        except KeyError:
            raise SyntaxError("unknown variable name: '{}'".format(self.name))


class BinaryOperator(Expression):
    """
    Expression class for a binary operator.
    """
    def __init__(self, operator, left, right):
        self.operator = operator
        self.left = left
        self.right = right

    def code(self, context):
        left = self.left.code(context)
        right = self.right.code(context)

        if self.operator == '+':
            return context.builder.fadd(left, right, 'addtmp')

        elif self.operator == '-':
            return context.builder.fsub(left, right, 'subtmp')

        elif self.operator == '*':
            return context.builder.fmul(left, right, 'multmp')

        elif self.operator == '<':
            ret = context.builder.fcmp(FCMP_ULT, left, right, 'cmptmp')
            # Convert bool 0 or 1 to double 0.0 or 1.0.
            return context.builder.uitofp(ret, Type.double(), 'booltmp')
        else:
            raise SyntaxError('unknown binary operator')


class Call(Expression):
    """
    Expression class for function calls.
    """
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

    def code(self, context):
        # Look up the name in the global module table.
        callee = context.module.get_function_named(self.callee)

        # Check for argument mismatch error.
        if len(callee.args) != len(self.args):
            raise SyntaxError('Incorrect number of arguments passed.')  # FIXME

        args = [arg.code(context) for arg in self.args]
        return context.builder.call(callee, args, 'calltmp')


class If(Expression):
    """
    Expression class for if / then / else.
    """
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

    def code(self, context):
        condition = self.condition.code(context)
        zero = Constant.real(Type.double(), 0)
        boolean = context.builder.fcmp(FCMP_ONE, condition, zero, 'ifcond')

        func = context.builder.basic_block.function

        # Create blocks for the then and else cases. Insert the 'then' block
        # at the end of the function.
        then_block = func.append_basic_block('then')
        else_block = func.append_basic_block('else')
        merge_block = func.append_basic_block('ifcont')
        context.builder.cbranch(boolean, then_block, else_block)

        # Emit then value.
        context.builder.position_at_end(then_block)
        then_value = self.then_branch.code(context)
        context.builder.branch(merge_block)

        # code generation of 'Then' can change the current block; update
        # then_block or the PHI node.
        then_block = context.builder.basic_block

        # Emit else block.
        context.builder.position_at_end(else_block)
        else_value = self.else_branch.code(context)
        context.builder.branch(merge_block)

        # code generation of 'Else' can change the current block, update
        # else_block or the PHI node.
        else_block = context.builder.basic_block

        # Emit merge block.
        context.builder.position_at_end(merge_block)
        phi = context.builder.phi(Type.double(), 'iftmp')
        phi.add_incoming(then_value, then_block)
        phi.add_incoming(else_value, else_block)
        return phi


class Prototype(object):
    """
    This class represents the "prototype" for a function, which captures its
    name, and its argument names (thus implicitly the number of arguments the
    function takes).
    """
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def code(self, context):
        # Make the function type, eg. double(double, double).
        func_args = (Type.double(),) * len(self.args)
        func_type = Type.function(Type.double(), func_args, False)
        func = Func.new(context.module, func_type, self.name)

        # FIXME deal with function redefinition

        for arg, name in zip(func.args, self.args):
            arg.name = name
            context.scope[name] = arg  # Add arguments to symbol table.

        return func


class Function(object):
    """
    This class represents a function definition itself.
    """
    def __init__(self, prototype, body):
        self.prototype = prototype
        self.body = body

    def code(self, context):
        context.scope = {}  # Create a new scope

        # Create a function object.
        func = self.prototype.code(context)

        # Create a new basic block to start insertion into.
        block = func.append_basic_block('entry')
        context.builder = Builder.new(block)

        # Finish off the function.
        try:
            ret = self.body.code(context)
            context.builder.ret(ret)

            # Validate the generated code, checking for consistency.
            func.verify()
            context.fpm.run(func)
        except:
            func.delete()
            raise

        return func
