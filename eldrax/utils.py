import functools


def memoize(func):
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        memo = self.__dict__.setdefault("memo", {})
        key = (func.__name__, args)
        if key in memo:
            value = memo[key]
        else:
            value = func(self, *args, **kwargs)
            memo[key] = value
        return value
    return wrapped
