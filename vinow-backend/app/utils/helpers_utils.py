内容系统

import hashlib
import time
import random
import string
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
import json
import re
import uuid
from urllib.parse import urlparse
import base64

def generate_id(prefix: str = "") -> str:
    """生成唯一ID
    
    Args:
        prefix: ID前缀
        
    Returns:
        带时间戳和随机字符串的唯一ID
    """
    timestamp = int(time.time() * 1000)
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{prefix}{timestamp}_{random_str}"

def generate_uuid() -> str:
    """生成UUID
    
    Returns:
        标准UUID字符串
    """
    return str(uuid.uuid4())

def calculate_file_hash(file_path: str) -> str:
    """计算文件哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        SHA256哈希值
        
    Raises:
        FileNotFoundError: 文件不存在
        IOError: 文件读取错误
    """
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except FileNotFoundError:
        raise FileNotFoundError(f"文件不存在: {file_path}")
    except IOError as e:
        raise IOError(f"文件读取错误: {str(e)}")

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小
    
    Args:
        size_bytes: 字节大小
        
    Returns:
        格式化后的文件大小字符串
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def format_duration(seconds: Union[int, float]) -> str:
    """格式化时长（秒转换为时分秒）
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时长字符串
    """
    if seconds < 0:
        return "0秒"
    
    seconds = int(seconds)
    
    if seconds < 60:
        return f"{seconds}秒"
    
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        if remaining_seconds > 0:
            return f"{minutes}分{remaining_seconds}秒"
        return f"{minutes}分"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    result = f"{hours}时"
    if remaining_minutes > 0:
        result += f"{remaining_minutes}分"
    if remaining_seconds > 0:
        result += f"{remaining_seconds}秒"
    
    return result

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全地解析JSON字符串
    
    Args:
        json_str: JSON字符串
        default: 解析失败时的默认值
        
    Returns:
        解析后的数据或默认值
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(obj: Any, **kwargs) -> str:
    """安全地序列化为JSON字符串
    
    Args:
        obj: 要序列化的对象
        **kwargs: json.dumps的其他参数
        
    Returns:
        JSON字符串
    """
    try:
        return json.dumps(obj, **kwargs)
    except (TypeError, ValueError) as e:
        raise ValueError(f"JSON序列化失败: {str(e)}")

