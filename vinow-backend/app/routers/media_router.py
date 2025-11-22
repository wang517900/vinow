内容系统
from typing import List, Optional, Dict, Any  # 导入类型注解
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Request  # 导入FastAPI相关依赖
from app.schemas.media_schemas import MediaUploadResponseSchema, ChunkedUploadResponseSchema  # 导入媒体上传数据模式
from app.schemas.response_schemas import StandardResponse, create_success_response  # 导入响应模式
from app.services.storage_service import storage_service  # 导入存储服务
from app.utils.security import get_current_user  # 导入安全工具
import logging  # 导入日志模块
import uuid  # 导入UUID生成模块

# 创建媒体上传路由的APIRouter实例
router = APIRouter(prefix="/media", tags=["media"])

# 获取日志记录器
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=StandardResponse[MediaUploadResponseSchema])
async def upload_media(
    file: UploadFile = File(..., description="上传的媒体文件"),  # 文件上传参数
    content_type: str = Form(..., description="内容类型"),  # 内容类型表单参数
    background_tasks: BackgroundTasks = None,  # 后台任务管理器
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    上传媒体文件（图片、视频等）
    
    Args:
        file: 上传的媒体文件
        content_type: 内容类型
        background_tasks: 后台任务管理器
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        媒体上传响应
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用存储服务上传文件
        upload_result = await storage_service.upload_file(
            file=file,
            user_id=user_id,
            content_type=content_type,
            background_tasks=background_tasks
        )
        
        # 记录成功日志
        logger.info(f"媒体文件上传成功: {upload_result['file_name']}, 用户: {user_id}, 大小: {upload_result['file_size']}字节")
        
        # 返回成功响应
        return create_success_response(
            data=upload_result,
            message="文件上传成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"媒体文件上传异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败，请稍后重试"
        )

@router.post("/upload-chunk", response_model=StandardResponse[ChunkedUploadResponseSchema])
async def upload_chunked_media(
    chunk: UploadFile = File(..., description="文件分片"),  # 文件分片上传参数
    upload_id: str = Form(..., description="上传会话ID"),  # 上传ID表单参数
    chunk_number: int = Form(..., ge=1, description="当前分片序号"),  # 分片序号表单参数
    total_chunks: int = Form(..., ge=1, description="总分片数"),  # 总分片数表单参数
    original_filename: str = Form(..., description="原始文件名"),  # 原始文件名表单参数
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    分片上传媒体文件（支持大文件上传）
    
    Args:
        chunk: 文件分片
        upload_id: 上传会话ID
        chunk_number: 当前分片序号
        total_chunks: 总分片数
        original_filename: 原始文件名
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        分片上传响应
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用存储服务分片上传文件
        upload_result = await storage_service.upload_chunked_file(
            chunk=chunk,
            upload_id=upload_id,
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            user_id=user_id,
            original_filename=original_filename
        )
        
        # 记录成功日志
        logger.info(f"文件分片上传成功: 分片{chunk_number}/{total_chunks}, 上传ID: {upload_id}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=upload_result,
            message="文件分片上传成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"文件分片上传异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件分片上传失败，请稍后重试"
        )

@router.delete("/{file_path:path}", response_model=StandardResponse[bool])
async def delete_media(
    file_path: str,  # 文件路径参数
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    删除媒体文件
    
    Args:
        file_path: 文件路径
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        删除操作结果
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用存储服务删除文件
        success = await storage_service.delete_file(file_path, user_id)
        
        # 检查删除是否成功
        if not success:
            # 返回404错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或删除失败"
            )
        
        # 记录成功日志
        logger.info(f"媒体文件删除成功: {file_path}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=True,
            message="文件删除成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"删除媒体文件异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件删除失败，请稍后重试"
        )

@router.get("/presigned-url/{file_path:path}", response_model=StandardResponse[Dict[str, str]])
async def generate_presigned_url(
    file_path: str,  # 文件路径参数
    expires_in: int = Query(3600, ge=60, le=86400, description="URL过期时间（秒）"),  # 过期时间查询参数
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    生成预签名URL（用于安全访问私有文件）
    
    Args:
        file_path: 文件路径
        expires_in: URL过期时间（秒）
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        预签名URL响应
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用存储服务生成预签名URL
        presigned_url = await storage_service.generate_presigned_url(file_path, expires_in)
        
        # 检查URL是否成功生成
        if not presigned_url:
            # 返回404错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或无法生成访问URL"
            )
        
        # 记录成功日志
        logger.info(f"预签名URL生成成功: {file_path}, 用户: {user_id}, 过期时间: {expires_in}秒")
        
        # 返回成功响应
        return create_success_response(
            data={"presigned_url": presigned_url},
            message="预签名URL生成成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"生成预签名URL异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成访问URL失败，请稍后重试"
        )

@router.post("/initiate-upload", response_model=StandardResponse[Dict[str, str]])
async def initiate_chunked_upload(
    file_name: str = Form(..., description="文件名"),  # 文件名表单参数
    file_size: int = Form(..., ge=1, description="文件大小（字节）"),  # 文件大小表单参数
    content_type: str = Form(..., description="文件类型"),  # 文件类型表单参数
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    初始化分片上传会话
    
    Args:
        file_name: 文件名
        file_size: 文件大小（字节）
        content_type: 文件类型
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        初始化上传响应
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 生成唯一的上传会话ID
        upload_id = str(uuid.uuid4())
        
        # 计算建议的分片大小（默认为5MB）
        chunk_size = 5 * 1024 * 1024  # 5MB
        # 计算总分片数
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        # 记录初始化日志
        logger.info(f"分片上传初始化: 文件{file_name}, 大小{file_size}字节, 总分片{total_chunks}, 上传ID: {upload_id}, 用户: {user_id}")
        
        # 返回初始化结果
        return create_success_response(
            data={
                "upload_id": upload_id,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "file_name": file_name,
                "file_size": file_size
            },
            message="分片上传初始化成功"
        )
        
    except Exception as e:
        # 记录错误日志
        logger.error(f"初始化分片上传异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="初始化上传失败，请稍后重试"
        )