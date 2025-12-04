class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def singleton(cls):
    ns = dict(cls.__dict__)
    ns.pop("__dict__", None)
    ns.pop("__weakref__", None)
    return SingletonMeta(cls.__name__, cls.__bases__, ns)
