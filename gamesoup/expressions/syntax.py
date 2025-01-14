'''
For parsing interface expressions.
'''

import memcache, re, sys
from gamesoup.expressions.context import TemplateContext
from gamesoup.expressions.grammar import Rule


__all__ = (
    'Expr',
    )


class Cached(object):

    @classmethod
    def _clean_key(cls, key):
        if not hasattr(cls, '_mc'):
            cls._mc = memcache.Client(['127.0.0.1:11211'])
        key = key.replace('@', '__at__').replace('+', '__plus__').replace(' ', '')
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        return key

    @classmethod
    def get(cls, key):
        key = cls._clean_key(key)
        return cls._mc.get(key)
    
    @classmethod
    def set(cls, key, value):
        key = cls._clean_key(key)
        return cls._mc.set(key, value)


class Expr(Cached):
    '''
    This class accepts an interface expression (which is a string) and
    parses it into an intermediate data structure.
    '''
    
    #--------------------------------------------------------------------------
    # Instantiation
    
    @classmethod
    def parse(cls, w):
        """
        This is the usual way to instantiate an interface expression
        from a string.
        
        The most basic interface expression is the empty expression,
        to which all other expressions are super. It is represented
        as an empty union set using square brackets.
        
            >>> Expr.parse('[]')
            []
        
        Parsing an empty string will just return the integer 0
        instead of an expression object.
        
            >>> nothing = Expr.parse('')
            >>> nothing
            0
            >>> nothing.__class__.__name__
            'int'
        """
        if isinstance(w, Expr): return w
        if re.match(r'^\s*(?:0)?\s*$', w): return 0
        expr = cls.get(w)
        if expr is None:
            tree = Rule.expr(w)
            expr = cls.from_tree(tree)
            cls.set(w, expr)
        return expr
        
    @classmethod
    def from_tree(cls, tree):
        assert tree[0] == 'EXPR'
        atoms = []
        if tree[1][0] in ('ATOMIC_EXPR', 'BUILT_IN_ID'):
            atoms.append(Atom.from_tree(tree[1]))
        else:
            assert tree[1][0] == 'EXPR_LIST'
            if len(tree[1]) > 1:
                x = tree[1][1]
                while x:
                    atoms.append(Atom.from_tree(x[1]))
                    x = len(x) > 2 and x[2] or None
        return cls.from_atoms(atoms)
        
    @classmethod
    def from_atoms(cls, atoms):
        '''
        Create an expression from a sequence of atoms.
        '''
        expr = cls()
        expr._child = dict([(atom.id, atom) for atom in atoms])
        return expr #cls.unique(expr)
    
    #--------------------------------------------------------------------------
    # Queries
    
    def _get_sorted_atoms(self):
        """
        >>> e = Expr.parse('[D + B + C + A]')
        >>> e.atoms
        [A, B, C, D]
        >>> e.atoms[0].__class__.__name__
        'Atom'
        """
        return sorted(self._child.values(), cmp=cmp_by_id)
    atoms = property(_get_sorted_atoms)
        
    def _get_sorted_ids(self):
        """
        >>> Expr.parse('[D + B + C + A]').ids
        ['A', 'B', 'C', 'D']
        """
        return sorted([atom.id for atom in self._child.values()])
    ids = property(_get_sorted_ids)
    
    def _is_singleton(self):
        """
        >>> Expr.parse('[A]').is_singleton
        True
        >>> Expr.parse('A!').is_singleton
        True
        >>> Expr.parse('[@Type.a]').is_singleton
        True
        >>> Expr.parse('[43.a]').is_singleton
        True
        >>> Expr.parse('[A<item=B>]').is_singleton
        True
        >>> Expr.parse('[A + B]').is_singleton
        False
        """
        return len(self) == 1
    is_singleton = property(_is_singleton)
    
    def _is_built_in(self):
        """
        >>> Expr.parse('A').is_built_in
        False
        >>> Expr.parse('@T.a').is_built_in
        False
        >>> Expr.parse('32.a').is_built_in
        False
        >>> Expr.parse('A!').is_built_in
        True
        >>> Expr.parse('[A<item=A!>]').is_built_in
        False
        """
        return self.is_singleton and self.singleton.is_built_in
    is_built_in = property(_is_built_in)
    
    def _is_var(self):
        """
        >>> Expr.parse('A').is_var
        False
        >>> Expr.parse('A!').is_var
        False
        >>> Expr.parse('@T.a').is_var
        True
        >>> Expr.parse('21.a').is_var
        True
        >>> Expr.parse('[21.a]').is_var
        True
        >>> Expr.parse('[21.a + B]').is_var
        False
        """
        return self.is_singleton and self.singleton.is_var
    is_var = property(_is_var)
    
    def get_singleton(self):
        assert self.is_singleton
        return self.atoms[0]
    singleton = property(get_singleton)
    
    def __repr__(self):
        """
        Produce the normalized representation of this expression. For
        each level of nesting, all identifiers will be sorted
        alphabetically. White space is also normalized.
        
        Normal singleton interfaces and variables are placed within
        square brackets, to indicate that they can be unioned with other
        expressions.
        
            >>> Expr.parse('A')
            [A]
            >>> Expr.parse('@T.a')
            [@T.a]
        
        Built-in interfaces cannot be unioned with other interfaces, so
        they are represented outside of any square brackets.
        
            >>> Expr.parse('A!')
            A!
        """
        if self.is_built_in:
            return `self.singleton`
        return '[%s]' % ' + '.join([`a` for a in self.atoms])
    
    def __len__(self):
        """
        >>> len(Expr.parse('[]'))
        0
        >>> len(Expr.parse('A'))
        1
        >>> len(Expr.parse('A!'))
        1
        >>> len(Expr.parse('[A<item=[P+Q+R]> + B]'))
        2        
        """
        return len(self._child)

    def __nonzero__(self):
        """        
        So that expressions are always evaluated as True. This is useful
        in short-circuited boolean python expressions which first check
        that an expression is not None and then use some property.

        For example:
        
            >>> e = Expr.parse('[A]')
            >>> e and e.is_singleton
            True
        
        Note that even an empty expression evaluates to True:
        
            >>> bool(Expr.parse('[]'))
            True
        
        However the nothing expression, which is not even an
        expression, but 0, will evaluate to False:
        
            >>> bool(Expr.parse(''))
            False
        """
        return True

    #--------------------------------------------------------------------------
    # Composition
    
    def __add__(self, other):
        '''
        >>> a = Expr.parse('[R + S<item=Foo<color=Red, favorite=Murphy>, engine=Electric> + T]')
        >>> b = Expr.parse('[S<item=[Bar + Foo<item=Car, favorite=Fred>]> + T + U]')
        >>> a + b
        [R + S<engine=[Electric], item=[Bar + Foo<color=[Red], favorite=[Fred + Murphy], item=[Car]>]> + T + U]
        '''
        union = []
        for atom1, atom2 in self.join(other):
            if atom1 and atom2 and atom1 != atom2:
                union.append(atom1 + atom2)
            else:
                union.append(atom1 or atom2)
        return Expr.from_atoms(union)

    def __mod__(self, c):
        '''
        Resolve this expression with the template context c.

        >>> from gamesoup.expressions.context import TemplateContext as C
        >>> e = Expr.parse('Bar')
        >>> c = C({
        ...     'A.item': e,
        ...     '@C.item': e,
        ...     '12.item': e,
        ... })        
        >>> e = Expr.parse('[A<item=[]> + B<item=[12.item + Car<item=@C.item>]> + @C.item]')
        >>> e
        [@C.item + A<item=[]> + B<item=[12.item + Car<item=[@C.item]>]>]
        >>> e % c
        [A<item=[Bar]> + B<item=[Bar + Car<item=[Bar]>]> + Bar]
        
        >>> e = Expr.parse('[@C.item + 12.item]')
        >>> e % c
        [Bar]
        
        >>> Expr.parse('Foo<item=[@T.a]>') % C({})
        [Foo<item=[@T.a]>]
        
        >>> Expr.parse('[@T.a]') % C({})
        [@T.a]
        '''
        # Note that atom % c returns an Expr, not an Atom,
        # so taking the sum of a list of Expr will call the
        # __add__ method of Expr.
        return Expr.reduce([atom % c for atom in self.atoms])

    @staticmethod
    def reduce(list_of_exprs):
        '''
        Reduces a list of expressions to a single expression by
        repeatedly taking the union of the result with the first
        expression in the list, until the list is empty.
        
        Reducing an empty list returns the empty expression.
        
            >>> Expr.reduce([])
            []
        
        Reducing a list with a single expressions returns just that
        expression.
        
            >>> Expr.reduce([ Expr.parse('[A+B]') ])
            [A + B]
        
        More complicated examples:
        
            >>> Expr.reduce([ Expr.parse('[A<item=C>]'), Expr.parse('[A<item=D>]'), Expr.parse('B')])
            [A<item=[C + D]> + B]
        '''
        l = len(list_of_exprs)
        if l == 0:
            return Expr.parse('[]')
        elif l == 1:
            return list_of_exprs[0]
        else:
            return reduce(lambda x, y: x + y, list_of_exprs)
    
    #--------------------------------------------------------------------------
    # Comparison
    
    def __gt__(self, other):
        return self.is_super(other)

    def __lt__(self, other):
        return other.is_super(self)

    def __eq__(self, other):
        return `self` == `other`

    def is_super(self, other):
        """
        Is this expression a super expression of other?
        
        If so, any place other is required, this one will work too.
        >>> 1
        2
        >>> r = Expr.parse('Readable')
        >>> w = Expr.parse('Writable')
        >>> r.is_super(r)
        True
        >>> r.is_super(w)
        False
        >>> w.is_super(r)
        False
        >>> (r + w).is_super(w)
        True
        >>> (r + w).is_super(r)
        True
        >>> (r + w).is_super(w + r)
        True

        >>> rs = Expr.parse('Readable<item=String>')
        >>> rs.is_super(r)
        True
        >>> r.is_super(rs)
        False
        >>> rs.is_super(r + w)
        False
        >>> (r + w).is_super(rs)
        False

        >>> c1 = Expr.parse('Foo<bar=[Bar<far=Far,where=[Where+There]>+Car]>')
        >>> c2 = Expr.parse('[Foo<bar=[Bar<far=[Far+War],where=[Here+There+Every+Where],at=Fat>+Car<item=Bitem>+Fat<hat=Cat>]>+Quick]')
        >>> c2.is_super(c1)
        True
        >>> c1.is_super(c2)
        False
        """
        for atom1, atom2 in self.join(other):
            if atom1 and atom2 and not atom1.is_super(atom2):
                return False
            if not atom1 and atom2:
                return False
        return True

    def resolvent_for(self, other):
        """
        Attempts to compute and return minimal resolvent that
        will make (self % resolvent).is_super(other). If no such
        resolvent exists a resolvent will still be returned, but
        (self % resolvent) will not be super to other.

        >>> f1 = Expr.parse('Foo<item=[@T.a]>')
        >>> f2 = Expr.parse('Foo<item=[Bar]>')
        >>> f3 = Expr.parse('Bar<item=[]>')
        >>> f2.resolvent_for(f1)
        <BLANKLINE>
        >>> f1.resolvent_for(f2)
        @T.a : [Bar]
        >>> f1 % f1.resolvent_for(f2)
        [Foo<item=[Bar]>]
        >>> f1.resolvent_for(f3)
        <BLANKLINE>        

        >>> f1 % f1.resolvent_for(f3)
        [Foo<item=[@T.a]>]
        
        >>> a = Expr.parse('@T.a')
        >>> b = Expr.parse('Bar')
        >>> a.resolvent_for(b)
        @T.a : [Bar]
        >>> b.resolvent_for(a)
        <BLANKLINE>
        >>> b % b.resolvent_for(a)
        [Bar]
        
        >>> Expr.parse(
        ...     '[A<x=@T.pain> + B<x=T!> + C<x=D<x=12.foo>> + D]'
        ... ).resolvent_for(Expr.parse(
        ...     '[A<x=[Q+R]> + C<x=D<x=Q>> + B<x=S!>]'
        ... ))
        12.foo : [Q]
        @T.pain : [Q + R]        
        """
        c = TemplateContext({})
        if self.is_var:
            c[self.atoms[0].id] = other
        else:
            for atom1, atom2 in self.join(other):
                if atom1 and atom2:
                    c.update(atom1.resolvent_for(atom2))
        return c

    def join(self, other):
        return _join(self, other, '_child', 'ids')


