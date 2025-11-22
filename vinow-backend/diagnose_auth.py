# diagnose_auth.py
import jwt
import os
from datetime import datetime, timedelta

def diagnose_auth():
    print("🔍 ========== FastAPI 认证问题诊断 ==========\n")
    
    # 1. 检查环境变量
    print("1. 检查环境变量:")
    jwt_secret = os.getenv("JWT_SECRET")
    if jwt_secret:
        print(f"✅ JWT_SECRET 已设置")
        print(f"   长度: {len(jwt_secret)} 字符")
        print(f"   值: {jwt_secret[:5]}...{jwt_secret[-5:]}")
    else:
        print("❌ JWT_SECRET 未设置!")
        return
    
    # 2. 测试 JWT 功能
    print("\n2. 测试 JWT 功能:")
    try:
        test_payload = {
            "user_id": "fd59de35-df00-49e3-8f59-2f15de38d618",
            "phone": "+841123456789",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        # 生成 token
        token = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
        print(f"✅ Token 生成成功")
        print(f"   Token: {token[:50]}...")
        
        # 验证 token
        decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        print(f"✅ Token 验证成功")
        print(f"   解码内容: {decoded}")
        
    except Exception as e:
        print(f"❌ JWT 测试失败: {e}")
        return
    
    # 3. 检查 PyJWT 版本
    print("\n3. 检查依赖:")
    try:
        import jwt as jwt_module
        print(f"✅ PyJWT 版本: {jwt_module.__version__}")
    except ImportError:
        print("❌ PyJWT 未安装")
        print("💡 运行: pip install PyJWT")
        return
    
    print("\n💡 建议检查:")
    print("   - 认证依赖是否正确应用到 /api/v1/users/profile 路由")
    print("   - JWT_SECRET 在生成和验证时是否一致")
    print("   - Token 过期时间设置")
    
    print("\n====================================\n")

if __name__ == "__main__":
    diagnose_auth()