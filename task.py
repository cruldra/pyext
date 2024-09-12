import traceback
from dataclasses import dataclass
from typing import Callable, Any, Optional
import uuid

from loguru import logger
from pydantic import BaseModel
import wrapt


# region 任务阶段模型
class Stage(BaseModel):
    """
    表示任务执行过程中的某个阶段,用于记录任务执行过程中的状态和信息。
    """

    name: str
    """ 阶段名称 """
    message: Optional[str] = None
    """ 阶段信息 """
    data: Optional[Any] = None
    """ 阶段数据 """
    error: Optional[Any] = None
    """ 阶段错误 """

    def to_dict(self):
        return {"name": self.name, "message": self.message}

    @property
    def is_completed(self):
        """
        阶段是否已完成。
        """
        return self.name in ["success_completed", "failed_completed"]

    @classmethod
    def running(cls, message: str = "None"):
        """
        创建一个表示正在运行的阶段的实例。
        """
        return cls(name="running", message=message)

    @classmethod
    def success(cls, message: str = None, data: Any = None):
        """
        创建一个表示成功的阶段的实例。
        """
        return cls(name="success", message=message, data=data)

    @classmethod
    def failed(cls, message: str = None, error: Exception = None):
        """
        创建一个表示失败的阶段的实例。
        """
        return cls(
            name="failed", message=message if message else str(error), error=error
        )

    @classmethod
    def success_completed(cls, message: str = None, data: Any = None):
        """
        任务(包括子任务已全部完成)，无论成功还是失败。
        """
        return cls(name="success_completed", message=message, data=data)

    @classmethod
    def failed_completed(cls, message: str = None, error: Exception = None):
        """
        任务(包括子任务已全部完成)，无论成功还是失败。
        """
        return cls(name="failed_completed", message=message, error=error)


# endregion


# region 任务树模型
class Task:
    """
    表示一个任务
    """

    def __init__(
        self,
        title: str,
        executable: Callable = None,
        context: Any = None,
        children: list["Task"] = None,
        parent: "Task" = None,
    ):
        self.title = title
        """ 任务的标题 """
        self.executable = executable
        """ 任务的执行函数 """
        self.context = context
        """ 任务的上下文 """
        self.children = children
        """ 子任务 """
        self.parent = parent
        """ 父任务 """
        self.id = str(uuid.uuid4())
        """ 任务的唯一标识 """
        self.stage: Stage|None = None
        """ 任务当前所在的阶段 """

    def get_ancestors(self) -> list["Task"]:
        """
        返回此任务的所有祖先任务的列表，按从最远祖先到最近祖先的顺序排列
        """

        def collect_ancestors(task: "Task", ancestors: list["Task"]):
            if task.parent:
                collect_ancestors(task.parent, ancestors)
                ancestors.append(task.parent)

        result = []
        collect_ancestors(self, result)
        return result

    def to_dict(self) -> dict:
        """
        将任务转换为字典,仅保留id,title,children三个字段

        Returns:
            dict: 任务的字典表示
        """
        return {
            "id": self.id,
            "title": self.title,
            "stage": self.stage.to_dict() if self.stage else None,
            "children": (
                [child.to_dict() for child in self.children] if self.children else None
            ),
        }

    def organize_hierarchy(self):
        """
        梳理该任务及其子任务的层次结构
        """
        if self.children:
            for child in self.children:
                child.organize_hierarchy()
                child.parent = self

    # region 执行任务树
    def run_sync(
        self, on_stage_change: Callable[[Stage, "Task"], None] = None, last_result=None
    ) -> Any:
        """
        并行执行此任务及其子任务,任务的执行顺序由放入任务树的顺序决定

        Args:
            on_stage_change (Callable[[Stage], None], optional): 阶段变化时的回调函数. Defaults to None.
            last_result (Any, optional): 上一个任务的执行结果. Defaults to None.

        Returns:
            Any: 返回最后一个任务的执行结果
        """
        # 遍历任务树中包含有效执行函数的任务,遵从放入任务树的顺序
        tasks: list[Task] = []

        def _run_sync(task: "Task"):
            if task.executable:
                tasks.append(task)
            if task.children:
                for child in task.children:
                    _run_sync(child)

        _run_sync(self)

        def find_context(task: "Task"):
            """
            递归查找任务的上下文。如果任务本身有上下文,则返回该上下文;否则,递归查找父任务的上下文,直到找到根任务为止。

            Args:
                task (Task): 要查找上下文的任务

            Returns:
                Any: 任务的上下文,如果找不到则返回 None
            """
            if task.context:
                return task.context
            if task.parent:
                return find_context(task.parent)
            return None

        def update_stage(task: Task, stage: Stage):
            """
            更新任务的阶段
            """
            task.stage = stage
            if on_stage_change:
                for ancesto_task in task.get_ancestors():
                    stage_dict = stage.model_dump()
                    stage_dict["message"] = None
                    ancesto_task.stage = Stage(**stage_dict)
                    on_stage_change(ancesto_task.stage, ancesto_task)
                on_stage_change(stage, task)

        last_error = None
        try:
            for task in tasks:
                try:
                    update_stage(task, Stage.running(f"Running task [{task.title}]..."))
                    last_result = task.executable(find_context(task), last_result)
                    update_stage(task, Stage.success(f"Task [{task.title}] succeeded."))
                except Exception as e:
                    logger.error(str(e))
                    traceback.print_exc()
                    update_stage(task, Stage.failed(f"Task [{task.title}] failed.", e))
                    last_error = e
                    raise e
        finally:
            if last_error:
                stage = Stage.failed_completed(
                    f"Task [{self.title}] failed.", last_error
                )
            else:
                stage = Stage.success_completed(
                    f"Task [{self.title}] completed.", last_result
                )
            update_stage(self, stage)

        return last_result

    # endregion


# endregion


# region 任务装饰器
def task(title: str, context: Any = None, dependencies: list[Callable] = None):
    @wrapt.decorator
    def decorator(wrapped, instance, args, kwargs):

        if dependencies:
            root_task = Task(title, None, context)
            dependent_tasks: list[Task] = [f() for f in dependencies]
            for dependent_task in dependent_tasks:
                dependent_task.parent = root_task
            dependent_tasks.append(Task(title, wrapped, parent=root_task))
            root_task.children = dependent_tasks
            return root_task
        else:
            return Task(title, wrapped, context)

    return decorator


# endregion
