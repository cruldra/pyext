from typing import Any, Callable, Iterable, TypeVar


T = TypeVar("T", bound="Any")


class Collection(object):
    """
    表示一个集合
    """

    def __init__(self, *args: T):
        self.value = list(args)

    def inserts(self, index:int,*args:T )->'Collection[T]':
        """
        在指定位置插入一个子集合,如果插入位置已有元素，将它们移动到子数组之后

        Args:
            index: 插入位置
            args: 要插入的元素

        Returns:
            Collection[T]: 插入后的集合
        """
        pass

    def map(self, func: Callable[[T], T]) -> 'Collection[T]':
        """
        对集合中的每个元素应用一个函数，并返回一个新的集合
        Args:
            func: 要应用的函数
        Returns:
                Collection[T]: 应用函数后的新集合
        """
        pass


class List(Collection):
    """
    表示一个列表
    """

    def __init__(self, *args: T):
        super().__init__(*args)


    def inserts(self, index: int, *args: T):
        new_list = self.value[:index] + list(args) + self.value[index:]
        return List(*new_list)
    
    def map(self, func: Callable[[T], T]) -> 'List[T]':
        """
        对集合中的每个元素应用一个函数，并返回一个新的集合
        Args:
            func: 要应用的函数
        Returns:
                Collection[T]: 应用函数后的新集合
        """
        return List(*map(func, self.value))
        
