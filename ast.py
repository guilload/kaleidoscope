from llvm.core import Builder, Constant, FCMP_ONE, FCMP_ULT, Type
from llvm.core import Function as Func


def create_alloca_block(function, name):
    entry = function.get_entry_basic_block()
    builder = Builder.new(entry)
    builder.position_at_beginning(entry)
    return builder.alloca(Type.double(), name=name)


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
            return context.builder.load(context.scope[self.name], self.name)
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
        if self.operator == '=':
            if not isinstance(self.left, Variable):
                raise SyntaxError('Destination of "=" must be a variable.')

            value = self.right.code(context)  # RHS code generation
            variable = context.scope[self.left.name]  # Look up the name
            context.builder.store(value, variable)  # Store value, return it
            return value

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

        for name, arg in zip(self.prototype.args, func.args):
            alloca = create_alloca_block(func, name)
            context.builder.store(arg, alloca)
            context.scope[name] = alloca

        # Finish off the function.
        try:
            ret = self.body.code(context)
            context.builder.ret(ret)

            # Validate the generated code, checking for consistency.
            func.verify()

            # Optimize the function.
            context.fpm.run(func)
        except:
            func.delete()
            raise

        return func


class For(Expression):
    """
    Expression class for for / in.
    """
    def __init__(self, variable, start, end, step, body):
        self.variable = variable
        self.start = start
        self.end = end
        self.step = step
        self.body = body

    # code function using a PHI node

    # def code(self, context):
    #     # Emit the start code first, without 'variable' in scope.
    #     start_value = self.start.code(context)

    #     # Make the new basic block for the loop header, inserting after
    #     # current block.
    #     function = context.builder.basic_block.function
    #     pre_header_block = context.builder.basic_block
    #     loop_block = function.append_basic_block('loop')

    #     # Insert an explicit fallthrough from the current block to the
    #     # loop_block.
    #     context.builder.branch(loop_block)

    #     # Start insertion in loop_block.
    #     context.builder.position_at_end(loop_block)

    #     # Start the PHI node with an entry for start.
    #     variable_phi = context.builder.phi(Type.double(), self.variable)
    #     variable_phi.add_incoming(start_value, pre_header_block)

    #     # Within the loop, the variable is defined equal to the PHI node. If
    #     # if shadows an existing variable, we have to restore it, so save it
    #     # now.
    #     old_value = context.scope.get(self.variable, None)
    #     context.scope[self.variable] = variable_phi

    #     # Emit the body of the loop.  This, like any other expr, can change
    #     # the current BB.  Note that we ignore the value computed by the body.
    #     self.body.code(context)

    #     # Emit the step value.
    #     if self.step:
    #         step_value = self.step.code(context)
    #     else:
    #         # If not specified, use 1.0.
    #         step_value = Constant.real(Type.double(), 1)

    #     next_value = context.builder.fadd(variable_phi, step_value, 'next')

    #     # Compute the end condition and convert it to a bool by comparing to
    #     # 0.0.
    #     end_condition = self.end.code(context)
    #     end_condition_bool = context.builder.fcmp(FCMP_ONE, end_condition, Constant.real(Type.double(), 0), 'loopcond')

    #     # Create the "after loop" block and insert it.
    #     loop_end_block = context.builder.basic_block
    #     after_block = function.append_basic_block('afterloop')

    #     # Insert the conditional branch into the end of loop_end_block.
    #     context.builder.cbranch(end_condition_bool, loop_block, after_block)

    #     # Any new code will be inserted in after_block.
    #     context.builder.position_at_end(after_block)

    #     # Add a new entry to the PHI node for the backedge.
    #     variable_phi.add_incoming(next_value, loop_end_block)

    #     # Restore the unshadowed variable.
    #     if old_value:
    #         context.scope[self.variable] = old_value
    #     else:
    #         del context.scope[self.variable]

    #     # for expr always returns 0.0.
    #     return Constant.real(Type.double(), 0)

    def code(self, context):
        function = context.builder.basic_block.function

        # Create an alloca for the variable in the entry block.
        alloca = create_alloca_block(function, self.variable)

        # Emit the start code first, without 'variable' in scope.
        start_value = self.start.code(context)

        # Store the value into the alloca.
        context.builder.store(start_value, alloca)

        # Make the new basic block for the loop, inserting after current block.
        loop_block = function.append_basic_block('loop')

        # Insert an explicit fall through from the current block to the
        # loop_block.
        context.builder.branch(loop_block)

        # Start insertion in loop_block.
        context.builder.position_at_end(loop_block)

        # Within the loop, the variable is defined equal to the alloca.  If it
        # shadows an existing variable, we have to restore it, so save it now.
        old_value = context.scope.get(self.variable, None)
        context.scope[self.variable] = alloca

        # Emit the body of the loop.  This, like any other expr, can change the
        # current BB.  Note that we ignore the value computed by the body.
        self.body.code(context)

        # Emit the step value.
        if self.step:
            step_value = self.step.code(context)
        else:
            # If not specified, use 1.0.
            step_value = Constant.real(Type.double(), 1)

        # Compute the end condition.
        end_condition = self.end.code(context)

        # Reload, increment, and restore the alloca.  This handles the case
        # where the body of the loop mutates the variable.
        cur_value = context.builder.load(alloca, self.variable)
        next_value = context.builder.fadd(cur_value, step_value, 'nextvar')
        context.builder.store(next_value, alloca)

        # Convert condition to a bool by comparing equal to 0.0.
        end_condition_bool = context.builder.fcmp(FCMP_ONE, end_condition, Constant.real(Type.double(), 0), 'loopcond')

        # Create the "after loop" block and insert it.
        after_block = function.append_basic_block('afterloop')

        # Insert the conditional branch into the end of loop_block.
        context.builder.cbranch(end_condition_bool, loop_block, after_block)

        # Any new code will be inserted in after_block.
        context.builder.position_at_end(after_block)

        # Restore the unshadowed variable.
        if old_value is not None:
            context.scope[self.variable] = old_value
        else:
            del context.scope[self.variable]

        # for expr always returns 0.0.
        return Constant.real(Type.double(), 0)


class Var(Expression):
    def __init__(self, variables, body):
        self.variables = variables
        self.body = body

    def code(self, context):
        old_bindings = {}
        function = context.builder.basic_block.function

        # Register all variables and emit their initializer.
        for name, expression in self.variables.items():
            # Emit the initializer before adding the variable to scope, this
            # prevents the initializer from referencing the variable itself,
            # d permits stuff like this:
            #  var a = 1 in
            #    var a = a in ...   # refers to outer 'a'.
            if expression is not None:
                value = expression.code(context)
            else:
                value = Constant.real(Type.double(), 0)

            alloca = create_alloca_block(function, name)
            context.builder.store(value, alloca)

            # Remember the old variable binding so that we can restore the
            # binding when we unrecurse.
            old_bindings[name] = context.scope.get(name, None)

            # Remember this binding.
            context.scope[name] = alloca

        # Codegen the body, now that all vars are in scope.
        body = self.body.code(context)

        # Pop all our variables from scope.
        for name in self.variables:
            if old_bindings[name] is not None:
                context.scope[name] = old_bindings[name]
            else:
                del context.scope[name]

        # Return the body computation.
        return body
