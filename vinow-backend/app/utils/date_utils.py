商家板块6财务中心
from datetime import datetime, date, timedelta
from typing import Tuple, Optional
import calendar
import logging

logger = logging.getLogger(__name__)

class DateUtils:
    """日期工具类"""
    
    @staticmethod
    def get_today() -> date:
        """获取今天日期
        
        Returns:
            date: 今天的日期对象
        """
        return date.today()
    
    @staticmethod
    def get_yesterday() -> date:
        """获取昨天日期
        
        Returns:
            date: 昨天的日期对象
        """
        return date.today() - timedelta(days=1)
    
    @staticmethod
    def get_week_range(target_date: date = None) -> Tuple[date, date]:
        """获取指定日期所在周的起始和结束日期（周一到周日）
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            Tuple[date, date]: (周一日期, 周日日期)
            
        Raises:
            TypeError: 当target_date不是date类型时
        """
        if target_date is None:
            target_date = date.today()
        
        if not isinstance(target_date, date):
            raise TypeError("target_date必须是date类型")
            
        # 验证日期合理性
        if target_date.year < 1900 or target_date.year > 2100:
            raise ValueError("日期年份必须在1900-2100之间")
        
        start_date = target_date - timedelta(days=target_date.weekday())
        end_date = start_date + timedelta(days=6)
        return start_date, end_date
    
    @staticmethod
    def get_month_range(target_date: date = None) -> Tuple[date, date]:
        """获取指定日期所在月的起始和结束日期
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            Tuple[date, date]: (月初日期, 月末日期)
            
        Raises:
            TypeError: 当target_date不是date类型时
        """
        if target_date is None:
            target_date = date.today()
            
        if not isinstance(target_date, date):
            raise TypeError("target_date必须是date类型")
            
        # 验证日期合理性
        if target_date.year < 1900 or target_date.year > 2100:
            raise ValueError("日期年份必须在1900-2100之间")
        
        start_date = date(target_date.year, target_date.month, 1)
        last_day = calendar.monthrange(target_date.year, target_date.month)[1]
        end_date = date(target_date.year, target_date.month, last_day)
        return start_date, end_date
    
    @staticmethod
    def get_quarter_range(target_date: date = None) -> Tuple[date, date]:
        """获取指定日期所在季度的起始和结束日期
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            Tuple[date, date]: (季度初日期, 季度末日期)
            
        Raises:
            TypeError: 当target_date不是date类型时
        """
        if target_date is None:
            target_date = date.today()
            
        if not isinstance(target_date, date):
            raise TypeError("target_date必须是date类型")
            
        # 验证日期合理性
        if target_date.year < 1900 or target_date.year > 2100:
            raise ValueError("日期年份必须在1900-2100之间")
        
        quarter = (target_date.month - 1) // 3 + 1
        start_month = 3 * (quarter - 1) + 1
        end_month = start_month + 2
        
        start_date = date(target_date.year, start_month, 1)
        last_day = calendar.monthrange(target_date.year, end_month)[1]
        end_date = date(target_date.year, end_month, last_day)
        return start_date, end_date
    
    @staticmethod
    def get_year_range(target_date: date = None) -> Tuple[date, date]:
        """获取指定日期所在年的起始和结束日期
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            Tuple[date, date]: (年初日期, 年末日期)
            
        Raises:
            TypeError: 当target_date不是date类型时
        """
        if target_date is None:
            target_date = date.today()
            
        if not isinstance(target_date, date):
            raise TypeError("target_date必须是date类型")
            
        # 验证日期合理性
        if target_date.year < 1900 or target_date.year > 2100:
            raise ValueError("日期年份必须在1900-2100之间")
        
        start_date = date(target_date.year, 1, 1)
        end_date = date(target_date.year, 12, 31)
        return start_date, end_date
    
    @staticmethod
    def format_date_for_query(date_str: str) -> Optional[date]:
        """格式化查询日期字符串为日期对象
        
        Args:
            date_str: 日期字符串，格式应为YYYY-MM-DD
            
        Returns:
            Optional[date]: 解析成功的日期对象，解析失败返回None
        """
        if not date_str or not isinstance(date_str, str):
            return None
        
        # 去除首尾空格
        date_str = date_str.strip()
        
        if not date_str:
            return None
            
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            # 验证日期合理性
            if parsed_date.year < 1900 or parsed_date.year > 2100:
                logger.warning(f"日期年份超出合理范围: {parsed_date.year}")
                return None
            return parsed_date
        except ValueError as e:
            logger.warning(f"日期格式解析失败: {date_str}, 错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"日期解析发生未知错误: {date_str}, 错误: {str(e)}")
            return None
    
    @staticmethod
    def calculate_date_range(
        start_date_str: str = None,
        end_date_str: str = None,
        default_days: int = 7
    ) -> Tuple[date, date]:
        """计算日期范围
        
        Args:
            start_date_str: 开始日期字符串，格式YYYY-MM-DD
            end_date_str: 结束日期字符串，格式YYYY-MM-DD
            default_days: 默认天数，当未指定start_date_str时使用
            
        Returns:
            Tuple[date, date]: (开始日期, 结束日期)
        """
        # 验证default_days参数
        if default_days <= 0:
            default_days = 7
        elif default_days > 365:
            default_days = 365
            
        end_date = DateUtils.format_date_for_query(end_date_str) or date.today()
        
        if start_date_str:
            start_date = DateUtils.format_date_for_query(start_date_str)
            if start_date is None:
                # 如果开始日期格式不正确，则使用默认天数
                start_date = end_date - timedelta(days=default_days - 1)
        else:
            start_date = end_date - timedelta(days=default_days - 1)
        
        return start_date, end_date
    
    @staticmethod
    def is_valid_date_range(start_date: date, end_date: date, max_days: int = 365) -> bool:
        """验证日期范围是否有效
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            max_days: 最大允许天数
            
        Returns:
            bool: 日期范围有效返回True，否则返回False
        """
        # 参数类型检查
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            return False
            
        # 验证日期合理性
        if (start_date.year < 1900 or start_date.year > 2100 or 
            end_date.year < 1900 or end_date.year > 2100):
            return False
            
        # 开始日期不能晚于结束日期
        if start_date > end_date:
            return False
        
        # 检查日期间隔是否超过最大限制
        if (end_date - start_date).days > max_days:
            return False
        
        return True
    
    @staticmethod
    def get_settlement_cycle_date() -> date:
        """获取结算周期日期（T+1），即昨天
        
        Returns:
            date: 昨天的日期对象
        """
        return date.today() - timedelta(days=1)
    
    @staticmethod
    def get_last_n_days(n: int, base_date: date = None) -> Tuple[date, date]:
        """获取最近N天的日期范围
        
        Args:
            n: 天数
            base_date: 基准日期，默认为今天
            
        Returns:
            Tuple[date, date]: (开始日期, 结束日期)
        """
        if base_date is None:
            base_date = date.today()
            
        if not isinstance(base_date, date):
            raise TypeError("base_date必须是date类型")
            
        if n <= 0:
            n = 1
        elif n > 365:
            n = 365
            
        end_date = base_date
        start_date = base_date - timedelta(days=n-1)
        return start_date, end_date
    
    @staticmethod
    def is_weekend(target_date: date = None) -> bool:
        """判断指定日期是否为周末
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            bool: 是周末返回True，否则返回False
        """
        if target_date is None:
            target_date = date.today()
            
        if not isinstance(target_date, date):
            raise TypeError("target_date必须是date类型")
            
        # 周一是0，周日是6
        return target_date.weekday() >= 5  # 5=周六, 6=周日
    
    @staticmethod
    def add_business_days(start_date: date, days: int) -> date:
        """添加工作日（排除周末）
        
        Args:
            start_date: 起始日期
            days: 要添加的工作日天数
            
        Returns:
            date: 计算后的日期
        """
        if not isinstance(start_date, date):
            raise TypeError("start_date必须是date类型")
            
        if days == 0:
            return start_date
            
        result_date = start_date
        added_days = 0
        step = 1 if days > 0 else -1
        
        while added_days < abs(days):
            result_date += timedelta(days=step)
            # 如果不是周末，则计数加1
            if result_date.weekday() < 5:  # 0-4是周一到周五
                added_days += 1
                
        return result_date