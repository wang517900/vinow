内容板块
"""
数据验证工具模块

本模块提供了各种数据验证功能，包括：
1. UUID格式验证
2. 邮箱格式验证
3. 手机号格式验证（越南）
4. 内容文本验证和清理
5. 敏感词检查
6. 评分范围验证
7. 文件类型和大小验证
8. 日期时间格式验证
9. 地理坐标验证
10. URL格式验证
11. 内容和评价数据完整性验证

所有验证函数都具有完善的异常处理机制。
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date
from fastapi import HTTPException, status
from app.models.content_models import ContentType, ContentStatus
from app.models.review_models import ReviewVerificationStatus
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

__all__ = [
    'validate_uuid',
    'validate_email',
    'validate_phone_number',
    'validate_content_text',
    'sanitize_content_text',
    'check_sensitive_words',
    'validate_rating',
    'validate_file_type',
    'validate_file_size',
    'validate_content_creation',
    'validate_review_creation',
    'validate_date_format',
    'validate_datetime_format',
    'validate_coordinates',
    'validate_url'
]

# 敏感词列表（实际应该从数据库或配置文件中加载）
SENSITIVE_WORDS = [
    "赌博", "赌场", "色情", "成人", "暴力", "恐怖", "毒品", "违禁品",
    "枪支", "弹药", "爆炸物", "诈骗", "传销", "非法", "反动", "政治"
]

# 越南语敏感词列表
VIETNAMESE_SENSITIVE_WORDS = [
    "cờ bạc", "sòng bạc", "khiêu dâm", "người lớn", "bạo lực", 
    "khủng bố", "ma túy", "hàng cấm", "súng", "đạn", "chất nổ"
]


def validate_uuid(uuid_string: str) -> bool:
    """
    验证UUID字符串格式
    
    Args:
        uuid_string: UUID字符串
        
    Returns:
        是否为有效的UUID
    """
    try:
        # 尝试将字符串转换为UUID对象
        uuid_obj = uuid.UUID(uuid_string)
        # 检查转换后的UUID字符串是否与原始字符串相同（忽略大小写和连字符格式）
        return str(uuid_obj).replace("-", "").lower() == uuid_string.replace("-", "").lower()
    except (ValueError, AttributeError):
        # UUID格式无效
        return False


def validate_email(email: str) -> bool:
    """
    验证邮箱格式
    
    Args:
        email: 邮箱地址
        
    Returns:
        是否为有效的邮箱格式
    """
    # 邮箱正则表达式
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    # 匹配邮箱格式
    return bool(re.match(email_regex, email))


def validate_phone_number(phone: str) -> bool:
    """
    验证手机号格式（越南手机号格式）
    
    Args:
        phone: 手机号码
        
    Returns:
        是否为有效的越南手机号格式
    """
    # 越南手机号正则表达式（以0开头，后面跟9位数字，或者+84开头）
    phone_regex = r'^(0|\+84)(3[2-9]|5[2689]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}$'
    # 清理手机号格式（移除空格和连字符）
    cleaned_phone = re.sub(r'[\s\-]', '', phone)
    # 匹配手机号格式
    return bool(re.match(phone_regex, cleaned_phone))


def validate_content_text(text: str, max_length: int = 5000) -> Tuple[bool, str]:
    """
    验证内容文本
    
    Args:
        text: 文本内容
        max_length: 最大长度限制
        
    Returns:
        (是否有效, 错误消息) 元组
    """
    # 检查文本是否为空
    if not text or not text.strip():
        return False, "内容不能为空"
    
    # 检查文本长度
    if len(text) > max_length:
        return False, f"内容长度不能超过{max_length}个字符"
    
    # 检查敏感词
    sensitive_words_found = check_sensitive_words(text)
    if sensitive_words_found:
        return False, f"内容包含敏感词: {', '.join(sensitive_words_found)}"
    
    # 文本验证通过
    return True, ""


def sanitize_content_text(text: str) -> str:
    """
    清理内容文本（移除潜在的XSS攻击等）
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return text
    
    # 移除HTML标签
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<.*?>', '', text)
    
    # 移除潜在的JavaScript代码
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+=', '', text, flags=re.IGNORECASE)
    
    # 移除多余的空格和换行
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def check_sensitive_words(text: str) -> List[str]:
    """
    检查文本中的敏感词
    
    Args:
        text: 待检查的文本
        
    Returns:
        找到的敏感词列表
    """
    found_words = []
    
    # 检查中文敏感词
    for word in SENSITIVE_WORDS:
        if word in text:
            found_words.append(word)
    
    # 检查越南语敏感词
    for word in VIETNAMESE_SENSITIVE_WORDS:
        if word.lower() in text.lower():
            found_words.append(word)
    
    return found_words


