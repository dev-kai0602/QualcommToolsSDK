""" 这个模块包含了空函数，会接收值但不做任何处理，用于替换旧代码中的一些输出/日志函数

"""

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
