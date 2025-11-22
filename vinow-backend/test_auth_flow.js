// test_auth_flow.js - 完整认证流程测试
const jwt = require('jsonwebtoken');

console.log('🚀 ========== 完整认证流程测试 ==========\n');

function simulateAuthFlow() {
  const JWT_SECRET = process.env.JWT_SECRET;
  
  if (!JWT_SECRET) {
    console.log('❌ 无法测试: JWT_SECRET 未设置');
    return;
  }

  // 模拟用户数据（从您的日志中获取）
  const userData = {
    userId: 'fd59de35-df00-49e3-8f59-2f15le38d618',
    phone: '+841123456789'
  };

  console.log('1. 📱 模拟OTP验证成功');
  console.log('   用户:', userData);

  console.log('\n2. 🔑 生成访问令牌');
  const token = jwt.sign(userData, JWT_SECRET, { expiresIn: '24h' });
  console.log('   ✅ Token生成成功');
  console.log(`   📏 Token: Bearer ${token.substring(0, 50)}...`);

  console.log('\n3. 🔍 模拟前端请求头');
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
  console.log('   📨 请求头:', headers);

  console.log('\n4. ✅ 模拟后端验证');
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    console.log('   ✅ Token验证成功');
    console.log('   👤 用户信息:', decoded);
    
    console.log('\n🎉 认证流程测试完成: 所有步骤成功!');
    console.log('\n💡 如果实际请求仍然失败，请检查:');
    console.log('   - 前端是否正确设置Authorization头');
    console.log('   - 是否有CORS问题');
    console.log('   - 网络请求是否被拦截');
    console.log('   - 服务器日志中的具体错误信息');
    
  } catch (error) {
    console.log('❌ Token验证失败:', error.message);
  }
}

simulateAuthFlow();
console.log('\n========================================\n');