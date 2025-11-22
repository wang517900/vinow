# tests/test_data.py
import asyncio
from datetime import datetime, timedelta
from app.services.order_service import order_service
from app.models.order import OrderCreate, OrderStatus, PaymentMethod
import random

# 测试数据
TEST_MERCHANT_ID = "merchant_001"
TEST_STORE_ID = "store_001"
TEST_PRODUCTS = [
    "越南春卷套餐",
    "河内牛肉粉", 
    "顺化牛肉米线",
    "烤猪肉米线",
    "越南咖啡",
    "水果沙拉",
    "炸春卷",
    "越南法棍三明治"
]

def generate_phone_number():
    """生成随机手机号"""
    return f"09{random.randint(10000000, 99999999)}"

def generate_order_number():
    """生成订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices('0123456789', k=6))
    return f"ORD{timestamp}{random_str}"

def generate_verification_code():
    """生成核销码"""
    return ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))

async def create_test_orders(count: int = 50):
    """创建测试订单"""
    orders_created = 0
    
    for i in range(count):
        try:
            # 随机生成订单数据
            product_name = random.choice(TEST_PRODUCTS)
            unit_price = random.randint(50000, 200000)
            quantity = random.randint(1, 3)
            total_amount = unit_price * quantity
            discount = random.randint(0, 20000)
            paid_amount = total_amount - discount
            
            # 随机状态分布
            status_weights = [0.4, 0.3, 0.1, 0.1, 0.1]  # 待核销40%，已核销30%，其他30%
            status = random.choices(
                [OrderStatus.PENDING, OrderStatus.VERIFIED, OrderStatus.REFUNDING, OrderStatus.REFUNDED, OrderStatus.COMPLETED],
                weights=status_weights
            )[0]
            
            order_data = OrderCreate(
                order_number=generate_order_number(),
                user_id=f"user_{random.randint(1000, 9999)}",
                user_phone=generate_phone_number(),
                user_name=f"用户{random.randint(1000, 9999)}",
                product_name=product_name,
                product_id=f"product_{random.randint(1, 100)}",
                quantity=quantity,
                unit_price=unit_price,
                total_amount=total_amount,
                discount_amount=discount,
                paid_amount=paid_amount,
                payment_method=random.choice(list(PaymentMethod)),
                status=status,
                verification_code=generate_verification_code(),
                merchant_id=TEST_MERCHANT_ID,
                store_id=TEST_STORE_ID
            )
            
            order = await order_service.create_order(order_data)
            if order:
                orders_created += 1
                print(f"创建订单: {order.order_number} - {order.product_name} - {order.status}")
            
        except Exception as e:
            print(f"创建订单失败: {e}")
    
    print(f"成功创建 {orders_created} 个测试订单")

if __name__ == "__main__":
    asyncio.run(create_test_orders(50))

    商家板块5数据分析
    import json
from datetime import date, datetime, timedelta
from uuid import uuid4
from app.core.logging import logger

def generate_test_data():
    """生成测试数据"""
    
    # 业务指标测试数据
    business_metrics = []
    start_date = date(2024, 1, 8)
    
    for i in range(8):  # 生成8天数据
        current_date = start_date + timedelta(days=i)
        metrics = {
            "id": str(uuid4()),
            "date": current_date.isoformat(),
            "customer_count": 120 + i * 5,
            "revenue": 8000000 + i * 600000,
            "order_count": 75 + i * 2,
            "rating": 4.6 + (i * 0.02),
            "health_score": 82 + i,
            "competitor_count": 8,
            "rating_rank": 2,
            "better_than_peers": 85 + i,
            "morning_revenue": 1000000 + i * 50000,
            "lunch_revenue": 4000000 + i * 300000,
            "afternoon_revenue": 800000 + i * 40000,
            "evening_revenue": 5000000 + i * 250000,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        business_metrics.append(metrics)
    
    # 预警测试数据
    alerts = [
        {
            "id": str(uuid4()),
            "title": "高峰时段等位流失率高",
            "description": "17:00-19:00时段等位流失率45%",
            "level": "critical",
            "is_resolved": False,
            "business_date": date.today().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid4()),
            "title": "招牌菜库存不足",
            "description": "招牌菜'牛肉pho'库存不足",
            "level": "warning",
            "is_resolved": False,
            "business_date": date.today().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid4()),
            "title": "新评价待回复",
            "description": "3条新评价待回复",
            "level": "warning",
            "is_resolved": False,
            "business_date": date.today().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # 收入趋势测试数据
    revenue_trends = []
    for i in range(7):
        trend_date = date.today() - timedelta(days=6-i)
        revenue_trends.extend([
            {
                "id": str(uuid4()),
                "business_date": trend_date.isoformat(),
                "revenue": 1200000,
                "period": "morning",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid4()),
                "business_date": trend_date.isoformat(),
                "revenue": 5800000 + i * 200000,
                "period": "lunch",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid4()),
                "business_date": trend_date.isoformat(),
                "revenue": 900000,
                "period": "afternoon",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid4()),
                "business_date": trend_date.isoformat(),
                "revenue": 6900000 + i * 300000,
                "period": "evening",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ])
    
    # 竞对分析测试数据
    competitor_analysis = [
        {
            "id": str(uuid4()),
            "business_date": date.today().isoformat(),
            "total_competitors": 8,
            "rating_rank": 2,
            "price_level": "medium_high",
            "customer_flow_rank": 3,
            "promotion_intensity": "medium",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # 营销活动测试数据
    marketing_campaigns = [
        {
            "id": str(uuid4()),
            "name": "优惠券活动",
            "start_date": (date.today() - timedelta(days=5)).isoformat(),
            "end_date": date.today().isoformat(),
            "investment": 1200000,
            "revenue_generated": 8500000,
            "new_customers": 45,
            "roi": 608.33,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid4()),
            "name": "达人推广",
            "start_date": (date.today() - timedelta(days=3)).isoformat(),
            "end_date": (date.today() + timedelta(days=2)).isoformat(),
            "investment": 500000,
            "revenue_generated": 3200000,
            "new_customers": 23,
            "roi": 540.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # 评价测试数据
    reviews = []
    keywords_data = []
    
    for i in range(23):
        review_date = date.today() - timedelta(days=i % 3)
        reviews.append({
            "id": str(uuid4()),
            "business_date": review_date.isoformat(),
            "rating": 5 if i < 15 else 4 if i < 20 else 2,
            "comment": f"测试评价 {i+1}",
            "is_responded": i < 20,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    # 关键词频率
    keyword_frequency = [
        {"keyword": "好吃", "frequency": 32},
        {"keyword": "服务好", "frequency": 18},
        {"keyword": "等位久", "frequency": 12},
        {"keyword": "价格合理", "frequency": 10},
        {"keyword": "环境不错", "frequency": 8}
    ]
    
    test_data = {
        "business_metrics": business_metrics,
        "alerts": alerts,
        "revenue_trends": revenue_trends,
        "competitor_analysis": competitor_analysis,
        "marketing_campaigns": marketing_campaigns,
        "reviews": reviews,
        "keyword_frequency": keyword_frequency
    }
    
    # 保存测试数据到文件
    with open("test_data.json", "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)
    
    logger.info("测试数据生成完成")
    return test_data

if __name__ == "__main__":
    generate_test_data()

    商家板块5数据分析测试生成脚本
    import json
from datetime import date, datetime, timedelta
from uuid import uuid4
from app.core.logging import logger

def generate_test_data():
    """生成测试数据"""
    
    # 业务指标测试数据
    business_metrics = []
    start_date = date(2024, 1, 8)
    
    for i in range(8):  # 生成8天数据
        current_date = start_date + timedelta(days=i)
        metrics = {
            "id": str(uuid4()),
            "date": current_date.isoformat(),
            "customer_count": 120 + i * 5,
            "revenue": 8000000 + i * 600000,
            "order_count": 75 + i * 2,
            "rating": 4.6 + (i * 0.02),
            "health_score": 82 + i,
            "competitor_count": 8,
            "rating_rank": 2,
            "better_than_peers": 85 + i,
            "morning_revenue": 1000000 + i * 50000,
            "lunch_revenue": 4000000 + i * 300000,
            "afternoon_revenue": 800000 + i * 40000,
            "evening_revenue": 5000000 + i * 250000,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        business_metrics.append(metrics)
    
    # 预警测试数据
    alerts = [
        {
            "id": str(uuid4()),
            "title": "高峰时段等位流失率高",
            "description": "17:00-19:00时段等位流失率45%",
            "level": "critical",
            "is_resolved": False,
            "business_date": date.today().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid4()),
            "title": "招牌菜库存不足",
            "description": "招牌菜'牛肉pho'库存不足",
            "level": "warning",
            "is_resolved": False,
            "business_date": date.today().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid4()),
            "title": "新评价待回复",
            "description": "3条新评价待回复",
            "level": "warning",
            "is_resolved": False,
            "business_date": date.today().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # 收入趋势测试数据
    revenue_trends = []
    for i in range(7):
        trend_date = date.today() - timedelta(days=6-i)
        revenue_trends.extend([
            {
                "id": str(uuid4()),
                "business_date": trend_date.isoformat(),
                "revenue": 1200000,
                "period": "morning",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid4()),
                "business_date": trend_date.isoformat(),
                "revenue": 5800000 + i * 200000,
                "period": "lunch",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid4()),
                "business_date": trend_date.isoformat(),
                "revenue": 900000,
                "period": "afternoon",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid4()),
                "business_date": trend_date.isoformat(),
                "revenue": 6900000 + i * 300000,
                "period": "evening",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ])
    
    # 竞对分析测试数据
    competitor_analysis = [
        {
            "id": str(uuid4()),
            "business_date": date.today().isoformat(),
            "total_competitors": 8,
            "rating_rank": 2,
            "price_level": "medium_high",
            "customer_flow_rank": 3,
            "promotion_intensity": "medium",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # 营销活动测试数据
    marketing_campaigns = [
        {
            "id": str(uuid4()),
            "name": "优惠券活动",
            "start_date": (date.today() - timedelta(days=5)).isoformat(),
            "end_date": date.today().isoformat(),
            "investment": 1200000,
            "revenue_generated": 8500000,
            "new_customers": 45,
            "roi": 608.33,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid4()),
            "name": "达人推广",
            "start_date": (date.today() - timedelta(days=3)).isoformat(),
            "end_date": (date.today() + timedelta(days=2)).isoformat(),
            "investment": 500000,
            "revenue_generated": 3200000,
            "new_customers": 23,
            "roi": 540.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    
    # 评价测试数据
    reviews = []
    keywords_data = []
    
    for i in range(23):
        review_date = date.today() - timedelta(days=i % 3)
        reviews.append({
            "id": str(uuid4()),
            "business_date": review_date.isoformat(),
            "rating": 5 if i < 15 else 4 if i < 20 else 2,
            "comment": f"测试评价 {i+1}",
            "is_responded": i < 20,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    # 关键词频率
    keyword_frequency = [
        {"keyword": "好吃", "frequency": 32},
        {"keyword": "服务好", "frequency": 18},
        {"keyword": "等位久", "frequency": 12},
        {"keyword": "价格合理", "frequency": 10},
        {"keyword": "环境不错", "frequency": 8}
    ]
    
    test_data = {
        "business_metrics": business_metrics,
        "alerts": alerts,
        "revenue_trends": revenue_trends,
        "competitor_analysis": competitor_analysis,
        "marketing_campaigns": marketing_campaigns,
        "reviews": reviews,
        "keyword_frequency": keyword_frequency
    }
    
    # 保存测试数据到文件
    with open("test_data.json", "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)
    
    logger.info("测试数据生成完成")
    return test_data

if __name__ == "__main__":
    generate_test_data()