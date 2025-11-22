内容板块-日志配置文件
"""
日志工具模块

本模块提供了生产级别的日志配置和管理功能，包括：
1. JSON格式日志输出
2. 多种日志轮转策略（按大小、按时间）
3. 分级别的日志文件输出
4. 结构化日志数据
5. 第三方库日志级别控制

支持的特性：
- 开发环境：控制台输出，易读格式
- 生产环境：文件输出，JSON格式
- 自动日志轮转和清理
- 多种日志级别分离（应用日志、错误日志、访问日志）
"""

import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from app.config import settings
import json
from datetime import datetime
from typing import Dict, Any

__all__ = [
    'JSONFormatter',
    'setup_logging',
    'get_logger',
    'log_extra_data',
    'RequestContextFilter'
]


class JSONFormatter(logging.Formatter):
    """
    JSON日志格式化器 - 生产级别的结构化日志
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为JSON格式
        
        Args:
            record: 日志记录
            
        Returns:
            JSON格式的日志字符串
        """
        # 构建日志数据字典
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",  # 时间戳
            "level": record.levelname,  # 日志级别
            "logger": record.name,  # 日志记录器名称
            "message": record.getMessage(),  # 日志消息
            "module": record.module,  # 模块名
            "function": record.funcName,  # 函数名
            "line": record.lineno,  # 行号
            "process": record.process,  # 进程ID
            "thread": record.thread,  # 线程ID
        }
        
        # 如果有异常信息，添加到日志数据中
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 如果有额外的日志字段，添加到日志数据中
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # 返回JSON格式的日志字符串
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    """
    配置日志系统 - 生产级别的日志配置
    """
    # 创建日志目录
    log_dir = "logs"
    # 如果日志目录不存在，则创建
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    # 设置日志级别
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建JSON格式化器
    json_formatter = JSONFormatter()
    
    # 创建控制台处理器（用于开发环境）
    if settings.DEBUG:
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        # 创建开发环境格式化器（易读格式）
        dev_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(module)s:%(funcName)s:%(lineno)d]'
        )
        # 设置控制台处理器的格式化器
        console_handler.setFormatter(dev_formatter)
        # 设置控制台处理器的日志级别
        console_handler.setLevel(logging.DEBUG)
        # 添加控制台处理器到根日志记录器
        root_logger.addHandler(console_handler)
    
    # 创建文件处理器（用于生产环境）
    # 按文件大小轮转的处理器
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),  # 日志文件路径
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,  # 保留10个备份文件
        encoding='utf-8'  # 文件编码
    )
    # 设置文件处理器的格式化器
    file_handler.setFormatter(json_formatter)
    # 设置文件处理器的日志级别
    file_handler.setLevel(logging.INFO)
    # 添加文件处理器到根日志记录器
    root_logger.addHandler(file_handler)
    
    # 创建错误日志处理器（专门记录错误日志）
    error_file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, 'error.log'),  # 错误日志文件路径
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,  # 保留5个备份文件
        encoding='utf-8'  # 文件编码
    )
    # 设置错误日志处理器的格式化器
    error_file_handler.setFormatter(json_formatter)
    # 设置错误日志处理器的日志级别（只记录错误及以上级别）
    error_file_handler.setLevel(logging.ERROR)
    # 添加错误日志处理器到根日志记录器
    root_logger.addHandler(error_file_handler)
    
    # 创建访问日志处理器（专门记录API访问日志）
    access_file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'access.log'),  # 访问日志文件路径
        when='midnight',  # 每天轮转
        backupCount=30,  # 保留30天日志
        encoding='utf-8'  # 文件编码
    )
    # 设置访问日志处理器的格式化器
    access_file_handler.setFormatter(json_formatter)
    # 设置访问日志处理器的日志级别
    access_file_handler.setLevel(logging.INFO)
    # 添加访问日志处理器到根日志记录器
    root_logger.addHandler(access_file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('uvicorn').setLevel(logging.WARNING)  # Uvicorn日志
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)  # Uvicorn访问日志
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # SQLAlchemy引擎日志
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)  # SQLAlchemy连接池日志
    logging.getLogger('httpx').setLevel(logging.WARNING)  # HTTPX客户端日志
    logging.getLogger('httpcore').setLevel(logging.WARNING)  # HTTP核心日志
    
    # 记录日志系统初始化完成
    root_logger.info("日志系统初始化完成", extra={
        "environment": settings.ENVIRONMENT,
        "log_level": settings.LOG_LEVEL,
        "log_dir": log_dir
    })


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        配置好的日志记录器
    """
    return logging.getLogger(name)


def log_extra_data(**kwargs) -> Dict[str, Any]:
    """
    创建额外的日志数据
    
    Args:
        **kwargs: 额外的日志字段
        
    Returns:
        额外的日志数据字典
    """
    return {"extra_data": kwargs}


class RequestContextFilter(logging.Filter):
    """
    请求上下文过滤器 - 为日志记录添加请求上下文信息
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录并添加上下文信息
        
        Args:
            record: 日志记录
            
        Returns:
            是否记录该日志
        """
        # 这里可以添加请求ID、用户ID等上下文信息
        # 简化实现：直接返回True
        return True


# 应用启动时自动配置日志
setup_logging()


内容板块-日志配置文件

import logging
import sys
from logging.handlers import RotatingFileHandler
import json
import os
from datetime import datetime


def setup_logging():
    """设置日志配置"""
    
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    json_format = {
        "timestamp": "%(asctime)s",
        "logger": "%(name)s",
        "level": "%(levelname)s",
        "message": "%(message)s",
        "module": "%(module)s",
        "function": "%(funcName)s",
        "line": "%(lineno)d"
    }
    
    # 根日志配置
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            RotatingFileHandler(
                f"{log_dir}/app.log",
                maxBytes=10485760,  # 10MB
                backupCount=10
            ),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # 创建JSON格式的日志处理器（用于生产环境）
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
            
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            
            return json.dumps(log_data)
    
    # 为API请求添加单独的日志处理器
    api_logger = logging.getLogger("api")
    api_handler = RotatingFileHandler(
        f"{log_dir}/api.log",
        maxBytes=10485760,
        backupCount=5
    )
    api_handler.setFormatter(JSONFormatter())
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)