from typing import Callable, Any


class Task:
    """
    表示一个任务
    """

    def __init__(self,title:str, executable: Callable, context: Any= None, children: list['Task'] = None):
        self.title = title
        self.executable = executable
        self.context = context
        self.children = children
