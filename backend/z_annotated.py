from typing import Annotated, get_args, get_origin
import inspect

# 1. 定义一个自定义标签类
class LogTag:
    def __init__(self, message):
        self.message = message

# 2. 定义带标签的类型
MyInt = Annotated[int, LogTag("这是一个被监控的整数")]

# 3. 编写一个“微型框架”函数来消费它
def process(value: MyInt):
    # 获取类型注解
    hints = inspect.get_annotations(process)
    arg_type = hints['value']
    
    # 检查是否是 Annotated
    if get_origin(arg_type) is Annotated:
        args = get_args(arg_type)
        # 遍历后面的参数
        for metadata in args[1:]:
            if isinstance(metadata, LogTag):
                # 触发逻辑！
                print(f"🔥 日志系统触发: {metadata.message}")
    
    print(f"处理数值: {value}")

# 运行
process(100)