商家板块5数据分析"""商家系统 - formatters"""
from typing import List, Dict, Any
from datetime import date, datetime
from app.core.logging import logger

def format_currency(amount: float, currency: str = "VND") -> str:
    """格式化货币金额"""
    try:
        if currency == "VND":
            if amount >= 1000000:
                return f"{amount/1000000:.1f}M VND"
            elif amount >= 1000:
                return f"{amount/1000:.1f}K VND"
            else:
                return f"{amount:.0f} VND"
        else:
            return f"{amount:.2f} {currency}"
    except Exception as e:
        logger.error(f"Currency formatting error: {str(e)}")
        return f"{amount} {currency}"

def format_percentage(value: float) -> str:
    """格式化百分比"""
    try:
        return f"{value:+.1f}%"
    except Exception as e:
        logger.error(f"Percentage formatting error: {str(e)}")
        return f"{value}%"

def format_trend_visualization(value: float, max_value: float, width: int = 10) -> str:
    """格式化趋势可视化"""
    try:
        if max_value <= 0:
            return "█" * width
        
        ratio = value / max_value
        bars = int(ratio * width)
        return "█" * bars
    except Exception as e:
        logger.error(f"Trend visualization formatting error: {str(e)}")
        return "█" * width

def generate_health_score_emoji(score: int) -> str:
    """生成健康分数表情"""
    if score >= 90:
        return "💎"
    elif score >= 80:
        return "🟢"
    elif score >= 70:
        return "🟡"
    elif score >= 60:
        return "🟠"
    else:
        return "🔴"

def generate_alert_emoji(level: str) -> str:
    """生成预警级别表情"""
    level_map = {
        "critical": "🔴",
        "warning": "🟡", 
        "normal": "🟢"
    }
    return level_map.get(level, "⚪")

def format_dashboard_text(data: Dict[str, Any]) -> Dict[str, Any]:
    """格式化仪表盘文本输出"""
    try:
        formatted = {}
        
        # 格式化健康分数
        health_score = data.get('health_score', {})
        formatted['health_score'] = {
            'score': f"{generate_health_score_emoji(health_score.get('score', 0))} 今日健康分：{health_score.get('score', 0)}分",
            'level': health_score.get('level', 'good'),
            'better_than_peers': f"优于周边{health_score.get('better_than_peers', 0)}%的同行"
        }
        
        # 格式化核心指标
        core_metrics = data.get('core_metrics', {}).get('metrics', [])
        formatted_metrics = []
        for metric in core_metrics:
            change_arrow = "↑" if metric.get('change_direction') == 'up' else "↓" if metric.get('change_direction') == 'down' else "→"
            formatted_metrics.append(
                f"{metric['name']}：{metric['value']} {change_arrow}{metric.get('change_percentage', 0):.0f}%"
            )
        formatted['core_metrics'] = formatted_metrics
        
        # 格式化预警
        alerts = data.get('alerts', {})
        formatted['alerts'] = {
            'critical': alerts.get('critical', 0),
            'warning': alerts.get('warning', 0),
            'normal': alerts.get('normal', 0)
        }
        
        return formatted
    except Exception as e:
        logger.error(f"Dashboard text formatting error: {str(e)}")
        return data
# TODO: 实现商家系统相关功能
