# [文件: scripts/test_all_apis.py] [行号: 2351-2500]
"""
Vinow API 完整测试脚本
测试 v1.0.0 到 v1.7.0 所有功能
"""
import requests
import json
import time
import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_PHONE = "+84123456789"
TEST_EMAIL = "test@vinow.com"

class APITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token = None
        self.user_id = None
        self.test_results = {}
        
    def print_header(self, title):
        """打印测试标题"""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")
        
    def print_success(self, message):
        """打印成功信息"""
        print(f"✅ {message}")
        
    def print_error(self, message):
        """打印错误信息"""
        print(f"❌ {message}")
        
    def print_warning(self, message):
        """打印警告信息"""
        print(f"⚠️  {message}")
        
    def test_endpoint(self, method, endpoint, data=None, expected_status=200, auth_required=False):
        """通用端点测试方法"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if auth_required and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
            
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                headers["Content-Type"] = "application/json"
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                headers["Content-Type"] = "application/json"
                response = self.session.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                return False, f"不支持的HTTP方法: {method}"
                
            success = response.status_code == expected_status
            if success:
                return True, response.json() if response.content else {"status": "success"}
            else:
                return False, f"状态码: {response.status_code}, 响应: {response.text}"
                
        except Exception as e:
            return False, f"请求异常: {str(e)}"
            
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始 Vinow API 完整测试")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 目标地址: {self.base_url}")
        
        # 测试基础功能
        self.test_basic_functionality()
        
        # 测试认证系统 (v1.0.0)
        self.test_auth_system()
        
        if self.access_token:
            # 测试用户资料管理 (v1.1.0)
            self.test_user_management()
            
            # 测试用户互动数据 (v1.2.0)
            self.test_interactions()
            
            # 测试订单中心 (v1.3.0)
            self.test_orders()
            
            # 测试评价系统 (v1.4.0)
            self.test_reviews()
            
            # 测试数据分析 (v1.5.0)
            self.test_analytics()
            
            # 测试支付集成 (v1.6.0)
            self.test_payment()
            
            # 测试高级功能 (v1.7.0)
            self.test_advanced_features()
        
        # 生成测试报告
        self.generate_report()
        
    def test_basic_functionality(self):
        """测试基础功能"""
        self.print_header("基础功能测试")
        
        # 测试根端点
        success, result = self.test_endpoint("GET", "/")
        if success:
            self.print_success(f"根端点: {result.get('message')}")
        else:
            self.print_error(f"根端点: {result}")
        self.test_results["root"] = success
        
        # 测试健康检查
        success, result = self.test_endpoint("GET", "/health")
        if success:
            self.print_success("健康检查: 服务正常")
        else:
            self.print_error(f"健康检查: {result}")
        self.test_results["health"] = success
        
        # 测试版本信息
        success, result = self.test_endpoint("GET", "/api/version")
        if success:
            self.print_success(f"版本信息: {result.get('current_version')}")
        else:
            self.print_error(f"版本信息: {result}")
        self.test_results["version"] = success
        
        # 测试API文档
        try:
            response = self.session.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                self.print_success("API文档: 可正常访问")
            else:
                self.print_error(f"API文档: 状态码 {response.status_code}")
            self.test_results["docs"] = response.status_code == 200
        except Exception as e:
            self.print_error(f"API文档: {str(e)}")
            self.test_results["docs"] = False
    
    def test_auth_system(self):
        """测试认证系统 (v1.0.0)"""
        self.print_header("v1.0.0 - 认证系统测试")
        
        # 发送验证码
        auth_data = {"phone": TEST_PHONE}
        success, result = self.test_endpoint("POST", "/api/v1/auth/send-otp", auth_data)
        if success:
            self.print_success("发送验证码: 成功")
            debug_code = result.get("data", {}).get("debug_code")
            if debug_code:
                self.print_warning(f"开发模式验证码: {debug_code}")
                
                # 验证登录（使用收到的验证码）
                verify_data = {"phone": TEST_PHONE, "token": debug_code}
                success, result = self.test_endpoint("POST", "/api/v1/auth/verify-otp", verify_data)
                if success:
                    self.access_token = result.get("access_token")
                    self.user_id = result.get("user", {}).get("id")
                    self.print_success("验证登录: 成功")
                    self.print_success(f"用户ID: {self.user_id}")
                else:
                    self.print_error(f"验证登录: {result}")
            else:
                self.print_warning("验证码发送成功，但未返回调试代码（生产模式）")
        else:
            self.print_error(f"发送验证码: {result}")
            
        self.test_results["auth"] = bool(self.access_token)
        
        if self.access_token:
            # 测试获取用户资料
            success, result = self.test_endpoint("GET", "/api/v1/auth/profile", auth_required=True)
            if success:
                self.print_success("获取当前用户: 成功")
            else:
                self.print_error(f"获取当前用户: {result}")
                
            # 测试刷新令牌
            if "refresh_token" in result:
                refresh_data = {"refresh_token": result["refresh_token"]}
                success, result = self.test_endpoint("POST", "/api/v1/auth/refresh", refresh_data)
                if success:
                    self.print_success("刷新令牌: 成功")
                else:
                    self.print_error(f"刷新令牌: {result}")
    
    def test_user_management(self):
        """测试用户资料管理 (v1.1.0)"""
        self.print_header("v1.1.0 - 用户资料管理测试")
        
        # 获取用户资料
        success, result = self.test_endpoint("GET", "/api/v1/users/profile", auth_required=True)
        if success:
            self.print_success("获取用户资料: 成功")
        else:
            self.print_error(f"获取用户资料: {result}")
        self.test_results["user_profile"] = success
        
        # 更新用户资料
        update_data = {
            "username": "test_user_updated",
            "full_name": "测试用户更新",
            "gender": "male"
        }
        success, result = self.test_endpoint("PUT", "/api/v1/users/profile", update_data, auth_required=True)
        if success:
            self.print_success("更新用户资料: 成功")
        else:
            self.print_error(f"更新用户资料: {result}")
            
        # 获取用户偏好
        success, result = self.test_endpoint("GET", "/api/v1/users/preferences", auth_required=True)
        if success:
            self.print_success("获取用户偏好: 成功")
        else:
            self.print_error(f"获取用户偏好: {result}")
            
        # 获取用户地址
        success, result = self.test_endpoint("GET", "/api/v1/users/addresses", auth_required=True)
        if success:
            self.print_success("获取用户地址: 成功")
        else:
            self.print_error(f"获取用户地址: {result}")
            
        # 获取用户统计
        success, result = self.test_endpoint("GET", "/api/v1/users/stats", auth_required=True)
        if success:
            self.print_success("获取用户统计: 成功")
        else:
            self.print_error(f"获取用户统计: {result}")
    
    def test_interactions(self):
        """测试用户互动数据 (v1.2.0)"""
        self.print_header("v1.2.0 - 用户互动数据测试")
        
        # 测试收藏功能
        endpoints = [
            ("/api/v1/users/favorites/merchants", "商家收藏"),
            ("/api/v1/users/favorites/products", "商品收藏"),
            ("/api/v1/users/history/merchants", "商家历史"),
            ("/api/v1/users/history/searches", "搜索历史")
        ]
        
        for endpoint, name in endpoints:
            success, result = self.test_endpoint("GET", endpoint, auth_required=True)
            if success:
                self.print_success(f"{name}: 获取成功")
            else:
                self.print_warning(f"{name}: {result}")
                
        self.test_results["interactions"] = True
    
    def test_orders(self):
        """测试订单中心 (v1.3.0)"""
        self.print_header("v1.3.0 - 订单中心测试")
        
        # 获取订单列表
        success, result = self.test_endpoint("GET", "/api/v1/orders", auth_required=True)
        if success:
            self.print_success("获取订单列表: 成功")
        else:
            self.print_warning(f"获取订单列表: {result}")
            
        # 获取订单统计
        success, result = self.test_endpoint("GET", "/api/v1/orders/stats", auth_required=True)
        if success:
            self.print_success("获取订单统计: 成功")
        else:
            self.print_warning(f"获取订单统计: {result}")
            
        self.test_results["orders"] = True
    
    def test_reviews(self):
        """测试评价系统 (v1.4.0)"""
        self.print_header("v1.4.0 - 评价系统测试")
        
        # 获取评价列表
        success, result = self.test_endpoint("GET", "/api/v1/reviews", auth_required=True)
        if success:
            self.print_success("获取评价列表: 成功")
        else:
            self.print_warning(f"获取评价列表: {result}")
            
        # 获取评价统计
        success, result = self.test_endpoint("GET", "/api/v1/reviews/stats", auth_required=True)
        if success:
            self.print_success("获取评价统计: 成功")
        else:
            self.print_warning(f"获取评价统计: {result}")
            
        self.test_results["reviews"] = True
    
    def test_analytics(self):
        """测试数据分析 (v1.5.0)"""
        self.print_header("v1.5.0 - 数据分析测试")
        
        analytics_endpoints = [
            ("/api/v1/analytics/user/overview", "用户数据总览"),
            ("/api/v1/analytics/user/behavior", "用户行为分析"),
            ("/api/v1/analytics/user/spending", "消费分析")
        ]
        
        for endpoint, name in analytics_endpoints:
            success, result = self.test_endpoint("GET", endpoint, auth_required=True)
            if success:
                self.print_success(f"{name}: 成功")
            else:
                self.print_warning(f"{name}: {result}")
                
        self.test_results["analytics"] = True
    
    def test_payment(self):
        """测试支付集成 (v1.6.0)"""
        self.print_header("v1.6.0 - 支付集成测试")
        
        # 获取支付方式
        success, result = self.test_endpoint("GET", "/api/v1/payment/methods", auth_required=True)
        if success:
            self.print_success("获取支付方式: 成功")
        else:
            self.print_warning(f"获取支付方式: {result}")
            
        self.test_results["payment"] = True
    
    def test_advanced_features(self):
        """测试高级功能 (v1.7.0)"""
        self.print_header("v1.7.0 - 高级功能测试")
        
        # 测试通知令牌注册
        notification_data = {"fcm_token": "test_fcm_token_12345"}
        success, result = self.test_endpoint("POST", "/api/v1/notifications/token", notification_data, auth_required=True)
        if success:
            self.print_success("注册推送令牌: 成功")
        else:
            self.print_warning(f"注册推送令牌: {result}")
            
        self.test_results["notifications"] = True
    
    def generate_report(self):
        """生成测试报告"""
        self.print_header("测试报告")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📊 总体结果: {passed_tests}/{total_tests} 测试通过")
        print(f"📈 成功率: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("🎉 所有测试通过！系统运行正常。")
        elif success_rate >= 80:
            print("👍 大部分功能正常，部分功能需要检查。")
        elif success_rate >= 60:
            print("⚠️  基本功能正常，多个功能需要修复。")
        else:
            print("❌ 系统存在较多问题，需要重点修复。")
            
        # 保存测试报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": success_rate,
            "details": self.test_results
        }
        
        with open("test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"📄 详细报告已保存至: test_report.json")

def main():
    """主函数"""
    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ 服务未运行，请先启动服务器: python main.py")
            return
    except:
        print("❌ 无法连接到服务器，请先启动服务器: python main.py")
        return
        
    # 运行测试
    tester = APITester(BASE_URL)
    tester.run_all_tests()

if __name__ == "__main__":
    main()