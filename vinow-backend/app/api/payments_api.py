交易系统

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from typing import Optional, Dict, Any
from datetime import datetime
import json
from app.schemas.payment_schemas import PaymentCreate, PaymentResponse, PaymentCallback
from app.services.payment_service import PaymentService
from app.services.order_service import OrderService
from app.auth.middleware_auth import JWTBearer
from app.utils.logger_api import logger, payment_logger
from app.middleware.rate_limiter_middleware import RateLimitMiddleware
from app.config import settings

# 创建API路由器
router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    responses={404: {"description": "Not found"}}
)

# 初始化服务
payment_service = PaymentService()
order_service = OrderService()

# 设置服务依赖（避免循环导入）
payment_service.set_order_service(order_service)

# 配置速率限制中间件
rate_limiter = RateLimitMiddleware(
    app=None,  # 在主应用中注册
    default_limits={
        "anonymous": {"requests": 30, "window": 60},      # 匿名用户每分钟30次
        "authenticated": {"requests": 200, "window": 60}, # 认证用户每分钟200次
    }
)

# 为特定路由设置更严格的限流
rate_limiter.set_route_limit("/api/v1/payments/", 100, 60)  # 创建支付每分钟100次
rate_limiter.set_route_limit("/api/v1/payments/callback", 500, 60)  # 回调每分钟500次

