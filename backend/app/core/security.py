from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# 初始化密码哈希处理器
# 配置为优先使用 Argon2 算法（更安全、现代），同时兼容 Bcrypt 算法
# 这样可以在验证旧密码（可能是 Bcrypt 加密的）时正常工作，
# 而新密码或更新后的密码将使用 Argon2 加密。
password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)

# JWT 签名算法：使用 HS256 (HMAC with SHA-256)
ALGORITHM = "HS256"

"""
Header.Payload.Signature
  |       |        |
  v       v        v
算法声明  用户数据   防篡改校验
( Base64 ) ( Base64 ) ( 哈希值 )
"""


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    """
    创建 JWT Access Token
    
    :param subject: 令牌的主题，通常是用户ID或用户名，会被转换为字符串
    :param expires_delta: 令牌的有效期时长 (timedelta 对象)
    :return: 编码后的 JWT 字符串
    """
    # 计算过期时间：当前 UTC 时间 + 有效期时长
    expire = datetime.now(timezone.utc) + expires_delta
    
    # 构建 JWT payload (负载)
    # 'exp': 过期时间戳 (jwt 库会自动识别并验证此字段)
    # 'sub': 主题 (Subject)，标识该令牌属于哪个用户
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # 使用密钥 (SECRET_KEY) 和算法对 payload 进行编码签名
    # settings.SECRET_KEY 应从环境变量或配置文件中安全获取
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    """
    验证明文密码是否与哈希密码匹配，并检查是否需要重新哈希
    
    :param plain_password: 用户输入的明文密码
    :param hashed_password: 数据库中存储的哈希密码
    :return: 返回一个元组 (匹配结果, 新的哈希值)
             - 如果匹配且算法/参数已过时，第二个元素为新的哈希字符串（需更新数据库）
             - 如果匹配且无需更新，第二个元素为 None
             - 如果不匹配，第一个元素为 False，第二个元素通常为 None
    """
    # verify_and_update 是 pwdlib 的核心方法
    # 它不仅验证密码，还会在检测到哈希算法升级或参数变强时，自动计算新的哈希值
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    对明文密码进行哈希处理，用于注册或修改密码时存储
    
    :param password: 用户的明文密码
    :return: 哈希后的密码字符串
    """
    # 使用配置的哈希策略（优先 Argon2）对密码进行哈希
    return password_hash.hash(password)
