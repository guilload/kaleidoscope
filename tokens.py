class Keyword(object):

    @property
    def name(self):
        return self.__class__.__name__.lstrip('_').lower()

    def __str__(self):
        return 'keyword \'{}\''.format(self.name)


class _Def(Keyword):
    pass

Def = _Def()


class _Else(Keyword):
    pass

Else = _Else()


class _For(Keyword):
    pass

For = _For()


class _If(Keyword):
    pass

If = _If()


class _Then(Keyword):
    pass

Then = _Then()


class _Extern(Keyword):
    pass

Extern = _Extern()


KEYWORDS = {k.name: k for k in (Def, Else, For, If, Then, Extern)}


class _EOF(object):

    def __str__(self):
        return 'EOF'

EOF = _EOF()


class Identifier(object):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'identifier \'{}\''.format(self.name)


class Number(object):
    def __init__(self, value):
        self.value = float(value)

    def __str__(self):
        return 'number \'{}\''.format(self.value)


class Char(object):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, basestring):
            return self.value == other
        elif isinstance(other, Char):
            return self.value == other.value
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return 'char \'{}\''.format(self.value)
