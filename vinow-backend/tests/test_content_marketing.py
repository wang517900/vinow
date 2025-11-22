# tests/test_content_marketing.py
import asyncio
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def test_content_creation():
    """测试内容创建"""
    # 先获取测试商家ID
    response = requests.get(f"{BASE_URL}/merchants?email=merchant1@test.com")
    if response.status_code == 200 and response.json()['data']:
        merchant_id = response.json()['data'][0]['id']
        
        # 创建测试内容
        content_data = {
            "title": "测试营销视频",
            "description": "这是一个测试营销视频内容",
            "content_type": "video",
            "status": "published",
            "video_url": "https://example.com/test-video.mp4",
            "thumbnail_url": "https://example.com/thumbnail.jpg",
            "product_ids": [],
            "merchant_id": merchant_id
        }
        
        response = requests.post(f"{BASE_URL}/contents", json=content_data)
        print("内容创建测试:", response.status_code, response.json())
        return response.status_code == 200
    
    return False

def test_collaboration_creation():
    """测试合作任务创建"""
    response = requests.get(f"{BASE_URL}/merchants?email=merchant1@test.com")
    if response.status_code == 200 and response.json()['data']:
        merchant_id = response.json()['data'][0]['id']
        
        collaboration_data = {
            "title": "测试合作任务",
            "description": "寻找达人合作推广我们的新产品",
            "requirements": "粉丝数1万以上，有美妆类内容经验",
            "budget_amount": 5000.00,
            "commission_rate": 10.0,
            "content_requirements": "需要制作1分钟以上的视频内容",
            "product_ids": [],
            "merchant_id": merchant_id
        }
        
        response = requests.post(f"{BASE_URL}/collaborations", json=collaboration_data)
        print("合作任务创建测试:", response.status_code, response.json())
        return response.status_code == 200
    
    return False

def test_dashboard():
    """测试数据看板"""
    response = requests.get(f"{BASE_URL}/merchants?email=merchant1@test.com")
    if response.status_code == 200 and response.json()['data']:
        merchant_id = response.json()['data'][0]['id']
        
        dashboard_response = requests.get(f"{BASE_URL}/dashboard?merchant_id={merchant_id}")
        print("数据看板测试:", dashboard_response.status_code, dashboard_response.json())
        return dashboard_response.status_code == 200
    
    return False

def run_content_marketing_tests():
    """运行内容营销系统测试"""
    print("开始运行内容营销系统测试...")
    
    tests = [
        ("内容创建", test_content_creation),
        ("合作任务创建", test_collaboration_creation),
        ("数据看板", test_dashboard),
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
    
    print(f"\n内容营销测试完成: {passed}/{total} 通过")
    return passed == total

if __name__ == "__main__":
    success = run_content_marketing_tests()
    exit(0 if success else 1)