class Atom(Cached):
    
    #--------------------------------------------------------------------------
    # Instantiation
    
    @classmethod
    def from_tree(cls, tree):
        if tree[0] == 'ATOMIC_EXPR':
            assert tree[1][0] in ('INTERFACE_ID', 'VARIABLE')
            if tree[1][0] == 'INTERFACE_ID':
                args = []
                if len(tree) > 2:
                    x = tree[2]
                    assert x[0] == 'ARG_LIST_PART'
                    while x:
                        args.append(Arg.from_tree(x[1]))
                        x = len(x) > 2 and x[2] or None
                return cls.from_args(args, id=tree[1][1])
            else: # tree[1][0] == 'VARIABLE'
                assert tree[1][1][0] in ('INTERFACE_ID', 'TYPE_ID', 'OBJECT_ID')
                assert tree[1][2][0] == 'VARIABLE_ID'
                id = '%s.%s' % (tree[1][1][1], tree[1][2][1])
                return cls.from_args([], id=id, var_type=tree[1][1][0][:-3].lower())
        else:
            assert tree[0] == 'BUILT_IN_ID'
            return cls.from_args([], id=tree[1], is_built_in=True)
    
    @classmethod
    def from_args(cls, args, id, var_type=None, is_built_in=False):
        atom = cls()
        atom._id = id
        atom._var_type = var_type
        atom._is_built_in = is_built_in
        atom._arg = dict([(arg.id, arg) for arg in args])
        return atom #cls.unique(atom)

    #--------------------------------------------------------------------------
    # Queries
    
    is_var = property(lambda self: self._var_type is not None)
    is_interface_var = property(lambda self: self._var_type == 'interface')
    is_type_var = property(lambda self: self._var_type == 'type')
    is_object_var = property(lambda self: self._var_type == 'object')
    var_type = property(lambda self: self._var_type)
    id = property(lambda self: self._id)
    is_built_in = property(lambda self: self._is_built_in)

    def get_sorted_param_ids(self):
        return sorted(self._arg.keys())
    param_ids = property(get_sorted_param_ids)
    
    def get_sorted_args(self):
        return sorted(self._arg.values(), cmp=cmp_by_id)
    args = property(get_sorted_args)

    def __repr__(self):    
        w = self.id
        if self._arg:
            w += '<%s>' % ', '.join([`arg` for arg in self.args])
        return w

    def __len__(self):
        return len(self._arg)

    def __nonzero__(self):
        return True
    
    #--------------------------------------------------------------------------
    # Composition

    def __add__(self, other):
        assert self.id == other.id
        assert self.var_type == other.var_type
        union = []
        for arg1, arg2 in self.join(other):
            if arg1 and arg2 and arg1 != arg2:
                union.append(arg1 + arg2)
            else:
                union.append(arg1 or arg2)
        return Atom.from_args(union, id=self.id, var_type=self.var_type)
    
    def __mod__(self, c):
        """
        Resolve this atom with the template context c.
        Returns an Expr, not an Atom.

        >>> from gamesoup.expressions.context import TemplateContext as C
        >>> a = Arg.from_expr(Expr.parse('[]'), id='item')
        >>> e = Expr.parse('Bar')
        >>> c = C({
        ...     'Foo.item': e,
        ...     '@Foo.item': e,
        ...     '12.item': e,
        ... })
        >>> atom = Atom.from_args([a], id='Foo')
        >>> atom
        Foo<item=[]>
        >>> atom % c
        [Foo<item=[Bar]>]
        
        >>> atom = Atom.from_args([], id='@Foo.item', var_type='type')
        >>> atom
        @Foo.item
        >>> atom % c
        [Bar]

        >>> atom = Atom.from_args([], id='12.item', var_type='object')
        >>> atom
        12.item
        >>> atom % c
        [Bar]
        
        >>> atom = Atom.from_args([], id='Integer!', is_built_in=True)
        >>> atom
        Integer!
        >>> atom % c
        Integer!
        >>> (atom % c).__class__.__name__
        'Expr'
        
        >>> atom = Expr.parse('B<item=[12.item + Car<item=@C.item>]>').atoms[0]
        >>> atom
        B<item=[12.item + Car<item=[@C.item]>]>
        >>> atom % C({'12.item': e, '@C.item': e})
        [B<item=[Bar + Car<item=[Bar]>]>]
        
        >>> Expr.parse('[@T.a]').atoms[0] % C({})
        [@T.a]
        """
        if self.is_built_in:
            # Can't resolve a built-in 
            return Expr.from_atoms([self])
        elif self.is_var:
            # Try to resolve this atom directly with the context
            if self.id in c:
                return c[self.id]
            else:
                return Expr.from_atoms([self])
        else:
            # Try to resolve any interface template arguments
            if len(self) == 0:
                # If there are no args, can't resolve anything
                return Expr.from_atoms([self])
            # Note that arg % c returns an Arg
            args = [arg.resolve(c, interface_name=self.id) for arg in self.args]
            return Expr.from_atoms([Atom.from_args(args, id=self.id)])

    #--------------------------------------------------------------------------
    # Comparison

    def is_super(self, other):
        for arg1, arg2 in self.join(other):
            if arg1 and arg2 and not arg1.expr.is_super(arg2.expr):
                return False
            if not arg1 and arg2:
                return False
        return True

    def resolvent_for(self, other):
        """
        Resolve self to other.

        >>> f1 = Expr.parse('Foo<item=12.item>').atoms[0]
        >>> f2 = Expr.parse('Foo<item=Bar>').atoms[0]
        >>> f3 = Expr.parse('Foo<item=Car>').atoms[0]
        >>> f2.resolvent_for(f1)
        <BLANKLINE>
        >>> f1.resolvent_for(f2)
        12.item : [Bar]
        >>> f2.resolvent_for(f3)
        <BLANKLINE>
        >>> f1.resolvent_for(f3 + f2)
        12.item : [Bar + Car]
        """
        c = TemplateContext({})
        if self.is_built_in:
            pass
        elif self.is_var:
            c[self.id] = other
        else:
            for arg1, arg2 in self.join(other):
                if arg1 and arg2:
                    c.update(arg1.expr.resolvent_for(arg2.expr))
        return c

    def join(self, other):
        return _join(self, other, '_arg', 'param_ids')        
    

