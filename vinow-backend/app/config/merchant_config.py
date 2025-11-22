"""商家系统配置模块"""

import os
from pydantic import BaseSettings
from typing import List, Dict, Any, Optional


class MerchantSettings(BaseSettings):
    """商家系统专用配置"""
    
    # ==================== 文件上传配置 ====================
    # 商家文件上传目录配置
    MERCHANT_UPLOAD_DIR: str = os.getenv("MERCHANT_UPLOAD_DIR", "./uploads/merchants")
    MERCHANT_LOGO_DIR: str = os.getenv("MERCHANT_LOGO_DIR", "./uploads/merchants/logos")
    MERCHANT_BANNER_DIR: str = os.getenv("MERCHANT_BANNER_DIR", "./uploads/merchants/banners")
    MERCHANT_PRODUCT_DIR: str = os.getenv("MERCHANT_PRODUCT_DIR", "./uploads/merchants/products")
    MERCHANT_QRCODE_DIR: str = os.getenv("MERCHANT_QRCODE_DIR", "./uploads/merchants/qrcodes")
    
    # 文件大小和类型限制
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", "5242880"))  # 5MB
    MAX_VIDEO_SIZE: int = int(os.getenv("MAX_VIDEO_SIZE", "52428800"))  # 50MB
    
    ALLOWED_IMAGE_TYPES: List[str] = [
        "image/jpeg", 
        "image/png", 
        "image/gif", 
        "image/webp"
    ]
    ALLOWED_VIDEO_TYPES: List[str] = [
        "video/mp4", 
        "video/quicktime",
        "video/x-msvideo",
        "video/webm"
    ]
    ALLOWED_DOCUMENT_TYPES: List[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    
    # ==================== 商家业务配置 ====================
    # 商家基础配置
    MAX_PRODUCTS_PER_MERCHANT: int = int(os.getenv("MAX_PRODUCTS_PER_MERCHANT", "1000"))
    MAX_CATEGORIES_PER_MERCHANT: int = int(os.getenv("MAX_CATEGORIES_PER_MERCHANT", "50"))
    MAX_COUPONS_PER_MERCHANT: int = int(os.getenv("MAX_COUPONS_PER_MERCHANT", "100"))
    MAX_PROMOTIONS_PER_MERCHANT: int = int(os.getenv("MAX_PROMOTIONS_PER_MERCHANT", "50"))
    
    # 佣金和费率配置
    DEFAULT_COMMISSION_RATE: float = float(os.getenv("DEFAULT_COMMISSION_RATE", "0.1"))  # 10%平台佣金
    MIN_COMMISSION_RATE: float = float(os.getenv("MIN_COMMISSION_RATE", "0.05"))  # 5%最低佣金
    MAX_COMMISSION_RATE: float = float(os.getenv("MAX_COMMISSION_RATE", "0.3"))  # 30%最高佣金
    
    # 订单和预约配置
    ORDER_AUTO_CONFIRM_MINUTES: int = int(os.getenv("ORDER_AUTO_CONFIRM_MINUTES", "15"))
    RESERVATION_REMINDER_HOURS: int = int(os.getenv("RESERVATION_REMINDER_HOURS", "2"))
    ORDER_CANCELLATION_TIMEOUT_MINUTES: int = int(os.getenv("ORDER_CANCELLATION_TIMEOUT_MINUTES", "30"))
    MAX_RESERVATION_DURATION_HOURS: int = int(os.getenv("MAX_RESERVATION_DURATION_HOURS", "24"))
    
    # 评价和评分配置
    MIN_RATING: int = int(os.getenv("MIN_RATING", "1"))
    MAX_RATING: int = int(os.getenv("MAX_RATING", "5"))
    MIN_REVIEW_LENGTH: int = int(os.getenv("MIN_REVIEW_LENGTH", "10"))
    MAX_REVIEW_LENGTH: int = int(os.getenv("MAX_REVIEW_LENGTH", "1000"))
    
    # ==================== 营销功能配置 ====================
    # 促销活动配置
    PROMOTION_MIN_DISCOUNT: float = float(os.getenv("PROMOTION_MIN_DISCOUNT", "0.01"))  # 1%最小折扣
    PROMOTION_MAX_DISCOUNT: float = float(os.getenv("PROMOTION_MAX_DISCOUNT", "0.99"))  # 99%最大折扣
    PROMOTION_MIN_DURATION_DAYS: int = int(os.getenv("PROMOTION_MIN_DURATION_DAYS", "1"))
    PROMOTION_MAX_DURATION_DAYS: int = int(os.getenv("PROMOTION_MAX_DURATION_DAYS", "365"))
    
    # 优惠券配置
    COUPON_MIN_VALUE: float = float(os.getenv("COUPON_MIN_VALUE", "1.0"))
    COUPON_MAX_VALUE: float = float(os.getenv("COUPON_MAX_VALUE", "1000.0"))
    COUPON_CODE_MIN_LENGTH: int = int(os.getenv("COUPON_CODE_MIN_LENGTH", "3"))
    COUPON_CODE_MAX_LENGTH: int = int(os.getenv("COUPON_CODE_MAX_LENGTH", "20"))
    
    # 广告配置
    MAX_ADVERTISEMENTS_PER_MERCHANT: int = int(os.getenv("MAX_ADVERTISEMENTS_PER_MERCHANT", "10"))
    ADVERTISEMENT_MIN_DURATION_DAYS: int = int(os.getenv("ADVERTISEMENT_MIN_DURATION_DAYS", "1"))
    ADVERTISEMENT_MAX_DURATION_DAYS: int = int(os.getenv("ADVERTISEMENT_MAX_DURATION_DAYS", "365"))
    
    # ==================== 地理位置配置 ====================
    # Google Maps配置
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    DEFAULT_MAP_ZOOM: int = int(os.getenv("DEFAULT_MAP_ZOOM", "15"))
    MAX_SEARCH_RADIUS_KM: int = int(os.getenv("MAX_SEARCH_RADIUS_KM", "50"))
    
    # 地址配置
    SUPPORTED_COUNTRIES: List[str] = ["VN"]  # 越南
    SUPPORTED_LANGUAGES: List[str] = ["vi", "en"]
    
    # ==================== 营业时间配置 ====================
    # 营业时间配置
    BUSINESS_HOURS_MIN_OPEN_TIME: str = os.getenv("BUSINESS_HOURS_MIN_OPEN_TIME", "00:00")
    BUSINESS_HOURS_MAX_CLOSE_TIME: str = os.getenv("BUSINESS_HOURS_MAX_CLOSE_TIME", "23:59")
    MAX_CONCURRENT_BOOKINGS: int = int(os.getenv("MAX_CONCURRENT_BOOKINGS", "100"))
    
    # ==================== 分析和统计配置 ====================
    # 数据分析配置
    ANALYTICS_DATA_RETENTION_DAYS: int = int(os.getenv("ANALYTICS_DATA_RETENTION_DAYS", "365"))
    ANALYTICS_MIN_DATA_POINTS: int = int(os.getenv("ANALYTICS_MIN_DATA_POINTS", "7"))
    MAX_EXPORT_DATA_ROWS: int = int(os.getenv("MAX_EXPORT_DATA_ROWS", "10000"))
    
    # ==================== 缓存配置 ====================
    # 缓存配置
    MERCHANT_CACHE_TTL: int = int(os.getenv("MERCHANT_CACHE_TTL", "300"))  # 5分钟
    PROMOTION_CACHE_TTL: int = int(os.getenv("PROMOTION_CACHE_TTL", "180"))  # 3分钟
    REVIEW_CACHE_TTL: int = int(os.getenv("REVIEW_CACHE_TTL", "600"))  # 10分钟
    
    # ==================== 通知配置 ====================
    # 通知配置
    ENABLE_EMAIL_NOTIFICATIONS: bool = os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "true").lower() == "true"
    ENABLE_SMS_NOTIFICATIONS: bool = os.getenv("ENABLE_SMS_NOTIFICATIONS", "false").lower() == "true"
    ENABLE_PUSH_NOTIFICATIONS: bool = os.getenv("ENABLE_PUSH_NOTIFICATIONS", "true").lower() == "true"
    
    # ==================== 安全配置 ====================
    # 安全配置
    MERCHANT_API_RATE_LIMIT: int = int(os.getenv("MERCHANT_API_RATE_LIMIT", "1000"))  # 每小时请求数
    ENABLE_MERCHANT_AUDIT_LOG: bool = os.getenv("ENABLE_MERCHANT_AUDIT_LOG", "true").lower() == "true"
    
    # ==================== 第三方集成配置 ====================
    # 第三方服务配置
    ENABLE_THIRD_PARTY_INTEGRATIONS: bool = os.getenv("ENABLE_THIRD_PARTY_INTEGRATIONS", "false").lower() == "true"
    SUPPORTED_INTEGRATIONS: List[str] = ["facebook", "instagram", "zalo"]
    
    class Config:
        """Pydantic配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
merchant_settings = MerchantSettings()

# ==================== 配置验证 ====================
def validate_merchant_settings() -> List[str]:
    """
    验证商家配置设置的有效性
    
    Returns:
        List[str]: 错误信息列表
    """
    errors = []
    
    # 验证文件大小配置
    if merchant_settings.MAX_IMAGE_SIZE > merchant_settings.MAX_FILE_SIZE:
        errors.append("MAX_IMAGE_SIZE 不能大于 MAX_FILE_SIZE")
    
    if merchant_settings.MAX_VIDEO_SIZE > merchant_settings.MAX_FILE_SIZE:
        errors.append("MAX_VIDEO_SIZE 不能大于 MAX_FILE_SIZE")
    
    # 验证佣金率配置
    if not (0 <= merchant_settings.MIN_COMMISSION_RATE <= merchant_settings.MAX_COMMISSION_RATE <= 1):
        errors.append("佣金率配置无效，必须满足 0 <= MIN <= MAX <= 1")
    
    # 验证评分配置
    if not (1 <= merchant_settings.MIN_RATING <= merchant_settings.MAX_RATING <= 5):
        errors.append("评分配置无效，必须满足 1 <= MIN <= MAX <= 5")
    
    # 验证折扣配置
    if not (0 < merchant_settings.PROMOTION_MIN_DISCOUNT <= merchant_settings.PROMOTION_MAX_DISCOUNT < 1):
        errors.append("促销折扣配置无效，必须满足 0 < MIN <= MAX < 1")
    
    # 验证搜索半径配置
    if merchant_settings.MAX_SEARCH_RADIUS_KM <= 0:
        errors.append("MAX_SEARCH_RADIUS_KM 必须大于0")
    
    return errors


# ==================== 配置信息函数 ====================
def get_merchant_config_info() -> Dict[str, Any]:
    """
    获取商家配置信息摘要
    
    Returns:
        Dict[str, Any]: 配置信息字典
    """
    return {
        "upload_directories": {
            "base": merchant_settings.MERCHANT_UPLOAD_DIR,
            "logos": merchant_settings.MERCHANT_LOGO_DIR,
            "banners": merchant_settings.MERCHANT_BANNER_DIR,
            "products": merchant_settings.MERCHANT_PRODUCT_DIR,
            "qrcodes": merchant_settings.MERCHANT_QRCODE_DIR
        },
        "file_limits": {
            "max_file_size": merchant_settings.MAX_FILE_SIZE,
            "max_image_size": merchant_settings.MAX_IMAGE_SIZE,
            "max_video_size": merchant_settings.MAX_VIDEO_SIZE
        },
        "business_limits": {
            "max_products": merchant_settings.MAX_PRODUCTS_PER_MERCHANT,
            "max_coupons": merchant_settings.MAX_COUPONS_PER_MERCHANT,
            "max_promotions": merchant_settings.MAX_PROMOTIONS_PER_MERCHANT
        },
        "commission": {
            "default_rate": merchant_settings.DEFAULT_COMMISSION_RATE,
            "min_rate": merchant_settings.MIN_COMMISSION_RATE,
            "max_rate": merchant_settings.MAX_COMMISSION_RATE
        },
        "integrations": {
            "google_maps_api_key_set": bool(merchant_settings.GOOGLE_MAPS_API_KEY),
            "third_party_enabled": merchant_settings.ENABLE_THIRD_PARTY_INTEGRATIONS
        }
    }


# 启动时验证配置
config_errors = validate_merchant_settings()
if config_errors:
    print("⚠️  商家系统配置警告:")
    for error in config_errors:
        print(f"   • {error}")