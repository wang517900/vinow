# tests/test_merchant_system.py
import asyncio
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def test_health_check():
    """测试健康检查"""
    response = requests.get("http://localhost:8000/health")
    print("健康检查:", response.status_code, response.json())
    return response.status_code == 200

def test_merchant_creation():
    """测试商家创建"""
    # 先获取测试商家ID
    response = requests.get(f"{BASE_URL}/merchants?email=merchant1@test.com")
    if response.status_code == 200 and response.json()['data']:
        merchant_id = response.json()['data'][0]['id']
        print(f"测试商家ID: {merchant_id}")
        return merchant_id
    return None

def test_order_operations(merchant_id):
    """测试订单操作"""
    # 获取订单列表
    response = requests.get(f"{BASE_URL}/orders?merchant_id={merchant_id}&page=1&page_size=10")
    print("订单列表测试:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print(f"获取到 {len(data['data']['orders'])} 个订单")
        return True
    return False

def test_verification_operations(merchant_id):
    """测试核销操作"""
    # 获取待核销订单
    response = requests.get(f"{BASE_URL}/orders?merchant_id={merchant_id}&status=pending&page_size=1")
    
    if response.status_code == 200 and response.json()['data']['orders']:
        order = response.json()['data']['orders'][0]
        
        # 测试核销
        verify_response = requests.post(
            f"{BASE_URL}/verification/code",
            params={
                "verification_code": order['verification_code'],
                "staff_id": "test_staff_001", 
                "staff_name": "测试员工"
            }
        )
        print("核销测试:", verify_response.status_code, verify_response.json())
        return verify_response.status_code == 200
    
    return False

def test_dashboard_operations(merchant_id):
    """测试数据看板"""
    tests = [
        ("订单趋势", f"{BASE_URL}/dashboard/order-trends?merchant_id={merchant_id}&days=7"),
        ("热销商品", f"{BASE_URL}/dashboard/top-products?merchant_id={merchant_id}&limit=5"),
        ("今日统计", f"{BASE_URL}/merchants/{merchant_id}/stats/today"),
    ]
    
    all_passed = True
    for name, url in tests:
        response = requests.get(url)
        status = "通过" if response.status_code == 200 else "失败"
        print(f"{name}: {status}")
        if response.status_code != 200:
            all_passed = False
    
    return all_passed

def run_all_tests():
    """运行所有测试"""
    print("开始运行商家订单管理系统测试...")
    
    if not test_health_check():
        print("健康检查失败，服务可能未启动")
        return False
    
    merchant_id = test_merchant_creation()
    if not merchant_id:
        print("获取商家ID失败")
        return False
    
    tests = [
        ("订单操作", lambda: test_order_operations(merchant_id)),
        ("核销操作", lambda: test_verification_operations(merchant_id)),
        ("数据看板", lambda: test_dashboard_operations(merchant_id)),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{test_name}: {'通过' if result else '失败'}")
        except Exception as e:
            print(f"{test_name}: 异常 - {e}")
            results.append((test_name, False))
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n测试完成: {passed}/{total} 通过")
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)