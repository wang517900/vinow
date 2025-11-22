# 创建获取token的专用脚本
cat > get_auth_token.py << 'EOF'
import requests
import json
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def get_auth_token():
    BASE_URL = 'http://localhost:8000'
    test_phone = "+84123456789"
    
    print("🔐 获取认证令牌流程")
    print("=" * 40)
    
    # 方法1：尝试使用数据库中的验证码
    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
    result = client.table('phone_verifications').select('*').eq('phone', test_phone).order('created_at', desc=True).limit(1).execute()
    
    if result.data:
        stored_otp = result.data[0].get('token')
        print(f"1. 使用存储的验证码: {stored_otp}")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/verify-otp",
            json={"phone": test_phone, "token": stored_otp}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            print(f"✅ 成功获取Token: {access_token[:30]}...")
            return access_token
    
    # 方法2：如果方法1失败，创建测试用户并生成token
    print("2. 方法1失败，创建测试用户...")
    try:
        # 创建测试用户资料
        user_data = {
            "phone": test_phone,
            "full_name": "测试用户",
            "email": "test@example.com"
        }
        result = client.table('user_profiles').upsert(user_data).execute()
        print("✅ 测试用户创建/更新成功")
        
        # 这里应该调用生成token的端点
        # 由于验证码流程有问题，我们可以暂时跳过直接认证
        print("⚠️  由于验证码问题，无法自动获取token")
        print("💡 请手动在Swagger UI中完成认证流程")
        
    except Exception as e:
        print(f"❌ 创建测试用户失败: {e}")
    
    return None

if __name__ == "__main__":
    token = get_auth_token()
    if token:
        print(f"\n🎯 使用以下Token进行测试:")
        print(f"Authorization: Bearer {token}")
    else:
        print("\n❌ 无法获取认证令牌")