def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """深度合并两个字典
    
    Args:
        dict1: 第一个字典
        dict2: 第二个字典
        
    Returns:
        合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if (key in result and isinstance(result[key], dict) 
            and isinstance(value, dict)):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def filter_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """过滤敏感数据
    
    Args:
        data: 包含敏感数据的字典
        
    Returns:
        过滤后的字典
    """
    sensitive_fields = {
        'password', 'password_hash', 'secret_key', 'api_key', 
        'token', 'access_token', 'refresh_token', 'private_key'
    }
    
    def filter_recursive(obj):
        if isinstance(obj, dict):
            return {k: filter_recursive(v) for k, v in obj.items() 
                   if k.lower() not in sensitive_fields}
        elif isinstance(obj, list):
            return [filter_recursive(item) for item in obj]
        else:
            return obj
    
    return filter_recursive(data)

def mask_sensitive_info(text: str, patterns: Optional[List[str]] = None) -> str:
    """遮蔽敏感信息
    
    Args:
        text: 原始文本
        patterns: 敏感信息模式列表
        
    Returns:
        遮蔽后的文本
    """
    if patterns is None:
        # 默认敏感信息模式
        patterns = [
            (r'\b\d{11}\b', '***********'),  # 手机号
            (r'\b\d{18}\b', '******************'),  # 身份证号
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***'),  # 邮箱
        ]
    
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)
    
    return result

def calculate_quality_score(
    completeness: float,
    engagement: float, 
    creator_reputation: float,
    freshness: float,
    media_quality: float
) -> float:
    """计算内容质量分数
    
    Args:
        completeness: 完整性 (0-1)
        engagement: 参与度 (0-1)
        creator_reputation: 创作者声誉 (0-1)
        freshness: 新鲜度 (0-1)
        media_quality: 媒体质量 (0-1)
        
    Returns:
        质量分数 (0-1)
    """
    # 验证输入参数
    scores = [completeness, engagement, creator_reputation, freshness, media_quality]
    for score in scores:
        if not 0 <= score <= 1:
            raise ValueError(f"分数必须在0-1之间，得到: {score}")
    
    weights = {
        'completeness': 0.2,
        'engagement': 0.3,
        'creator_reputation': 0.2,
        'freshness': 0.15,
        'media_quality': 0.15
    }
    
    score = (
        completeness * weights['completeness'] +
        engagement * weights['engagement'] +
        creator_reputation * weights['creator_reputation'] +
        freshness * weights['freshness'] +
        media_quality * weights['media_quality']
    )
    
    return round(score, 4)

def get_time_ago(timestamp: datetime) -> str:
    """获取相对时间描述
    
    Args:
        timestamp: 时间戳
        
    Returns:
        相对时间描述
    """
    if not isinstance(timestamp, datetime):
        raise TypeError("timestamp必须是datetime类型")
    
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff < timedelta(seconds=0):
        return "刚刚"
    
    if diff < timedelta(minutes=1):
        return "刚刚"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() // 60)
        return f"{minutes}分钟前"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() // 3600)
        return f"{hours}小时前"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days}天前"
    elif diff < timedelta(days=365):
        months = diff.days // 30
        return f"{months}个月前"
    else:
        years = diff.days // 365
        return f"{years}年前"

def is_valid_email(email: str) -> bool:
    """验证邮箱格式
    
    Args:
        email: 邮箱地址
        
    Returns:
        是否为有效邮箱格式
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone: str) -> bool:
    """验证手机号格式
    
    Args:
        phone: 手机号
        
    Returns:
        是否为有效手机号格式
    """
    # 简化的手机号验证（支持中国手机号）
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def is_valid_url(url: str) -> bool:
    """验证URL格式
    
    Args:
        url: URL地址
        
    Returns:
        是否为有效URL格式
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def slugify(text: str) -> str:
    """生成URL友好的slug
    
    Args:
        text: 原始文本
        
    Returns:
        URL友好的slug
    """
    # 转换为小写
    text = text.lower()
    # 替换空格和特殊字符为连字符
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # 移除开头和结尾的连字符
    text = text.strip('-')
    return text

def generate_random_string(length: int, chars: str = string.ascii_letters + string.digits) -> str:
    """生成随机字符串
    
    Args:
        length: 字符串长度
        chars: 字符集
        
    Returns:
        随机字符串
    """
    return ''.join(random.choices(chars, k=length))

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:  # 不是最后一次尝试
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        break
            
            raise last_exception
        return wrapper
    return decorator

def chunks(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """将列表分块
    
    Args:
        lst: 原始列表
        chunk_size: 块大小
        
    Returns:
        分块后的列表
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def base64_encode(data: Union[str, bytes]) -> str:
    """Base64编码
    
    Args:
        data: 要编码的数据
        
    Returns:
        Base64编码后的字符串
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.b64encode(data).decode('utf-8')

def base64_decode(encoded_data: str) -> str:
    """Base64解码
    
    Args:
        encoded_data: Base64编码的数据
        
    Returns:
        解码后的字符串
    """
    decoded_bytes = base64.b64decode(encoded_data)
    return decoded_bytes.decode('utf-8')

def get_client_ip(request) -> Optional[str]:
    """获取客户端IP地址
    
    Args:
        request: 请求对象
        
    Returns:
        客户端IP地址
    """
    # 这里是一个通用实现，实际使用时需要根据框架调整
    if hasattr(request, 'client'):
        return request.client.host
    elif hasattr(request, 'headers'):
        # 检查常见的代理头
        for header in ['X-Forwarded-For', 'X-Real-IP']:
            ip = request.headers.get(header)
            if ip:
                return ip.split(',')[0].strip()
    return None