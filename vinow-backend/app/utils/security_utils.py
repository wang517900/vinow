交易系统

import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# 配置日志
logger = logging.getLogger(__name__)

# 初始化密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_signature(data: Dict[str, Any], secret: str, signature: str) -> bool:
    """
    验证HMAC签名
    
    Args:
        data (Dict[str, Any]): 待验证的数据字典
        secret (str): 签名密钥
        signature (str): 待验证的签名
    
    Returns:
        bool: 签名验证结果，True表示验证通过
    
    Example:
        >>> data = {"amount": 100, "order_id": "123"}
        >>> secret = "my_secret"
        >>> sig = generate_signature(data, secret)
        >>> verify_signature(data, secret, sig)
        True
    """
    try:
        # 按字典序排序参数，排除signature字段本身
        sorted_params = sorted(data.items())
        message = "&".join([f"{k}={v}" for k, v in sorted_params if k != "signature"])
        
        # 计算HMAC-SHA256签名
        expected_signature = hmac.new(
            secret.encode('utf-8'), 
            message.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()
        
        # 使用安全的比较方法防止时序攻击
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Signature verification failed: {str(e)}")
        return False

def generate_signature(data: Dict[str, Any], secret: str) -> str:
    """
    生成HMAC-SHA256签名
    
    Args:
        data (Dict[str, Any]): 需要签名的数据字典
        secret (str): 签名密钥
    
    Returns:
        str: 生成的十六进制签名字符串
    
    Example:
        >>> data = {"amount": 100, "order_id": "123"}
        >>> secret = "my_secret"
        >>> generate_signature(data, secret)
        'a1b2c3d4e5f6...'
    """
    try:
        # 按字典序排序所有参数
        sorted_params = sorted(data.items())
        message = "&".join([f"{k}={v}" for k, v in sorted_params])
        
        # 生成HMAC-SHA256签名
        signature = hmac.new(
            secret.encode('utf-8'), 
            message.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()
        
        return signature
    except Exception as e:
        logger.error(f"Signature generation failed: {str(e)}")
        raise

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌
    
    Args:
        data (dict): 要编码到token中的数据
        expires_delta (Optional[timedelta]): token过期时间增量
    
    Returns:
        str: JWT token字符串
    
    Raises:
        Exception: 当token创建失败时抛出异常
    
    Example:
        >>> data = {"sub": "user123", "scopes": ["read"]}
        >>> token = create_access_token(data)
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    try:
        to_encode = data.copy()
        
        # 设置过期时间
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        
        # 编码JWT token
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.secret_key, 
            algorithm=settings.algorithm
        )
        
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token creation failed: {str(e)}")
        raise

def verify_token(token: str) -> Optional[dict]:
    """
    验证JWT token的有效性
    
    Args:
        token (str): 待验证的JWT token
    
    Returns:
        Optional[dict]: 如果验证成功返回payload，否则返回None
    
    Example:
        >>> payload = verify_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        >>> if payload:
        ...     print(f"User ID: {payload.get('sub')}")
    """
    try:
        # 解码并验证JWT token
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        return None

def hash_password(password: str) -> str:
    """
    使用bcrypt算法哈希密码
    
    Args:
        password (str): 明文密码
    
    Returns:
        str: 哈希后的密码
    
    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> print(hashed.startswith("$2b$"))
        True
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {str(e)}")
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    
    Args:
        plain_password (str): 明文密码
        hashed_password (str): 哈希后的密码
    
    Returns:
        bool: 密码匹配返回True，否则返回False
    
    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> verify_password("my_secure_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {str(e)}")
        return False

def generate_api_key() -> str:
    """
    生成安全的API密钥
    
    Returns:
        str: 生成的API密钥，使用URL安全的base64编码
    
    Example:
        >>> key = generate_api_key()
        >>> len(key) >= 32
        True
    """
    try:
        # 生成32字节的随机密钥，转换为URL安全的base64字符串
        return secrets.token_urlsafe(32)
    except Exception as e:
        logger.error(f"API key generation failed: {str(e)}")
        raise

def validate_ip_address(ip: str, allowed_ips: List[str]) -> bool:
    """
    验证IP地址是否在白名单中
    
    Args:
        ip (str): 待验证的IP地址
        allowed_ips (List[str]): 允许的IP地址列表
    
    Returns:
        bool: IP地址在白名单中返回True，否则返回False
    
    Example:
        >>> validate_ip_address("192.168.1.1", ["192.168.1.1", "10.0.0.1"])
        True
        >>> validate_ip_address("192.168.1.2", ["192.168.1.1", "10.0.0.1"])
        False
    """
    try:
        # 基本的IP白名单验证
        return ip in allowed_ips
    except Exception as e:
        logger.error(f"IP validation failed: {str(e)}")
        return False

# 新增的安全工具函数

def generate_secure_token(length: int = 32) -> str:
    """
    生成安全的随机令牌
    
    Args:
        length (int): 令牌长度（字节），默认32字节
        
    Returns:
        str: 十六进制格式的安全令牌
    """
    return secrets.token_hex(length)

def constant_time_compare(val1: str, val2: str) -> bool:
    """
    恒定时间字符串比较，防止时序攻击
    
    Args:
        val1 (str): 第一个字符串
        val2 (str): 第二个字符串
        
    Returns:
        bool: 字符串相等返回True，否则返回False
    """
    return secrets.compare_digest(val1, val2)



    内容系统
from typing import Optional, Dict, Any  # 导入类型注解
from datetime import datetime, timedelta  # 导入日期时间模块
from jose import JWTError, jwt  # 导入JWT相关模块
from passlib.context import CryptContext  # 导入密码加密上下文
from fastapi import HTTPException, status, Depends  # 导入FastAPI相关依赖
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # 导入HTTP Bearer认证
from app.config import settings  # 导入应用配置
import logging  # 导入日志模块

# 创建密码加密上下文（使用bcrypt算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 创建HTTP Bearer安全方案
security = HTTPBearer()

# 获取日志记录器
logger = logging.getLogger(__name__)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
        
    Returns:
        密码是否匹配
    """
    try:
        # 使用密码上下文验证密码
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # 记录验证异常
        logger.error(f"密码验证异常: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """
    生成密码哈希值
    
    Args:
        password: 明文密码
        
    Returns:
        哈希密码
    """
    try:
        # 使用密码上下文生成密码哈希
        return pwd_context.hash(password)
    except Exception as e:
        # 记录哈希生成异常
        logger.error(f"密码哈希生成异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码处理失败"
        )

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    Args:
        data: 令牌数据
        expires_delta: 过期时间增量
        
    Returns:
        JWT访问令牌
    """
    try:
        # 复制令牌数据
        to_encode = data.copy()
        
        # 计算令牌过期时间
        if expires_delta:
            # 使用指定的过期时间增量
            expire = datetime.utcnow() + expires_delta
        else:
            # 使用默认的过期时间（30分钟）
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # 添加过期时间到令牌数据
        to_encode.update({"exp": expire})
        
        # 使用JWT编码令牌
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # 返回编码后的令牌
        return encoded_jwt
        
    except Exception as e:
        # 记录令牌创建异常
        logger.error(f"访问令牌创建异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌创建失败"
        )

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    创建刷新令牌
    
    Args:
        data: 令牌数据
        
    Returns:
        JWT刷新令牌
    """
    try:
        # 复制令牌数据
        to_encode = data.copy()
        
        # 计算刷新令牌过期时间（7天）
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # 添加过期时间到令牌数据
        to_encode.update({"exp": expire, "type": "refresh"})
        
        # 使用JWT编码刷新令牌
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # 返回编码后的刷新令牌
        return encoded_jwt
        
    except Exception as e:
        # 记录刷新令牌创建异常
        logger.error(f"刷新令牌创建异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新令牌创建失败"
        )

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证JWT令牌
    
    Args:
        token: JWT令牌
        
    Returns:
        解码后的令牌数据或None
    """
    try:
        # 使用JWT解码令牌
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # 检查令牌类型（如果是刷新令牌，不能用于访问）
        token_type = payload.get("type")
        if token_type == "refresh":
            # 返回None表示刷新令牌不能用于访问认证
            return None
            
        # 返回解码后的令牌数据
        return payload
        
    except JWTError as e:
        # 记录JWT解码异常
        logger.warning(f"JWT令牌验证失败: {str(e)}")
        return None
    except Exception as e:
        # 记录其他异常
        logger.error(f"令牌验证异常: {str(e)}")
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    获取当前用户信息（依赖注入）
    
    Args:
        credentials: HTTP认证凭证
        
    Returns:
        当前用户信息
    """
    try:
        # 从认证凭证中提取令牌
        token = credentials.credentials
        
        # 验证令牌
        payload = verify_token(token)
        
        # 检查令牌是否有效
        if payload is None:
            # 抛出401未授权异常
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 从令牌中提取用户ID
        user_id = payload.get("user_id")
        # 从令牌中提取用户名
        username = payload.get("username")
        # 从令牌中提取用户邮箱
        email = payload.get("email")
        
        # 检查用户ID是否存在
        if user_id is None:
            # 抛出401未授权异常
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 构建用户信息字典
        user_info = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "token": token
        }
        
        # 返回用户信息
        return user_info
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录异常
        logger.error(f"获取当前用户异常: {str(e)}")
        # 抛出401未授权异常
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """
    获取当前用户信息（可选，用于不需要强制认证的接口）
    
    Args:
        credentials: HTTP认证凭证（可选）
        
    Returns:
        当前用户信息或None
    """
    try:
        # 检查认证凭证是否存在
        if credentials is None:
            # 返回None表示用户未认证
            return None
        
        # 从认证凭证中提取令牌
        token = credentials.credentials
        
        # 验证令牌
        payload = verify_token(token)
        
        # 检查令牌是否有效
        if payload is None:
            # 返回None表示令牌无效
            return None
        
        # 从令牌中提取用户ID
        user_id = payload.get("user_id")
        # 从令牌中提取用户名
        username = payload.get("username")
        # 从令牌中提取用户邮箱
        email = payload.get("email")
        
        # 检查用户ID是否存在
        if user_id is None:
            # 返回None表示用户ID不存在
            return None
        
        # 构建用户信息字典
        user_info = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "token": token
        }
        
        # 返回用户信息
        return user_info
        
    except Exception as e:
        # 记录异常
        logger.error(f"获取可选当前用户异常: {str(e)}")
        # 返回None表示认证失败
        return None

def validate_user_permission(user: Dict[str, Any], required_permissions: List[str]) -> bool:
    """
    验证用户权限
    
    Args:
        user: 用户信息
        required_permissions: 需要的权限列表
        
    Returns:
        用户是否具有所需权限
    """
    try:
        # 这里应该实现具体的权限验证逻辑
        # 简化实现：假设所有认证用户都有基本权限
        
        # 检查用户是否存在
        if not user:
            return False
        
        # 检查用户是否具有管理员权限（示例）
        user_permissions = user.get("permissions", [])
        is_admin = "admin" in user_permissions
        
        # 如果是管理员，拥有所有权限
        if is_admin:
            return True
        
        # 检查用户是否具有所有需要的权限
        for permission in required_permissions:
            if permission not in user_permissions:
                return False
        
        # 用户具有所有需要的权限
        return True
        
    except Exception as e:
        # 记录异常
        logger.error(f"用户权限验证异常: {str(e)}")
        return False

        内容模块-安全工具
    from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import secrets
import hashlib
import re

from app.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_key() -> str:
    """生成API密钥"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """哈希API密钥"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """验证密码强度"""
    if len(password) < 8:
        return False, "密码长度至少8个字符"
    
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少一个大写字母"
    
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含至少一个小写字母"
    
    if not re.search(r'\d', password):
        return False, "密码必须包含至少一个数字"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含至少一个特殊字符"
    
    return True, "密码强度足够"


def sanitize_input(text: str) -> str:
    """清理用户输入，防止XSS攻击"""
    if not text:
        return text
    
    # 移除危险标签和属性
    sanitized = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r'<.*?on\w+.*?>', '', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
    
    # 转义HTML特殊字符
    sanitized = (
        sanitized.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#x27;')
        .replace('/', '&#x2F;')
    )
    
    return sanitized


def generate_csrf_token() -> str:
    """生成CSRF令牌"""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, stored_token: str) -> bool:
    """验证CSRF令牌"""
    return secrets.compare_digest(token, stored_token)