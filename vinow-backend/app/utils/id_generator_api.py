交易系统

import time
import random
import string
import threading
from typing import Optional
from datetime import datetime

class IdGenerator:
    """
    ID生成器类
    
    提供各种业务场景下的唯一ID生成功能，包括订单号、支付号等
    采用时间戳+随机数的方式保证全局唯一性
    """
    
    # 线程锁，保证并发安全
    _lock = threading.Lock()
    
    # 记录上次生成的时间戳，防止同一毫秒内生成相同ID
    _last_timestamp = 0
    
    # 同一毫秒内的序列号
    _sequence = 0
    
    @classmethod
    def _generate_base_id(cls, prefix: str, random_length: int = 6, timestamp_digits: Optional[int] = None) -> str:
        """
        生成基础ID的核心方法
        
        Args:
            prefix (str): ID前缀
            random_length (int): 随机字符串长度，默认为6位
            timestamp_digits (Optional[int]): 时间戳保留位数，None表示完整时间戳
            
        Returns:
            str: 生成的唯一ID
        """
        with cls._lock:
            # 获取当前时间戳（毫秒）
            timestamp = int(time.time() * 1000)
            
            # 如果在同一毫秒内，增加序列号
            if timestamp == cls._last_timestamp:
                cls._sequence = (cls._sequence + 1) % (10 ** random_length)
                # 如果序列号已达到最大值，则等待下一毫秒
                if cls._sequence == 0:
                    while timestamp <= cls._last_timestamp:
                        timestamp = int(time.time() * 1000)
            else:
                cls._sequence = 0
                
            cls._last_timestamp = timestamp
            
            # 处理时间戳位数
            if timestamp_digits:
                # 取时间戳的后N位
                timestamp_str = str(timestamp)[-timestamp_digits:]
            else:
                timestamp_str = str(timestamp)
            
            # 生成随机字符串
            if cls._sequence > 0:
                # 使用序列号替代部分随机数
                sequence_str = str(cls._sequence).zfill(random_length)
                random_str = sequence_str
            else:
                # 生成随机字符串
                random_str = ''.join(random.choices(string.digits, k=random_length))
            
            return f"{prefix}{timestamp_str}{random_str}"
    
    @classmethod
    def generate_order_number(cls) -> str:
        """
        生成订单号
        
        格式: ORD + 时间戳 + 6位随机数字
        示例: ORD1701234567890123456
        
        Returns:
            str: 订单号
            
        Example:
            >>> order_no = IdGenerator.generate_order_number()
            >>> order_no.startswith('ORD')
            True
            >>> len(order_no) > 3
            True
        """
        return cls._generate_base_id("ORD")
    
    @classmethod
    def generate_payment_number(cls) -> str:
        """
        生成支付流水号
        
        格式: PAY + 时间戳 + 6位随机数字
        示例: PAY1701234567890123456
        
        Returns:
            str: 支付流水号
            
        Example:
            >>> payment_no = IdGenerator.generate_payment_number()
            >>> payment_no.startswith('PAY')
            True
        """
        return cls._generate_base_id("PAY")
    
    @classmethod
    def generate_refund_number(cls) -> str:
        """
        生成退款单号
        
        格式: REF + 时间戳 + 6位随机数字
        示例: REF1701234567890123456
        
        Returns:
            str: 退款单号
            
        Example:
            >>> refund_no = IdGenerator.generate_refund_number()
            >>> refund_no.startswith('REF')
            True
        """
        return cls._generate_base_id("REF")
    
    @classmethod
    def generate_settlement_number(cls) -> str:
        """
        生成结算单号
        
        格式: SET + 时间戳 + 6位随机数字
        示例: SET1701234567890123456
        
        Returns:
            str: 结算单号
            
        Example:
            >>> settlement_no = IdGenerator.generate_settlement_number()
            >>> settlement_no.startswith('SET')
            True
        """
        return cls._generate_base_id("SET")
    
    @classmethod
    def generate_custom_id(cls, prefix: str, length: int = 6, timestamp_digits: Optional[int] = None) -> str:
        """
        生成自定义格式的ID
        
        Args:
            prefix (str): 自定义前缀
            length (int): 随机字符串长度，默认为6
            timestamp_digits (Optional[int]): 时间戳位数，None表示完整时间戳
            
        Returns:
            str: 自定义格式的ID
            
        Example:
            >>> custom_id = IdGenerator.generate_custom_id('CUS', 8)
            >>> custom_id.startswith('CUS')
            True
        """
        if not prefix:
            raise ValueError("Prefix cannot be empty")
        return cls._generate_base_id(prefix, length, timestamp_digits)
    
    @staticmethod
    def generate_uuid_like_id(prefix: str = "") -> str:
        """
        生成类似UUID的ID（不使用UUID库）
        
        Args:
            prefix (str): 可选前缀
            
        Returns:
            str: UUID-like ID
            
        Example:
            >>> uuid_like = IdGenerator.generate_uuid_like_id('TXN')
            >>> len(uuid_like) > 4
            True
        """
        # 生成基于时间的部分
        timestamp = hex(int(time.time() * 1000000))[2:]  # 微秒时间戳的十六进制
        
        # 生成随机部分
        random_part1 = ''.join(random.choices(string.hexdigits.lower(), k=8))
        random_part2 = ''.join(random.choices(string.hexdigits.lower(), k=4))
        random_part3 = ''.join(random.choices(string.hexdigits.lower(), k=4))
        random_part4 = ''.join(random.choices(string.hexdigits.lower(), k=12))
        
        uuid_like = f"{timestamp}-{random_part1}-{random_part2}-{random_part3}-{random_part4}"
        
        if prefix:
            return f"{prefix}_{uuid_like}"
        return uuid_like

# 兼容旧版本的函数接口（如果需要）
def generate_order_number() -> str:
    """兼容函数：生成订单号"""
    return IdGenerator.generate_order_number()

def generate_payment_number() -> str:
    """兼容函数：生成支付流水号"""
    return IdGenerator.generate_payment_number()

def generate_refund_number() -> str:
    """兼容函数：生成退款单号"""
    return IdGenerator.generate_refund_number()

def generate_settlement_number() -> str:
    """兼容函数：生成结算单号"""
    return IdGenerator.generate_settlement_number()