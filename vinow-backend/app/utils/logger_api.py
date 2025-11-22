交易系统

import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union
import structlog
from app.config import settings

def setup_logging() -> structlog.BoundLogger:
    """
    配置结构化日志系统
    
    根据应用配置初始化structlog和标准logging，
    提供JSON格式的日志输出以便于日志收集和分析
    
    Returns:
        structlog.BoundLogger: 配置好的结构化日志记录器
        
    Example:
        >>> logger = setup_logging()
        >>> logger.info("app_started", version="1.0.0")
    """
    try:
        # 配置structlog处理器链
        structlog.configure(
            processors=[
                # 根据日志级别过滤
                structlog.stdlib.filter_by_level,
                # 添加logger名称
                structlog.stdlib.add_logger_name,
                # 添加日志级别
                structlog.stdlib.add_log_level,
                # 格式化位置参数
                structlog.stdlib.PositionalArgumentsFormatter(),
                # 添加时间戳
                structlog.processors.TimeStamper(fmt="iso"),
                # 渲染堆栈信息
                structlog.processors.StackInfoRenderer(),
                # 格式化异常信息
                structlog.processors.format_exc_info,
                # 解码Unicode字符
                structlog.processors.UnicodeDecoder(),
                # JSON渲染器
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # 配置标准logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.INFO if not settings.debug else logging.DEBUG,
        )
        
        # 返回配置好的logger
        return structlog.get_logger()
        
    except Exception as e:
        # 如果结构化日志配置失败，回退到标准日志
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO if not settings.debug else logging.DEBUG,
        )
        logging.error(f"Failed to setup structured logging, fallback to standard logging: {e}")
        return structlog.get_logger()

# 全局日志实例
logger = setup_logging()

class BaseLogger:
    """
    基础日志器类
    
    提供通用的日志记录方法和辅助功能
    """
    
    def __init__(self, logger_instance: structlog.BoundLogger = None):
        """
        初始化基础日志器
        
        Args:
            logger_instance: 日志实例，默认使用全局logger
        """
        self.logger = logger_instance or logger
    
    def _log_with_trace(self, level: str, event: str, trace_id: Optional[str] = None, **kwargs):
        """
        带追踪ID的日志记录
        
        Args:
            level: 日志级别
            event: 事件名称
            trace_id: 追踪ID
            **kwargs: 其他日志字段
        """
        if trace_id:
            kwargs['trace_id'] = trace_id
            
        getattr(self.logger, level)(event, **kwargs)

class PaymentLogger(BaseLogger):
    """
    支付专用日志器
    
    记录支付相关的操作和事件，便于支付流程追踪和问题排查
    """
    
    def log_payment_creation(self, payment_id: str, order_id: str, amount: float, 
                           method: str, user_id: Optional[str] = None, 
                           trace_id: Optional[str] = None):
        """
        记录支付创建事件
        
        Args:
            payment_id: 支付ID
            order_id: 订单ID
            amount: 支付金额
            method: 支付方式
            user_id: 用户ID（可选）
            trace_id: 请求追踪ID（可选）
            
        Example:
            >>> payment_logger = PaymentLogger()
            >>> payment_logger.log_payment_creation("pay_123", "ord_456", 100.0, "momo")
        """
        self._log_with_trace(
            "info",
            "payment_created",
            trace_id=trace_id,
            payment_id=payment_id,
            order_id=order_id,
            amount=amount,
            method=method,
            user_id=user_id
        )
    
    def log_payment_processing(self, payment_id: str, gateway: str, 
                              request_data: Dict[str, Any],
                              trace_id: Optional[str] = None):
        """
        记录支付处理事件
        
        Args:
            payment_id: 支付ID
            gateway: 支付网关
            request_data: 发送到网关的请求数据
            trace_id: 请求追踪ID（可选）
        """
        self._log_with_trace(
            "info",
            "payment_processing",
            trace_id=trace_id,
            payment_id=payment_id,
            gateway=gateway,
            request_data=request_data
        )
    
    def log_payment_success(self, payment_id: str, transaction_id: str,
                           response_data: Optional[Dict[str, Any]] = None,
                           trace_id: Optional[str] = None):
        """
        记录支付成功事件
        
        Args:
            payment_id: 支付ID
            transaction_id: 网关交易ID
            response_data: 网关响应数据（可选）
            trace_id: 请求追踪ID（可选）
            
        Example:
            >>> payment_logger.log_payment_success("pay_123", "txn_789")
        """
        self._log_with_trace(
            "info",
            "payment_success",
            trace_id=trace_id,
            payment_id=payment_id,
            transaction_id=transaction_id,
            response_data=response_data
        )
    
    def log_payment_failure(self, payment_id: str, error: str,
                           error_code: Optional[str] = None,
                           trace_id: Optional[str] = None):
        """
        记录支付失败事件
        
        Args:
            payment_id: 支付ID
            error: 错误信息
            error_code: 错误代码（可选）
            trace_id: 请求追踪ID（可选）
            
        Example:
            >>> payment_logger.log_payment_failure("pay_123", "网络超时", "TIMEOUT")
        """
        self._log_with_trace(
            "error",
            "payment_failed",
            trace_id=trace_id,
            payment_id=payment_id,
            error=error,
            error_code=error_code
        )
    
    def log_payment_callback(self, payment_id: str, status: str,
                            callback_data: Dict[str, Any],
                            trace_id: Optional[str] = None):
        """
        记录支付回调事件
        
        Args:
            payment_id: 支付ID
            status: 回调状态
            callback_data: 回调数据
            trace_id: 请求追踪ID（可选）
        """
        self._log_with_trace(
            "info",
            "payment_callback_received",
            trace_id=trace_id,
            payment_id=payment_id,
            status=status,
            callback_data=callback_data
        )

