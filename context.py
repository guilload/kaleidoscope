from llvm.core import Module


class Context(object):
    def __init__(self, name, module=None, builder=None, scope=None):
        self.name = name
        self.module = module or Module.new(name)
        self.builder = builder
        self.scope = scope or {}
