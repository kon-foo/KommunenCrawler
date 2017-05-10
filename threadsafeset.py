from threading import Lock

def lock_class(methodnames, lockfactory):
    return lambda cls: make_threadsafe(cls, methodnames, lockfactory)

def lock_method(method):
    if getattr(method, '__is_locked', False):
        raise TypeError("Method %r is already locked!" % method)
    def locked_method(self, *arg, **kwarg):
        with self._lock:
            return method(self, *arg, **kwarg)
    locked_method.__name__ = '%s(%s)' % ('lock_method', method.__name__)
    locked_method.__is_locked = True
    return locked_method


def make_threadsafe(cls, methodnames, lockfactory):
    init = cls.__init__
    def newinit(self, *arg, **kwarg):
        init(self, *arg, **kwarg)
        self._lock = lockfactory()
    cls.__init__ = newinit

    for methodname in methodnames:
        oldmethod = getattr(cls, methodname)
        newmethod = lock_method(oldmethod)
        setattr(cls, methodname, newmethod)

    return cls


@lock_class(['add','remove','__contains__','pop','copy'], Lock)
class LockedSet(set):
    @lock_method # if you double-lock a method, a TypeError is raised
    def frobnify(self):
        pass

if __name__ == '__main__':
    a = LockedSet(set())
    a.add('A')
    if a.__contains__('A'):
        print('True')
    if a.__contains__('B'):
        print('B')
    for el in a:
        print(el)
    print(len(a))
