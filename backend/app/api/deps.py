from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        # 如果有问题直接抛出异常
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user



"""
关于Annotated 和 Depends 的组合使用
1. Annotated 两部分参数 [类型，元参数1, 元参数2]
    - 每个元参数可以是python的任意对象
    - 每个框架（fastapi，sqlalchemy）运行时只读取自己看得懂的元参数，忽略看不懂的元参数，
        然后对元参数进行进一步处理
   类型像是“物品名称”， 各种元参数像是"不同语言的说明书"，框架像是说不同语言的人。中国人只看中文，不会看俄文

2. Depends() 会预先执行，并返回对应的结果

3. 当你在路由函数中声明 session: SessionDep 时，FastAPI 会执行以下逻辑：
- 启动阶段：
    FastAPI 检测到 get_db 是一个生成器函数（因为它包含 yield）。
    它调用 get_db()，获取生成器对象。
    它调用 next(generator)。
    代码执行到 with Session(engine) as session: 进入上下文，然后停在 yield session。
    yield 右边的 session 对象被提取出来，注入到你的路由函数参数 session 中。
    此时，你的路由函数 read_users 开始执行。
- 执行阶段：
    你的业务逻辑运行（查询数据库、处理数据）。
    逻辑运行完毕，返回结果。
- 清理阶段（关键！）：
    一旦路由函数执行结束（无论成功还是抛出异常），FastAPI 会捕获这个信号。
    它再次调用 next(generator)（或者更准确地说是处理生成器的关闭逻辑）。
    这会让生成器代码从 yield 处恢复执行。
    代码继续向下运行，遇到 with 语句块的结束。
    with 语句块会自动触发 session.close()（因为 Session 对象实现了 __exit__ 方法）。
    生成器运行结束，抛出 StopIteration。
- 结论：FastAPI 帮你调用了两次 next()。第一次是为了取值，第二次（在请求结束后）是为了清理。


=========================================================================================


很多开发者容易混淆 **OAuth2**、**JWT** 和 **密码登录**，因为它们经常一起出现。

简单来说：

- **密码登录** 是**验证身份的方式**（你告诉我你是谁，密码是什么）。
- **JWT** 是**令牌（Token）的格式**（就像一张特定样式的防伪身份证）。
- **OAuth2** 是**授权框架/协议**（一套规则，规定了你如何获取这张身份证，以及拿着这张身份证能干什么）。



在 OAuth2 协议中，有几种不同的“模式”（Grant Types），适用于不同场景：

- **授权码模式** (Authorization Code)：最安全，用于网页跳转登录（如“使用 Google 登录”）。

- 密码模式 (Password Grant)：

  用户直接把用户名密码给客户端，客户端转交给服务器换 Token。

  - *适用场景*：你自己开发的前端（信任的客户端），或者内部工具、脚本。
  - 流程：
    1. 前端收集用户输入的账号密码。
    2. 前端调用 `tokenUrl` (即 `/login/access-token`)，发送账号密码。
    3. 后端验证密码，生成 **JWT**，返回给前端。
    4. 前端后续请求都在 Header 带上 `Authorization: Bearer <JWT>`。
    5. 后端的 `OAuth2PasswordBearer` 拦截请求，提取 JWT 并验证。



#### **作为“依赖项” (实际运行时的守卫)**

```python
@app.get("/users/me")
async def read_users_me(current_user: str = Depends(reusable_oauth2)):
    return {"user": current_user}
```

此时，`reusable_oauth2` 对象内部的逻辑会被触发，执行以下**运行时任务**：

1. **拦截请求**：在您的函数 `read_users_me` 运行之前，FastAPI 先运行这个对象定义的逻辑。
2. **查找 Token**：它会自动去 HTTP 请求头（Header）里找 `Authorization` 字段。
3. 验证格式：检查是否是 `Bearer <token>`格式。
   - 如果**没找到** Token -> 直接返回 `401 Unauthorized`，你的函数根本不会执行。
   - 如果**格式不对** -> 返回 `401`。
4. **提取并传递**：如果一切正常，它会**提取出 token 字符串**（注意：此时它还**没有**验证这个 token 是不是合法的 JWT，也没解码，它只是把字符串拿出来了），然后把这串字符赋值给函数的参数 `current_user`。



**注意**：`OAuth2PasswordBearer` 默认只负责**提取** Token 字符串。


"""