class Arg(Cached):
    
    #--------------------------------------------------------------------------
    # Instantiation
    
    @classmethod
    def from_tree(cls, tree):
        assert tree[0] == 'ARG'
        assert tree[1][0] == 'VARIABLE_ID'
        assert tree[2][0] == 'EXPR'        
        expr = Expr.from_tree(tree[2])
        return cls.from_expr(expr, id=tree[1][1])

    @classmethod
    def from_expr(cls, expr, id):
        arg = cls()
        arg._id = id
        arg._expr = expr
        return arg #cls.unique(arg)
    
    #--------------------------------------------------------------------------
    # Queries
    
    id = property(lambda self: self._id)
    expr = property(lambda self: self._expr)

    def __repr__(self):
        return '%s=%s' % (self.id, `self.expr`)
        
    def __nonzero__(self):
        return True
    
    #--------------------------------------------------------------------------
    # Composition
    
    def __add__(self, other):
        assert self.id == other.id
        expr = self.expr + other.expr
        return Arg.from_expr(expr, id=self.id)

    def resolve(self, c, interface_name):
        """
        Resolve this arg with the template context c.
        Returns an Arg.
        
        >>> from gamesoup.expressions.context import TemplateContext as C
        >>> a = Arg.from_expr(Expr.parse('[]'), id='item')
        >>> a
        item=[]
        >>> a.resolve(C({'Foo.item': Expr.parse('Bar')}), interface_name='Foo')
        item=[Bar]
        
        >>> Expr.parse('Foo<item=[@T.a]>').atoms[0].args[0].resolve(C({}), interface_name='Foo')
        item=[@T.a]
        """
        key = '.'.join([interface_name, self.id])
        if key in c:
            return Arg.from_expr(c[key], id=self.id)
        else:
            return Arg.from_expr(self.expr % c, id=self.id)
    
    #--------------------------------------------------------------------------
    # Comparison

    def __gt__(self, other):
        return True