def validate_rating(rating: float, min_rating: float = 1.0, max_rating: float = 5.0) -> bool:
    """
    验证评分范围
    
    Args:
        rating: 评分值
        min_rating: 最小评分
        max_rating: 最大评分
        
    Returns:
        评分是否在有效范围内
    """
    return min_rating <= rating <= max_rating


def validate_file_type(filename: str, allowed_extensions: List[str]) -> bool:
    """
    验证文件类型
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的文件扩展名列表
        
    Returns:
        文件类型是否允许
    """
    if not filename:
        return False
    
    # 获取文件扩展名（小写）
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # 检查扩展名是否在允许列表中
    return file_extension in allowed_extensions


def validate_file_size(file_size: int, max_size: int) -> bool:
    """
    验证文件大小
    
    Args:
        file_size: 文件大小（字节）
        max_size: 最大文件大小（字节）
        
    Returns:
        文件大小是否在限制内
    """
    return file_size <= max_size


async def validate_content_creation(content_data: Dict[str, Any]) -> bool:
    """
    验证内容创建数据
    
    Args:
        content_data: 内容创建数据
        
    Returns:
        数据是否有效
        
    Raises:
        HTTPException: 当数据无效时抛出
    """
    try:
        # 验证内容类型
        content_type = content_data.get("content_type")
        if not content_type or content_type not in [ct.value for ct in ContentType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的内容类型: {content_type}"
            )
        
        # 验证标题和描述
        title = content_data.get("title")
        description = content_data.get("description")
        
        # 标题和描述不能同时为空
        if not title and not description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="标题和描述不能同时为空"
            )
        
        # 验证标题长度
        if title and len(title) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="标题长度不能超过500个字符"
            )
        
        # 验证描述长度
        if description and len(description) > 5000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="描述长度不能超过5000个字符"
            )
        
        # 验证作者ID
        author_id = content_data.get("author_id")
        if not author_id or not validate_uuid(author_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的作者ID"
            )
        
        # 验证标签
        tags = content_data.get("tags", [])
        if tags and len(tags) > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="标签数量不能超过20个"
            )
        
        for tag in tags:
            if len(tag) > 50:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"标签 '{tag}' 长度不能超过50个字符"
                )
        
        # 验证通过
        return True
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录验证异常
        logger.error(f"内容创建数据验证异常: {str(e)}")
        # 抛出验证失败异常
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="内容数据验证失败"
        )


async def validate_review_creation(review_data: Dict[str, Any]) -> bool:
    """
    验证评价创建数据
    
    Args:
        review_data: 评价创建数据
        
    Returns:
        数据是否有效
        
    Raises:
        HTTPException: 当数据无效时抛出
    """
    try:
        # 验证总体评分
        overall_rating = review_data.get("overall_rating")
        if not validate_rating(overall_rating):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="评分必须在1.0到5.0之间"
            )
        
        # 验证维度评分
        dimension_scores = review_data.get("dimension_scores", [])
        if not dimension_scores:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要一个维度评分"
            )
        
        # 验证每个维度评分
        for score in dimension_scores:
            if not validate_rating(score.get("score")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"维度 '{score.get('dimension')}' 评分无效"
                )
        
        # 验证目标实体信息
        target_entity_type = review_data.get("target_entity_type")
        target_entity_id = review_data.get("target_entity_id")
        
        if not target_entity_type or not target_entity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目标实体类型和ID不能为空"
            )
        
        # 验证目标实体ID格式
        if not validate_uuid(target_entity_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的目标实体ID"
            )
        
        # 验证描述内容
        description = review_data.get("description")
        if not description or not description.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="评价内容不能为空"
            )
        
        # 验证描述长度
        if len(description) > 2000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="评价内容长度不能超过2000个字符"
            )
        
        # 验证优点和缺点
        pros = review_data.get("pros", [])
        cons = review_data.get("cons", [])
        
        for pro in pros:
            if len(pro) > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="每个优点不能超过100个字符"
                )
        
        for con in cons:
            if len(con) > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="每个缺点不能超过100个字符"
                )
        
        # 验证通过
        return True
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录验证异常
        logger.error(f"评价创建数据验证异常: {str(e)}")
        # 抛出验证失败异常
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="评价数据验证失败"
        )


def validate_date_format(date_string: str, format: str = "%Y-%m-%d") -> bool:
    """
    验证日期格式
    
    Args:
        date_string: 日期字符串
        format: 日期格式
        
    Returns:
        日期格式是否有效
    """
    try:
        # 尝试解析日期字符串
        datetime.strptime(date_string, format)
        return True
    except (ValueError, TypeError):
        return False


