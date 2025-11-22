商家板块6财务中心
from datetime import datetime
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field, validator, root_validator
import math

DataT = TypeVar('DataT')


class PaginatedResponse(BaseModel, Generic[DataT]):
    """分页响应模型"""
    
    items: List[DataT] = Field(default_factory=list, description="数据列表")
    total: int = Field(0, ge=0, description="总记录数")
    page: int = Field(1, ge=1, description="当前页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")
    total_pages: int = Field(0, ge=0, description="总页数")
    
    @classmethod
    def create(
        cls, 
        items: List[DataT], 
        total: int, 
        page: int, 
        page_size: int
    ) -> 'PaginatedResponse[DataT]':
        """创建分页响应
        
        Args:
            items: 数据列表
            total: 总记录数
            page: 当前页码（从1开始）
            page_size: 每页数量
            
        Returns:
            PaginatedResponse[DataT]: 分页响应对象
        """
        # 参数验证
        if total < 0:
            total = 0
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100
            
        total_pages = math.ceil(total / page_size) if page_size > 0 and total > 0 else 0
        
        # 确保当前页不超过总页数
        if total_pages > 0 and page > total_pages:
            page = total_pages
            
        return cls(
            items=items or [],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.page < self.total_pages
    
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.page > 1
    
    def next_page(self) -> Optional[int]:
        """获取下一页页码"""
        return self.page + 1 if self.has_next() else None
    
    def prev_page(self) -> Optional[int]:
        """获取上一页页码"""
        return self.page - 1 if self.has_prev() else None


class DateRangeParams(BaseModel):
    """日期范围参数"""
    
    start_date: Optional[str] = Field(None, description="开始日期 (格式: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (格式: YYYY-MM-DD)")
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """验证日期格式"""
        if v is not None:
            if not isinstance(v, str):
                raise ValueError('日期必须是字符串格式')
            if len(v) != 10 or v[4] != '-' or v[7] != '-':
                raise ValueError('日期格式必须为 YYYY-MM-DD')
        return v
    
    @root_validator
    def validate_date_range(cls, values):
        """验证日期范围的合理性"""
        start_date, end_date = values.get('start_date'), values.get('end_date')
        if start_date and end_date:
            if start_date > end_date:
                raise ValueError('开始日期不能晚于结束日期')
        return values


class TimeRangeParams(BaseModel):
    """时间范围参数"""
    
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    
    @root_validator
    def validate_time_range(cls, values):
        """验证时间范围的合理性"""
        start_time, end_time = values.get('start_time'), values.get('end_time')
        if start_time and end_time:
            if start_time > end_time:
                raise ValueError('开始时间不能晚于结束时间')
        return values


class SortParams(BaseModel):
    """排序参数"""
    
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序顺序 (asc/desc)")


class SearchParams(BaseModel):
    """搜索参数"""
    
    keyword: Optional[str] = Field(None, description="搜索关键词")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")


class FilterParams(BaseModel):
    """过滤参数基类"""
    
    class Config:
        # 允许额外字段
        extra = "allow"


class ResponseModel(BaseModel, Generic[DataT]):
    """通用响应模型"""
    
    code: int = Field(200, description="响应状态码")
    message: str = Field("success", description="响应消息")
    data: Optional[DataT] = Field(None, description="响应数据")
    
    @classmethod
    def success(cls, data: DataT = None, message: str = "success") -> 'ResponseModel[DataT]':
        """创建成功响应"""
        return cls(code=200, message=message, data=data)
    
    @classmethod
    def error(cls, message: str = "error", code: int = 500) -> 'ResponseModel[DataT]':
        """创建错误响应"""
        return cls(code=code, message=message, data=None)