# app/core/logging.py
import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

def setup_logging():
    """配置应用程序日志"""
    
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 根日志配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # 控制台输出
            logging.StreamHandler(sys.stdout),
            # 文件输出（按大小轮转）
            RotatingFileHandler(
                f"{log_dir}/app.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
        ]
    )
    
    # 为不同模块设置不同的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # 业务模块日志
    business_logger = logging.getLogger("business")
    business_handler = RotatingFileHandler(
        f"{log_dir}/business.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    business_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    business_logger.addHandler(business_handler)
    
    # 安全审计日志
    audit_logger = logging.getLogger("audit")
    audit_handler = RotatingFileHandler(
        f"{log_dir}/audit.log", 
        maxBytes=10*1024*1024,
        backupCount=10,  # 保留更多审计日志
        encoding='utf-8'
    )
    audit_handler.setFormatter(logging.Formatter(
        '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
    ))
    audit_logger.addHandler(audit_handler)

class AuditLogger:
    """审计日志记录器"""
    
    @staticmethod
    def log_content_operation(operation: str, merchant_id: str, content_id: str, details: dict = None):
        """记录内容操作审计日志"""
        logger = logging.getLogger("audit")
        message = f"CONTENT_{operation} - Merchant: {merchant_id} - Content: {content_id}"
        if details:
            message += f" - Details: {details}"
        logger.info(message)
    
    @staticmethod
    def log_collaboration_operation(operation: str, merchant_id: str, collaboration_id: str, details: dict = None):
        """记录合作操作审计日志"""
        logger = logging.getLogger("audit")
        message = f"COLLABORATION_{operation} - Merchant: {merchant_id} - Collaboration: {collaboration_id}"
        if details:
            message += f" - Details: {details}"
        logger.info(message)
    
    @staticmethod
    def log_security_event(event: str, merchant_id: str, user_id: str, details: dict = None):
        """记录安全事件"""
        logger = logging.getLogger("audit")
        message = f"SECURITY_{event} - Merchant: {merchant_id} - User: {user_id}"
        if details:
            message += f" - Details: {details}"
        logger.warning(message)

class BusinessLogger:
    """业务日志记录器"""
    
    def __init__(self, module_name: str):
        self.logger = logging.getLogger(f"business.{module_name}")
    
    def log_operation(self, operation: str, merchant_id: str, **kwargs):
        """记录业务操作"""
        message = f"{operation} - Merchant: {merchant_id}"
        if kwargs:
            message += f" - {kwargs}"
        self.logger.info(message)
    
    def log_error(self, operation: str, merchant_id: str, error: Exception, **kwargs):
        """记录业务错误"""
        message = f"{operation}_ERROR - Merchant: {merchant_id} - Error: {str(error)}"
        if kwargs:
            message += f" - {kwargs}"
        self.logger.error(message, exc_info=True)
    
    def log_performance(self, operation: str, duration: float, merchant_id: str = None):
        """记录性能日志"""
        message = f"{operation}_PERFORMANCE - Duration: {duration:.3f}s"
        if merchant_id:
            message += f" - Merchant: {merchant_id}"
        self.logger.info(message)


        商家板块5数据分析
        import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any
from app.core.config import settings

class JSONFormatter(logging.Formatter):
    """JSON 日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)
            
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging():
    """设置日志配置"""
    
    # 清除现有的处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=settings.log_level_int,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if settings.LOG_FORMAT != "json" else "",
        handlers=[]
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.LOG_FORMAT == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
    
    # 获取根日志记录器并添加处理器
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    
    return root_logger

# 创建应用日志记录器
logger = logging.getLogger("analytics_suite")

商家板块6财务中心
import logging
import sys
from logging.handlers import RotatingFileHandler
import json
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityFilter(logging.Filter):
    """安全过滤器，防止记录敏感信息"""
    
    def filter(self, record):
        # 过滤敏感字段
        sensitive_fields = ['password', 'token', 'authorization', 'bank_account', 'secret_key']
        
        if hasattr(record, 'msg') and record.msg:
            message = str(record.msg).lower()
            for field in sensitive_fields:
                if field in message:
                    # 替换敏感信息
                    record.msg = self._mask_sensitive_data(record.msg, field)
        
        return True
    
    def _mask_sensitive_data(self, message, field):
        """掩码敏感数据"""
        import re
        message_str = str(message)
        # 匹配类似 "password": "secret" 的模式
        pattern = rf'("{field}"\s*:\s*")([^"]+)(")'
        replacement = rf'\1***\3'
        return re.sub(pattern, replacement, message_str)


class JSONFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""
    
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'trace_id': getattr(record, 'trace_id', ''),
            'merchant_id': getattr(record, 'merchant_id', '')
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging():
    """设置日志配置"""
    
    # 创建日志目录
    import os
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除已有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(SecurityFilter())
    logger.addHandler(console_handler)
    
    # 文件处理器（JSON格式）
    file_handler = RotatingFileHandler(
        f'{log_dir}/finance_system.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())
    file_handler.addFilter(SecurityFilter())
    logger.addHandler(file_handler)
    
    # 错误日志文件处理器
    error_handler = RotatingFileHandler(
        f'{log_dir}/finance_system_error.log',
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    error_handler.addFilter(SecurityFilter())
    logger.addHandler(error_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('supabase').setLevel(logging.WARNING)


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        import uuid
        request_id = str(uuid.uuid4())
        
        # 记录请求开始
        logger = logging.getLogger('api')
        start_time = time.time()
        
        # 添加请求ID到日志记录
        record_factory = logging.getLogRecordFactory()
        
        def factory(*args, **kwargs):
            record = record_factory(*args, **kwargs)
            record.trace_id = request_id
            # 尝试从请求中获取商户ID
            merchant_id = getattr(request.state, 'merchant_id', '')
            record.merchant_id = merchant_id
            return record
        
        logging.setLogRecordFactory(factory)
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录请求日志（排除敏感路径）
            if not any(path in str(request.url) for path in ['/health', '/docs', '/redoc']):
                logger.info(
                    f"Request completed: {request.method} {request.url.path} "
                    f"Status: {response.status_code} "
                    f"Duration: {process_time:.3f}s"
                )
            
            # 添加请求ID到响应头
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Process-Time'] = f"{process_time:.3f}"
            
            return response
            
        except Exception as exc:
            # 记录异常
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(exc)}",
                exc_info=True
            )
            raise


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    logger = logging.getLogger(name)
    return logger