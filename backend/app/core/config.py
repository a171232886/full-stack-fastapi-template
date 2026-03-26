
# 导入所需模块
import secrets
import warnings
from typing import Annotated, Any, Literal
from pydantic import (
    AnyUrl,  # 任意URL类型
    BeforeValidator,  # 字段验证前处理
    EmailStr,  # 邮箱类型
    HttpUrl,  # HTTP URL类型
    PostgresDsn,  # Postgres数据库连接字符串
    computed_field,  # 计算属性
    model_validator,  # 模型级验证器
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self



# 解析CORS配置，支持字符串和列表
def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        # 逗号分隔的字符串转为列表
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)



# 应用配置类，继承自Pydantic的BaseSettings
# 注意：仅能读取系统变量和.env文件
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 使用顶层.env文件（位于./backend/上一层）
        # env_file="../.env",
        env_file="/home/wh/code/full-stack-fastapi-template/.env",
        env_ignore_empty=True,  # 忽略空环境变量
        extra="ignore",  # 忽略未声明的额外字段
    )

    API_V1_STR: str = "/api/v1"  # API前缀
    SECRET_KEY: str = secrets.token_urlsafe(32)  # 随机生成的密钥
    # 60分钟 * 24小时 * 8天 = 8天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 访问令牌过期时间（分钟）
    FRONTEND_HOST: str = "http://localhost:5173"  # 前端地址
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"  # 环境类型

    # ============================================================================
    """
    灵活地解析环境变量中配置的跨域来源列表，并自动将当前的“前端主机地址”加入白名单，
    最终生成一个干净的、可供 FastAPI 中间件使用的字符串列表。

    后端允许的CORS来源
    既可以是一个 URL 列表，也可以是一个字符串。
    在 Pydantic 验证数据之前，会先运行一个自定义函数 parse_cors
    """
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []


    """
    在main.py中调用
        app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @computed_field 是 Pydantic V2 引入的特性。
    它的执行时机是在 模型实例化过程中，所有普通字段（包括经过验证和解析的字段）都已经赋值完成后，
    但在 模型实例完全返回给用户使用前 进行计算。

    @computed_field：该字段会被视为模型的一部分, 自动包含在 .model_dump() 或 .model_dump_json() 的结果中。
    """
    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        # 返回所有允许的CORS来源（包括前端）
        # .rstrip("/")：去除末尾的斜杠。
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    # ============================================================================

    PROJECT_NAME: str  # 项目名称
    SENTRY_DSN: HttpUrl | None = None  # Sentry监控DSN
    POSTGRES_SERVER: str  # Postgres服务器地址
    POSTGRES_PORT: int = 5432  # Postgres端口
    POSTGRES_USER: str  # Postgres用户名
    POSTGRES_PASSWORD: str = ""  # Postgres密码
    POSTGRES_DB: str = ""  # Postgres数据库名

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        # 构建SQLAlchemy数据库连接字符串
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True  # 是否启用TLS
    SMTP_SSL: bool = False  # 是否启用SSL
    SMTP_PORT: int = 587  # SMTP端口
    SMTP_HOST: str | None = None  # SMTP服务器
    SMTP_USER: str | None = None  # SMTP用户名
    SMTP_PASSWORD: str | None = None  # SMTP密码
    EMAILS_FROM_EMAIL: EmailStr | None = None  # 发件人邮箱
    EMAILS_FROM_NAME: str | None = None  # 发件人名称

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        # 如果未设置发件人名称，则使用项目名称
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48  # 重置密码令牌有效期（小时）

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        # 判断邮件功能是否启用
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"  # 测试用户邮箱
    FIRST_SUPERUSER: EmailStr  # 首个超级用户邮箱
    FIRST_SUPERUSER_PASSWORD: str  # 首个超级用户密码


    # 检查敏感信息是否为默认值
    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)


    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        # 强制检查关键配置项不能为默认值
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        return self


# 实例化全局配置对象
settings = Settings()  # type: ignore



"""
在 FastAPI（以及一般的 Web 开发）中，CORS 是 Cross-Origin Resource Sharing（跨域资源共享）的缩写。
CORS 是一种浏览器的安全机制，用于限制网页中的脚本（通常是 JavaScript）从当前域名（源）向不同域名（源）发起请求。

前端运行在：http://localhost:3000 (React/Vue 等)
后端运行在：http://localhost:8000 (FastAPI)
虽然都在本地，但端口不同，浏览器视为不同源。如果不加 CORS 配置，前端无法获取后端数据。

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 允许所有来源
    allow_methods=["*"],        # 允许所有 HTTP 方法
    allow_headers=["*"],        # 允许所有请求头
)

"""