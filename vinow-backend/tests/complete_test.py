# tests/complete_test.py
import asyncio
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def test_health_check():
    """测试健康检查"""
    response = requests.get("http://localhost:8000/health")
    print("健康检查:", response.status_code, response.json())

def test_create_test_orders():
    """创建测试订单"""
    from tests.test_data import create_test_orders
    asyncio.run(create_test_orders(20))
    print("测试订单创建完成")

def test_list_orders():
    """测试获取订单列表"""
    response = requests.get(f"{BASE_URL}/orders?merchant_id=merchant_001&page=1&page_size=10")
    print("订单列表:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print(f"获取到 {len(data['data']['orders'])} 个订单")

def test_get_order_stats():
    """测试获取订单统计"""
    response = requests.get(f"{BASE_URL}/merchants/merchant_001/stats/today")
    print("今日统计:", response.status_code, response.json())

def test_verification():
    """测试核销功能"""
    # 先获取一个待核销订单
    response = requests.get(f"{BASE_URL}/orders?merchant_id=merchant_001&status=pending&page_size=1")
    if response.status_code == 200:
        orders = response.json()['data']['orders']
        if orders:
            order = orders[0]
            # 测试核销
            verify_response = requests.post(
                f"{BASE_URL}/verification/code?verification_code={order['verification_code']}&staff_id=staff_001&staff_name=测试员工"
            )
            print("核销测试:", verify_response.status_code, verify_response.json())

def test_refund():
    """测试退款功能"""
    # 获取一个已核销订单进行退款测试
    response = requests.get(f"{BASE_URL}/orders?merchant_id=merchant_001&status=verified&page_size=1")
    if response.status_code == 200:
        orders = response.json()['data']['orders']
        if orders:
            order = orders[0]
            # 申请退款
            refund_data = {
                "order_id": order['id'],
                "reason": "商品质量问题",
                "explanation": "商品存在明显瑕疵"
            }
            refund_response = requests.post(f"{BASE_URL}/refunds/request", json=refund_data)
            print("退款申请:", refund_response.status_code, refund_response.json())

def test_dashboard():
    """测试数据看板"""
    responses = []
    
    # 测试订单趋势
    trend_response = requests.get(f"{BASE_URL}/dashboard/order-trends?merchant_id=merchant_001&days=7")
    responses.append(("订单趋势", trend_response.status_code))
    
    # 测试热销商品
    products_response = requests.get(f"{BASE_URL}/dashboard/top-products?merchant_id=merchant_001&limit=5")
    responses.append(("热销商品", products_response.status_code))
    
    # 测试日报表
    report_response = requests.get(f"{BASE_URL}/dashboard/daily-report?merchant_id=merchant_001")
    responses.append(("日报表", report_response.status_code))
    
    for name, status in responses:
        print(f"{name}: {status}")

def run_all_tests():
    """运行所有测试"""
    print("开始运行商家订单管理系统测试...")
    
    test_health_check()
    test_create_test_orders()
    test_list_orders()
    test_get_order_stats()
    test_verification()
    test_refund()
    test_dashboard()
    
    print("\n所有测试完成!")

if __name__ == "__main__":
    run_all_tests()