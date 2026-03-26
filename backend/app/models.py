
# 导入所需模块
import uuid
from datetime import datetime, timezone
from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


# 获取当前UTC时间
def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# 用户基础属性（所有用户相关模型的基类）
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)  # 邮箱，唯一且有索引
    is_active: bool = True  # 是否激活
    is_superuser: bool = False  # 是否为超级用户
    full_name: str | None = Field(default=None, max_length=255)  # 用户全名，可选


# 创建用户时接收的属性
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)  # 密码，8-128位


# 用户注册时接收的属性
class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)  # 邮箱
    password: str = Field(min_length=8, max_length=128)  # 密码
    full_name: str | None = Field(default=None, max_length=255)  # 全名，可选


# 用户更新时接收的属性（全部可选）
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # 邮箱，可选
    password: str | None = Field(default=None, min_length=8, max_length=128)  # 密码，可选


# 用户自助更新信息时的属性
class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)  # 全名
    email: EmailStr | None = Field(default=None, max_length=255)  # 邮箱


# 修改密码时的属性
class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)  # 当前密码
    new_password: str = Field(min_length=8, max_length=128)  # 新密码


# 用户数据库模型（表名自动推断）
class User(UserBase, table=True):
 
    # __tablename__ = "user"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)  # 主键ID，UUID
    hashed_password: str  # 哈希后的密码
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # 创建时间，带时区
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)  # 用户拥有的物品，级联删除


# 通过API返回的用户属性，id必需
class UserPublic(UserBase):
    id: uuid.UUID  # 用户ID
    created_at: datetime | None = None  # 创建时间


# 用户列表返回结构
class UsersPublic(SQLModel):
    data: list[UserPublic]  # 用户数据列表
    count: int  # 总数


# 物品基础属性
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)  # 标题
    description: str | None = Field(default=None, max_length=255)  # 描述，可选


# 创建物品时接收的属性
class ItemCreate(ItemBase):
    pass


# 更新物品时接收的属性
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # 标题可选


# 物品数据库模型（表名自动推断）
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)  # 主键ID，UUID
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # 创建时间，带时区
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"  # 外键，关联用户ID，删除用户时级联删除
    )
    owner: User | None = Relationship(back_populates="items")  # 物品所属用户


# 通过API返回的物品属性，id必需
class ItemPublic(ItemBase):
    id: uuid.UUID  # 物品ID
    owner_id: uuid.UUID  # 所属用户ID
    created_at: datetime | None = None  # 创建时间


# 物品列表返回结构
class ItemsPublic(SQLModel):
    data: list[ItemPublic]  # 物品数据列表
    count: int  # 总数


# 通用消息结构
class Message(SQLModel):
    message: str  # 消息内容


# 包含访问令牌的JSON结构
class Token(SQLModel):
    access_token: str  # 访问令牌
    token_type: str = "bearer"  # 令牌类型


# JWT令牌内容
class TokenPayload(SQLModel):
    sub: str | None = None  # 用户唯一标识


# 重置密码时的结构
class NewPassword(SQLModel):
    token: str  # 重置令牌
    new_password: str = Field(min_length=8, max_length=128)  # 新密码
