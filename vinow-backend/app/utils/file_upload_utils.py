# app/utils/file_upload.py
import os
import uuid
from fastapi import UploadFile, HTTPException
from typing import List
import logging

logger = logging.getLogger(__name__)

class FileUploadService:
    """文件上传服务"""
    
    def __init__(self, upload_dir: str = "app/static/uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    async def upload_content_file(self, file: UploadFile, merchant_id: str, content_type: str) -> str:
        """上传内容文件"""
        try:
            # 验证文件类型
            allowed_types = {
                'image': ['.jpg', '.jpeg', '.png', '.gif'],
                'video': ['.mp4', '.mov', '.avi', '.mkv']
            }
            
            file_extension = os.path.splitext(file.filename)[1].lower()
            if content_type == 'image' and file_extension not in allowed_types['image']:
                raise HTTPException(status_code=400, detail="不支持的图片格式")
            if content_type == 'video' and file_extension not in allowed_types['video']:
                raise HTTPException(status_code=400, detail="不支持的视频格式")
            
            # 生成唯一文件名
            filename = f"{merchant_id}_{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(self.upload_dir, "content", filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 保存文件
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # 返回文件URL（相对路径）
            return f"/static/uploads/content/{filename}"
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise HTTPException(status_code=500, detail="文件上传失败")
    
    async def upload_multiple_files(self, files: List[UploadFile], merchant_id: str) -> List[str]:
        """上传多个文件"""
        urls = []
        for file in files:
            url = await self.upload_content_file(file, merchant_id, 'image')
            urls.append(url)
        return urls

# 全局文件上传服务实例
file_upload_service = FileUploadService()