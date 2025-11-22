内容系统

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form, Query
from pydantic import BaseModel
import json

from app.services.file_service import FileService
from app.services.content_service import ContentService
from app.api.v1.dependencies import (
    GetFileService, GetContentService, GetCurrentActiveUser, RateLimitPerMinute
)
from app.models.content import ContentCreate, ContentType
from app.utils.logger import logger

# 创建文件上传路由
router = APIRouter(prefix="/upload", tags=["upload"])

class UploadResponse(BaseModel):
    """文件上传响应模型"""
    file_id: str
    filename: str
    file_url: str
    thumbnail_url: Optional[str]
    file_size: int
    content_type: str
    metadata: Optional[Dict[str, Any]]

class BatchUploadResponse(BaseModel):
    """批量上传响应模型"""
    successful: List[UploadResponse]
    failed: List[Dict[str, str]]
    total: int

class FileInfoResponse(BaseModel):
    """文件信息响应模型"""
    file_id: str
    filename: str
    file_url: str
    file_size: int
    content_type: str
    created_at: str
    metadata: Optional[Dict[str, Any]]

@router.post("/video", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(..., description="视频文件"),
    title: str = Form(..., description="视频标题"),
    description: str = Form(None, description="视频描述"),
    tags: str = Form("[]", description="视频标签JSON数组"),
    category: str = Form(None, description="视频分类"),
    location: str = Form(None, description="位置信息JSON对象"),
    file_service: FileService = Depends(GetFileService),
    content_service: ContentService = Depends(GetContentService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    rate_limit = Depends(RateLimitPerMinute)
):
    """上传视频文件
    
    上传视频文件并自动创建对应的内容记录。
    """
    try:
        # 处理视频上传
        video_info = await file_service.process_video_upload(file, str(current_user["id"]))
        
        # 解析标签
        try:
            tag_list = json.loads(tags) if tags else []
        except:
            tag_list = []
        
        # 解析位置信息
        location_data = None
        try:
            location_data = json.loads(location) if location else None
        except:
            location_data = None
        
        # 自动创建内容记录
        content_data = ContentCreate(
            title=title,
            description=description,
            content_type=ContentType.VIDEO,
            media_urls=[video_info["url"]],
            thumbnail_url=video_info.get("thumbnail_url"),
            tags=tag_list,
            categories=[category] if category else [],
            location_data=location_data,
            creator_id=current_user["id"]
        )
        
        # 创建内容记录
        content = await content_service.create_content(content_data)
        
        # 构建响应
        response = UploadResponse(
            file_id=video_info["file_id"],
            filename=video_info["filename"],
            file_url=video_info["url"],
            thumbnail_url=video_info.get("thumbnail_url"),
            file_size=video_info["file_size"],
            content_type=video_info["content_type"],
            metadata=video_info.get("metadata")
        )
        
        logger.info(f"视频上传成功: {video_info['file_id']}, 内容ID: {content['id']}")
        return response
        
    except Exception as e:
        logger.error(f"视频上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"视频上传失败: {str(e)}"
        )

@router.post("/image", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(..., description="图片文件"),
    title: str = Form(None, description="图片标题"),
    description: str = Form(None, description="图片描述"),
    tags: str = Form("[]", description="图片标签JSON数组"),
    file_service: FileService = Depends(GetFileService),
    content_service: ContentService = Depends(GetContentService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    rate_limit = Depends(RateLimitPerMinute)
):
    """上传图片文件
    
    上传单个图片文件。
    """
    try:
        # 处理图片上传
        image_info = await file_service.save_upload_file(file, "image", str(current_user["id"]))
        
        # 解析标签
        try:
            tag_list = json.loads(tags) if tags else []
        except:
            tag_list = []
        
        # 如果提供了标题，创建内容记录
        if title:
            content_data = ContentCreate(
                title=title,
                description=description,
                content_type=ContentType.IMAGE,
                media_urls=[image_info["url"]],
                tags=tag_list,
                creator_id=current_user["id"]
            )
            
            # 创建内容记录
            content = await content_service.create_content(content_data)
            logger.info(f"图片内容创建成功: {content['id']}")
        
        # 构建响应
        response = UploadResponse(
            file_id=image_info["file_id"],
            filename=image_info["filename"],
            file_url=image_info["url"],
            thumbnail_url=image_info["url"],  # 图片本身作为缩略图
            file_size=image_info["file_size"],
            content_type=image_info["content_type"]
        )
        
        logger.info(f"图片上传成功: {image_info['file_id']}")
        return response
        
    except Exception as e:
        logger.error(f"图片上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图片上传失败: {str(e)}"
        )

@router.post("/images/batch", response_model=BatchUploadResponse)
async def batch_upload_images(
    files: List[UploadFile] = File(..., description="图片文件列表"),
    file_service: FileService = Depends(GetFileService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    rate_limit = Depends(RateLimitPerMinute)
):
    """批量上传图片文件
    
    同时上传多个图片文件。
    """
    try:
        if len(files) > 10:  # 限制批量上传数量
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="一次最多上传10个文件"
            )
        
        # 批量处理文件
        results = await file_service.batch_process_files(
            files, "image", str(current_user["id"])
        )
        
        successful = []
        failed = []
        
        for result in results:
            if "error" in result:
                failed.append({
                    "filename": result.get("filename", "unknown"),
                    "error": result["error"]
                })
            else:
                successful.append(UploadResponse(
                    file_id=result["file_id"],
                    filename=result["filename"],
                    file_url=result["url"],
                    thumbnail_url=result["url"],
                    file_size=result["file_size"],
                    content_type=result["content_type"]
                ))
        
        response = BatchUploadResponse(
            successful=successful,
            failed=failed,
            total=len(files)
        )
        
        logger.info(f"批量图片上传完成: 成功 {len(successful)}, 失败 {len(failed)}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量图片上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"批量图片上传失败: {str(e)}"
        )

@router.post("/validate")
async def validate_file(
    file: UploadFile = File(..., description="待验证文件"),
    file_type: str = Form("video", description="文件类型: video, image, document"),
    file_service: FileService = Depends(GetFileService)
):
    """验证文件（不保存）
    
    验证文件是否符合系统要求，但不实际保存文件。
    """
    try:
        # 验证文件
        file_info = await file_service.validate_file(file, file_type)
        
        return {
            "is_valid": file_info["is_valid"],
            "file_info": file_info
        }
        
    except Exception as e:
        logger.error(f"文件验证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件验证失败: {str(e)}"
        )

@router.delete("/file/{file_id}")
async def delete_uploaded_file(
    file_id: str,
    file_type: str = Query(..., description="文件类型: video, image, document"),
    file_service: FileService = Depends(GetFileService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """删除已上传的文件
    
    删除指定的已上传文件。
    """
    try:
        # 根据文件类型确定存储目录
        if file_type == "video":
            storage_dir = file_service.video_dir
        elif file_type == "image":
            storage_dir = file_service.image_dir
        else:
            storage_dir = file_service.document_dir
        
        # 查找文件（尝试不同的扩展名）
        import glob
        from pathlib import Path
        
        # 构建可能的文件路径模式
        file_patterns = [
            str(storage_dir / f"{file_id}.*"),
            str(storage_dir / f"{file_id}_*.*")  # 包含时间戳的文件名
        ]
        
        actual_files = []
        for pattern in file_patterns:
            actual_files.extend(glob.glob(pattern))
        
        if not actual_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 删除所有匹配的文件（包括缩略图等）
        deleted_count = 0
        for file_path in actual_files:
            success = await file_service.delete_file(file_path)
            if success:
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"文件删除成功: {file_id}, 删除了 {deleted_count} 个文件")
            return {"message": f"文件删除成功，共删除 {deleted_count} 个文件"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件删除失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败 {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件删除失败"
        )

@router.get("/file/{file_id}", response_model=FileInfoResponse)
async def get_file_info(
    file_id: str,
    file_type: str = Query(..., description="文件类型: video, image, document"),
    file_service: FileService = Depends(GetFileService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """获取文件信息
    
    获取已上传文件的详细信息。
    """
    try:
        # 根据文件类型确定存储目录
        file_info = file_service.get_file_info(file_type, file_id)
        
        if not file_info:
            # 尝试带扩展名的查找
            import glob
            from pathlib import Path
            
            if file_type == "video":
                storage_dir = file_service.video_dir
            elif file_type == "image":
                storage_dir = file_service.image_dir
            else:
                storage_dir = file_service.document_dir
            
            # 查找文件
            file_patterns = [
                str(storage_dir / f"{file_id}.*"),
                str(storage_dir / f"{file_id}_*.*")
            ]
            
            actual_files = []
            for pattern in file_patterns:
                actual_files.extend(glob.glob(pattern))
            
            if not actual_files:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="文件不存在"
                )
            
            # 使用第一个找到的文件
            file_path = actual_files[0]
            file_info = file_service.get_file_info(file_type, Path(file_path).name)
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件信息不存在"
            )
        
        # 构建响应
        response = FileInfoResponse(
            file_id=file_id,
            filename=file_info["filename"],
            file_url=file_info["url"],
            file_size=file_info["file_size"],
            content_type=file_info.get("content_type", "unknown"),
            created_at=file_info["created_time"],
            metadata=file_info.get("metadata")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败 {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件信息失败"
        )

@router.get("/quota")
async def get_upload_quota(
    file_service: FileService = Depends(GetFileService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """获取上传配额信息
    
    获取当前用户的上传配额和使用情况。
    """
    try:
        # 这里应该查询数据库获取用户的配额信息
        # 暂时返回模拟数据
        
        quota_info = {
            "user_id": current_user["id"],
            "total_quota": 10 * 1024 * 1024 * 1024,  # 10GB
            "used_quota": 2 * 1024 * 1024 * 1024,    # 2GB
            "remaining_quota": 8 * 1024 * 1024 * 1024, # 8GB
            "quota_reset_date": "2023-12-01"  # 配额重置日期
        }
        
        return quota_info
        
    except Exception as e:
        logger.error(f"获取上传配额失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取上传配额失败"
        )

@router.post("/presigned-url")
async def generate_presigned_url(
    file_type: str = Form(..., description="文件类型: video, image, document"),
    file_name: str = Form(..., description="文件名"),
    content_type: str = Form(..., description="MIME类型"),
    file_service: FileService = Depends(GetFileService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """生成预签名上传URL
    
    为大文件上传生成预签名URL，支持分片上传。
    """
    try:
        # 这里应该调用云存储服务生成预签名URL
        # 暂时返回模拟数据
        
        presigned_info = {
            "upload_url": f"https://storage.example.com/upload/{file_type}/{file_name}",
            "expires_in": 3600,  # 1小时过期
            "file_id": "temp_file_id",
            "max_file_size": 5 * 1024 * 1024 * 1024  # 5GB
        }
        
        return presigned_info
        
    except Exception as e:
        logger.error(f"生成预签名URL失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成预签名URL失败"
        )