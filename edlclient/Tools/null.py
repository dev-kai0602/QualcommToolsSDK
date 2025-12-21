""" 这个模块包含了空函数，会接收值但不做任何处理，用于替换旧代码中的一些输出/日志函数

"""

class NullObject:
    """ 空类

    Args:
        *args: 参数
        **kwargs: 参数

    """

    def __init__(self, *args, **kwargs):
        self.level = ''

    def FileHandler(self, *args, **kwargs) -> None:
        """ 空方法

        Args:
            *args: 参数
            **kwargs: 参数

        """
        pass

    def addHandler(self, *args, **kwargs) -> None:
        """ 空方法

        Args:
            *args: 参数
            **kwargs: 参数

        """
        pass

    def setLevel(self, *args, **kwargs) -> None:
        """ 空方法

        Args:
            *args: 参数
            **kwargs: 参数

        """
        pass


def null_function(*args, **kwargs):
    """ 空函数，会接收值但不做任何处理

    Args:
        *args: 参数
        **kwargs: 参数

    Return:
        null_function: 空函数

    """
    return null_function


def null_print(*args, **kwargs) -> None:
    """ 自定义print函数，用于替换旧代码中的print函数，阻止输出

    Args:
        *args: 参数
        **kwargs: 参数

    Return:
        None

    """
    pass