@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建支付订单",
    description="为指定订单创建支付记录并初始化支付流程",
    responses={
        201: {"description": "支付创建成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权访问"},
        404: {"description": "订单不存在"},
        500: {"description": "服务器内部错误"}
    }
)
async def create_payment(
    payment_data: PaymentCreate,
    user_info: dict = Depends(JWTBearer()),
    background_tasks: BackgroundTasks = None,
    request: Request = None
):
    """
    创建支付订单
    
    此接口用于为指定订单创建支付记录，并根据选择的支付方式初始化支付流程。
    
    Args:
        payment_data (PaymentCreate): 支付创建数据
        user_info (dict): 从JWT token解析的用户信息
        background_tasks (BackgroundTasks): 后台任务队列
        request (Request): 请求对象
        
    Returns:
        PaymentResponse: 支付详情信息
        
    Raises:
        HTTPException: 当发生错误时抛出相应HTTP异常
    """
    try:
        # 验证用户信息
        user_id = user_info.get("sub")  # 使用标准JWT sub字段作为用户ID
        if not user_id:
            logger.warning(
                "payment_create_missing_user_id",
                client_ip=_get_client_ip(request),
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        # 记录支付创建请求
        payment_logger.log_payment_creation(
            payment_id="",  # 尚未生成
            order_id=payment_data.order_id,
            amount=payment_data.amount,
            method=payment_data.method.value,
            user_id=user_id,
            trace_id=getattr(request.state, 'trace_id', None) if hasattr(request, 'state') else None
        )
        
        # 创建支付记录
        payment = await payment_service.create_payment(payment_data, user_id)
        
        # 记录成功创建的支付
        payment_logger.log_payment_creation(
            payment_id=payment.id,
            order_id=payment.order_id,
            amount=payment.amount,
            method=payment.method.value,
            user_id=user_id,
            trace_id=getattr(request.state, 'trace_id', None) if hasattr(request, 'state') else None
        )
        
        logger.info(
            "payment_created_successfully",
            payment_id=payment.id,
            order_id=payment.order_id,
            user_id=user_id,
            amount=payment.amount,
            method=payment.method.value
        )
        
        return payment
        
    except HTTPException:
        # 重新抛出已知的HTTP异常
        raise
    except Exception as e:
        logger.error(
            "payment_create_unexpected_error",
            user_id=user_id if 'user_id' in locals() else None,
            order_id=payment_data.order_id if 'payment_data' in locals() else None,
            error=str(e),
            error_type=type(e).__name__,
            traceback=str(e.__traceback__)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment"
        )

@router.post(
    "/callback/{gateway}",
    summary="支付回调接口",
    description="处理来自第三方支付平台的支付回调通知",
    responses={
        200: {"description": "回调处理成功"},
        400: {"description": "回调数据验证失败"},
        500: {"description": "服务器内部错误"}
    }
)
async def payment_callback(
    gateway: str,  # 支付网关标识（如momo, zalopay, vnpay）
    callback_data: PaymentCallback,
    request: Request,
    background_tasks: BackgroundTasks = None
):
    """
    支付回调接口
    
    接收并处理来自第三方支付平台的支付结果回调通知。
    支持多个支付网关的回调处理。
    
    Args:
        gateway (str): 支付网关标识
        callback_data (PaymentCallback): 回调数据
        request (Request): 请求对象
        background_tasks (BackgroundTasks): 后台任务队列
        
    Returns:
        dict: 回调处理结果
    """
    try:
        # 获取客户端IP
        client_ip = _get_client_ip(request)
        
        # 验证支付网关
        supported_gateways = ["momo", "zalopay", "vnpay", "credit_card"]
        if gateway not in supported_gateways:
            logger.warning(
                "payment_callback_unsupported_gateway",
                gateway=gateway,
                client_ip=client_ip,
                path=request.url.path
            )
            return {
                "code": 400,
                "message": f"Unsupported payment gateway: {gateway}"
            }
        
        # 记录回调接收
        payment_logger.log_payment_callback(
            payment_id=callback_data.payment_id,
            status=callback_data.status.value,
            callback_data=callback_data.dict(),
            trace_id=getattr(request.state, 'trace_id', None) if hasattr(request, 'state') else None
        )
        
        logger.info(
            "payment_callback_received",
            gateway=gateway,
            payment_id=callback_data.payment_id,
            transaction_id=callback_data.transaction_id,
            status=callback_data.status.value,
            client_ip=client_ip
        )
        
        # 处理支付回调
        payment = await payment_service.process_payment_callback(callback_data, client_ip)
        
        # 记录回调处理成功
        payment_logger.log_payment_success(
            payment_id=callback_data.payment_id,
            transaction_id=callback_data.transaction_id,
            trace_id=getattr(request.state, 'trace_id', None) if hasattr(request, 'state') else None
        )
        
        logger.info(
            "payment_callback_processed",
            payment_id=payment.id,
            status=payment.status.value,
            gateway=gateway
        )
        
        return {
            "code": 0,
            "message": "Callback processed successfully",
            "data": {
                "payment_id": payment.id,
                "status": payment.status.value,
                "transaction_id": callback_data.transaction_id
            }
        }
        
    except HTTPException as e:
        logger.error(
            "payment_callback_http_error",
            gateway=gateway if 'gateway' in locals() else None,
            error=str(e.detail),
            client_ip=_get_client_ip(request),
            status_code=e.status_code
        )
        return {
            "code": e.status_code,
            "message": str(e.detail)
        }
    except Exception as e:
        logger.error(
            "payment_callback_unexpected_error",
            gateway=gateway if 'gateway' in locals() else None,
            error=str(e),
            error_type=type(e).__name__,
            client_ip=_get_client_ip(request)
        )
        return {
            "code": 500,
            "message": "Internal server error"
        }

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="获取支付详情",
    description="根据支付ID获取支付记录的详细信息",
    responses={
        200: {"description": "获取支付详情成功"},
        401: {"description": "未授权访问"},
        404: {"description": "支付记录不存在"},
        500: {"description": "服务器内部错误"}
    }
)
async def get_payment(
    payment_id: str,
    user_info: dict = Depends(JWTBearer()),
    request: Request = None
):
    """
    获取支付详情
    
    根据支付ID获取支付记录的详细信息，包括支付状态、金额、时间等。
    
    Args:
        payment_id (str): 支付ID
        user_info (dict): 从JWT token解析的用户信息
        request (Request): 请求对象
        
    Returns:
        PaymentResponse: 支付详情信息
        
    Raises:
        HTTPException: 当发生错误时抛出相应HTTP异常
    """
    try:
        # 验证用户信息
        user_id = user_info.get("sub")
        if not user_id:
            logger.warning(
                "payment_get_missing_user_id",
                payment_id=payment_id,
                client_ip=_get_client_ip(request),
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        logger.info(
            "payment_get_requested",
            payment_id=payment_id,
            user_id=user_id,
            client_ip=_get_client_ip(request)
        )
        
        # 获取支付详情
        payment = await payment_service.get_payment_by_id(payment_id, user_id)
        
        logger.info(
            "payment_get_success",
            payment_id=payment_id,
            user_id=user_id
        )
        
        return payment
        
    except HTTPException:
        # 重新抛出已知的HTTP异常
        raise
    except Exception as e:
        logger.error(
            "payment_get_unexpected_error",
            payment_id=payment_id if 'payment_id' in locals() else None,
            user_id=user_id if 'user_id' in locals() else None,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment details"
        )

@router.get(
    "/order/{order_id}",
    response_model=PaymentResponse,
    summary="根据订单ID获取支付信息",
    description="根据订单ID获取对应的支付记录信息",
    responses={
        200: {"description": "获取支付信息成功"},
        401: {"description": "未授权访问"},
        404: {"description": "支付记录不存在"},
        500: {"description": "服务器内部错误"}
    }
)
async def get_payment_by_order(
    order_id: str,
    user_info: dict = Depends(JWTBearer()),
    request: Request = None
):
    """
    根据订单ID获取支付信息
    
    根据订单ID查找并返回对应的支付记录信息。
    
    Args:
        order_id (str): 订单ID
        user_info (dict): 从JWT token解析的用户信息
        request (Request): 请求对象
        
    Returns:
        PaymentResponse: 支付详情信息
    """
    try:
        user_id = user_info.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        logger.info(
            "payment_get_by_order_requested",
            order_id=order_id,
            user_id=user_id
        )
        
        payment = await payment_service.get_payment_by_order_id(order_id, user_id)
        
        logger.info(
            "payment_get_by_order_success",
            order_id=order_id,
            payment_id=payment.id,
            user_id=user_id
        )
        
        return payment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "payment_get_by_order_error",
            order_id=order_id,
            user_id=user_id if 'user_id' in locals() else None,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment by order"
        )

def _get_client_ip(request: Request) -> Optional[str]:
    """
    获取客户端真实IP地址
    
    Args:
        request (Request): 请求对象
        
    Returns:
        str: 客户端IP地址
    """
    if not request:
        return None
        
    # 检查常见的代理头部
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
        
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
        
    cf_connecting_ip = request.headers.get("cf-connecting-ip")
    if cf_connecting_ip:
        return cf_connecting_ip
        
    # 回退到直接客户端IP
    if request.client:
        return request.client.host
        
    return None

# 健康检查端点
@router.get(
    "/health",
    summary="支付服务健康检查",
    description="检查支付服务是否正常运行",
    include_in_schema=False  # 不包含在API文档中
)
async def health_check():
    """
    健康检查端点
    
    用于检查支付服务是否正常运行。
    
    Returns:
        dict: 健康状态信息
    """
    return {
        "status": "healthy",
        "service": "payment-service",
        "timestamp": datetime.utcnow().isoformat()
    }

# API文档自定义信息
router.openapi_tags = [{
    "name": "payments",
    "description": "支付相关接口，包括创建支付、处理回调、查询支付状态等功能。",
    "externalDocs": {
        "description": "支付集成文档",
        "url": "https://docs.example.com/payments"
    }
}]