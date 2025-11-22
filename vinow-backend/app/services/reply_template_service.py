商家系统7评价管理（智能回复模版服务）
"""
回复模板相关业务服务类

本模块提供了评价回复模板的相关业务逻辑处理，包括：
- 根据评分获取推荐回复模板
- 获取商家常用回复模板
- 保存商家自定义回复模板
"""

from typing import List, Dict, Any
from app.database import supabase

class ReplyTemplateService:
    """
    回复模板业务服务类
    
    负责处理回复模板相关的业务逻辑，包括默认模板管理、自定义模板等
    """
    
    # 默认回复模板配置
    DEFAULT_TEMPLATES = {
        # 正面评价回复模板（4-5星）
        "positive": [
            {"id": "positive_1", "content": "感谢您的认可！期待再次光临～", "type": "thank"},
            {"id": "positive_2", "content": "谢谢喜欢！我们会继续努力💪", "type": "thank"},
            {"id": "positive_3", "content": "很高兴您喜欢我们的服务，欢迎下次再来！", "type": "official"}
        ],
        # 中性评价回复模板（3星）
        "neutral": [
            {"id": "neutral_1", "content": "感谢反馈，我们会改进的", "type": "official"},
            {"id": "neutral_2", "content": "抱歉让您失望了，我们会优化", "type": "official"},
            {"id": "neutral_3", "content": "谢谢您的建议，我们会认真考虑", "type": "official"}
        ],
        # 负面评价回复模板（1-2星）
        "negative": [
            {"id": "negative_1", "content": "非常抱歉！请联系我们补救：XXXXX", "type": "official"},
            {"id": "negative_2", "content": "对不起给您不好的体验，已内部整改", "type": "official"},
            {"id": "negative_3", "content": "抱歉未能达到您的期望，我们会改进", "type": "official"}
        ]
    }

    async def get_templates_by_rating(self, rating: int) -> List[Dict[str, Any]]:
        """
        根据评分获取推荐回复模板
        
        根据用户给出的评分自动推荐合适的回复模板：
        - 4-5星：正面评价模板
        - 3星：中性评价模板
        - 1-2星：负面评价模板
        
        Args:
            rating (int): 用户评分（1-5星）
            
        Returns:
            List[Dict[str, Any]]: 推荐的回复模板列表
        """
        # 根据评分返回相应的模板列表
        if rating >= 4:
            # 4-5星使用正面评价模板
            return self.DEFAULT_TEMPLATES["positive"]
        elif rating == 3:
            # 3星使用中性评价模板
            return self.DEFAULT_TEMPLATES["neutral"]
        else:
            # 1-2星使用负面评价模板
            return self.DEFAULT_TEMPLATES["negative"]

    async def get_frequently_used(self, merchant_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取商家常用回复模板
        
        根据商家的历史回复数据，分析并返回最常用的回复模板
        （当前为简化版本，实际应用中应基于真实数据分析）
        
        Args:
            merchant_id (int): 商户ID
            limit (int): 返回模板数量限制，默认为5个
            
        Returns:
            List[Dict[str, Any]]: 常用回复模板列表
        """
        # TODO: 实际应用中应该查询商家历史回复数据，分析使用频率并返回最常用的回复
        # 简化版本：返回预设的常用回复模板
        return [
            {"id": "frequent_1", "content": "感谢您的评价！", "type": "official"},
            {"id": "frequent_2", "content": "谢谢光临，欢迎下次再来！", "type": "thank"},
            {"id": "frequent_3", "content": "我们会继续努力提供更好的服务", "type": "official"}
        ][:limit]

    async def save_custom_template(self, merchant_id: int, template_data: Dict[str, Any]) -> bool:
        """
        保存商家自定义回复模板
        
        将商家创建的自定义回复模板保存到数据库中
        
        Args:
            merchant_id (int): 商户ID
            template_data (Dict[str, Any]): 自定义模板数据（包含content和type等字段）
            
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            # 为模板数据添加商户ID关联信息
            template_data["merchant_id"] = merchant_id
            
            # 执行数据库插入操作
            result = supabase.table("reply_templates").insert(template_data).execute()
            
            # 根据插入结果判断是否成功
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            # 记录错误日志
            print(f"保存自定义模板失败: {e}")
            return False