def validate_datetime_format(datetime_string: str, format: str = "%Y-%m-%d %H:%M:%S") -> bool:
    """
    验证日期时间格式
    
    Args:
        datetime_string: 日期时间字符串
        format: 日期时间格式
        
    Returns:
        日期时间格式是否有效
    """
    try:
        # 尝试解析日期时间字符串
        datetime.strptime(datetime_string, format)
        return True
    except (ValueError, TypeError):
        return False


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    验证地理坐标
    
    Args:
        latitude: 纬度
        longitude: 经度
        
    Returns:
        坐标是否有效
    """
    # 验证纬度范围（-90到90）
    if not (-90 <= latitude <= 90):
        return False
    
    # 验证经度范围（-180到180）
    if not (-180 <= longitude <= 180):
        return False
    
    return True


def validate_url(url: str) -> bool:
    """
    验证URL格式
    
    Args:
        url: URL字符串
        
    Returns:
        URL格式是否有效
    """
    # URL正则表达式
    url_regex = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[\w/\-?=%.]*\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|mov|avi|mkv|pdf|doc|docx|xls|xlsx|ppt|pptx))?[/\w\.\-?=%.]*$'
    # 匹配URL格式
    return bool(re.match(url_regex, url))



    内容系统

 import re
import logging
from typing import Any, Dict, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ContentValidator:
    """内容验证器"""
    
    @staticmethod
    def validate_title(title: str) -> bool:
        """验证标题"""
        if not title or len(title.strip()) == 0:
            return False
        
        if len(title) > 255:
            return False
        
        # 检查是否包含非法字符
        illegal_pattern = r'[<>"\']'
        if re.search(illegal_pattern, title):
            return False
        
        return True
    
    @staticmethod
    def validate_description(description: str) -> bool:
        """验证描述"""
        if description is None:
            return True
        
        if len(description) > 5000:
            return False
        
        return True
    
    @staticmethod
    def validate_tags(tags: List[str]) -> bool:
        """验证标签"""
        if not isinstance(tags, list):
            return False
        
        if len(tags) > 20:
            return False
        
        for tag in tags:
            if not isinstance(tag, str):
                return False
            if len(tag) > 50:
                return False
            if re.search(r'[<>"\']', tag):
                return False
        
        return True
    
    @staticmethod
    def validate_media_urls(urls: List[str]) -> bool:
        """验证媒体URL"""
        if not urls or len(urls) == 0:
            return False
        
        if len(urls) > 10:  # 最多10个媒体文件
            return False
        
        for url in urls:
            try:
                result = urlparse(url)
                if not all([result.scheme, result.netloc]):
                    return False
                
                # 检查支持的协议
                if result.scheme not in ['http', 'https']:
                    return False
                    
            except Exception:
                return False
        
        return True

class UserValidator:
    """用户验证器"""
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """验证用户名"""
        if not username or len(username) < 3:
            return False
        
        if len(username) > 50:
            return False
        
        # 只允许字母、数字、下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False
        
        return True
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱"""
        if not email:
            return False
        
        # 简单的邮箱格式验证
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """验证密码"""
        if not password or len(password) < 8:
            return False
        
        if len(password) > 100:
            return False
        
        # 检查密码强度（可选）
        # 这里可以添加更复杂的密码规则
        
        return True

class LocationValidator:
    """地理位置验证器"""
    
    @staticmethod
    def validate_location(location: Dict[str, Any]) -> bool:
        """验证地理位置数据"""
        if not location:
            return True
        
        if not isinstance(location, dict):
            return False
        
        # 检查必需字段
        if 'latitude' not in location or 'longitude' not in location:
            return False
        
        try:
            lat = float(location['latitude'])
            lng = float(location['longitude'])
            
            # 检查坐标范围
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False

def validate_content_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """验证内容数据并返回错误信息"""
    errors = []
    
    # 验证标题
    if not ContentValidator.validate_title(data.get('title', '')):
        errors.append("标题无效：标题不能为空，长度不能超过255个字符，且不能包含非法字符")
    
    # 验证描述
    if not ContentValidator.validate_description(data.get('description')):
        errors.append("描述无效：描述长度不能超过5000个字符")
    
    # 验证标签
    if not ContentValidator.validate_tags(data.get('tags', [])):
        errors.append("标签无效：最多20个标签，每个标签长度不能超过50个字符")
    
    # 验证媒体URL
    if not ContentValidator.validate_media_urls(data.get('media_urls', [])):
        errors.append("媒体URL无效：必须提供至少一个有效的HTTP/HTTPS URL，最多10个")
    
    # 验证地理位置
    if not LocationValidator.validate_location(data.get('location')):
        errors.append("地理位置数据无效")
    
    return {"errors": errors, "is_valid": len(errors) == 0}   