def cmp_by_id(x, y):
    return cmp(x.id, y.id)


def _join(a, b, d, ids):
    """
    Iterates through children of two components in pairs (x, y),
    where x is from a and y is from b, and both have the same
    identifier. Note that x or y may be None, but not both.
    
    a, b    - Expr or Atom
    d       - name of attribute which is a dictionary
              mapping ids to children
    ids     - name of attribute which is a list of ids
    """
    for id in set(getattr(a, ids)) | set(getattr(b, ids)):
        yield getattr(a, d).get(id, None), getattr(b, d).get(id, None)


__test__ = {'doctest': """
>>> from gamesoup.expressions.syntax import Expr

Here is an example:

    >>> obj = Expr.parse('Iterable<item=Readable<item=1.over>>')
    >>> param = Expr.parse('Iterable<item=Readable<item=Clearable>>')
    >>> resolvent = obj.resolvent_for(param)
    >>> resolvent
    1.over : [Clearable]

Now say we lookup the minimum interface required by the type template
parameter "over" and find it to be "[Drivable]". That's is no good,
because:

    >>> Expr.parse('Clearable') > Expr.parse('Drivable')
    False

because after applying the resolvent:

    >>> obj_after = obj % resolvent
    >>> obj_after > param
    True
    
In order to get this algorithm implemented. I need to do the following:

    1)

I have a general purpose type called
    @List<item=[]>
which implements
    [Iterable<item=@List.item[]> + Stack<item=@List.item[]>]
    
Then I have
    @Copier<item=[]>
which implements
    [Action]
and has parameters
    src :   [Iterable<item=Readable<item=@Copier.item[]>>]
    dest:   [Stack<item=@Copier.item[]>]

A copier reads data from its source and pushes it onto its
destination.

I instantiate a @List object
    1   :   [Iterable<item=@List.item[]> + Stack<item=@List.item[]>]
and a @Copier object
    2   :   [Action]
        src :   [Iterable<item=Readable<item=@Copier.item[]>>]
        dest:   [Stack<item=@Copier.item[]>]

Note that
    1.expr.is_super(2.dest)
because

    >>> Expr.parse('[Iterable<item=[]> + Stack<item=[]>]').is_super(Expr.parse('[Stack<item=[]>]'))
    True

and that although
    not 1.expr.is_super(2.src)
because

    >>> Expr.parse('[Iterable<item=[]> + Stack<item=[]>]').is_super(Expr.parse('[Iterable<item=Readable<item=[]>>]'))
    False

if we bind
    1.item from [] to [Readable<item=2.item[]>]
then

    >>> Expr.parse('[Iterable<item=Readable<item=[]>> + Stack<item=Readable<item=[]>>]').is_super(Expr.parse('[Iterable<item=Readable<item=[]>>]'))
    True

Now the expression for 1 is
    [Iterable<item=[Readable<item=2.item[]>]> + Stack<item=[Readable<item=2.item[]>]>]
This expression involves one of 2's template variables.
"""
}