class OrderLogger(BaseLogger):
    """
    订单专用日志器
    
    记录订单相关的操作和事件，便于订单流程追踪
    """
    
    def log_order_creation(self, order_id: str, user_id: str, amount: float,
                          items: Optional[list] = None, trace_id: Optional[str] = None):
        """
        记录订单创建事件
        
        Args:
            order_id: 订单ID
            user_id: 用户ID
            amount: 订单金额
            items: 订单项目列表（可选）
            trace_id: 请求追踪ID（可选）
            
        Example:
            >>> order_logger = OrderLogger()
            >>> order_logger.log_order_creation("ord_123", "user_456", 200.0)
        """
        self._log_with_trace(
            "info",
            "order_created",
            trace_id=trace_id,
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            items=items
        )
    
    def log_order_status_change(self, order_id: str, old_status: str, new_status: str,
                               reason: Optional[str] = None, trace_id: Optional[str] = None):
        """
        记录订单状态变更事件
        
        Args:
            order_id: 订单ID
            old_status: 原状态
            new_status: 新状态
            reason: 变更原因（可选）
            trace_id: 请求追踪ID（可选）
            
        Example:
            >>> order_logger.log_order_status_change("ord_123", "pending", "paid")
        """
        self._log_with_trace(
            "info",
            "order_status_changed",
            trace_id=trace_id,
            order_id=order_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason
        )
    
    def log_order_cancellation(self, order_id: str, user_id: str,
                              reason: str, trace_id: Optional[str] = None):
        """
        记录订单取消事件
        
        Args:
            order_id: 订单ID
            user_id: 用户ID
            reason: 取消原因
            trace_id: 请求追踪ID（可选）
        """
        self._log_with_trace(
            "info",
            "order_cancelled",
            trace_id=trace_id,
            order_id=order_id,
            user_id=user_id,
            reason=reason
        )

class SystemLogger(BaseLogger):
    """
    系统级日志器
    
    记录系统级别的事件和错误
    """
    
    def log_system_startup(self, version: str, environment: str):
        """
        记录系统启动事件
        
        Args:
            version: 应用版本
            environment: 运行环境
        """
        self.logger.info(
            "system_started",
            version=version,
            environment=environment,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_system_error(self, error: str, traceback_info: Optional[str] = None,
                        component: Optional[str] = None):
        """
        记录系统错误
        
        Args:
            error: 错误信息
            traceback_info: 堆栈追踪信息（可选）
            component: 出错组件（可选）
        """
        self.logger.error(
            "system_error",
            error=error,
            traceback=traceback_info or traceback.format_exc(),
            component=component
        )
    
    def log_external_api_call(self, api_name: str, request: Dict[str, Any],
                             response: Optional[Dict[str, Any]] = None,
                             duration: Optional[float] = None,
                             trace_id: Optional[str] = None):
        """
        记录外部API调用
        
        Args:
            api_name: API名称
            request: 请求数据
            response: 响应数据（可选）
            duration: 调用耗时（秒，可选）
            trace_id: 请求追踪ID（可选）
        """
        self._log_with_trace(
            "info",
            "external_api_called",
            trace_id=trace_id,
            api_name=api_name,
            request=request,
            response=response,
            duration=duration
        )

# 创建全局日志器实例
payment_logger = PaymentLogger()
order_logger = OrderLogger()
system_logger = SystemLogger()

# 为了向后兼容，保留原有的logger
def get_logger() -> structlog.BoundLogger:
    """
    获取全局日志实例（向后兼容）
    
    Returns:
        structlog.BoundLogger: 全局日志实例
    """
    return logger