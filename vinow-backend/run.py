内容系统
#!/usr/bin/env python3
"""
视频内容系统 - 启动脚本
这个脚本用于启动FastAPI应用
"""

import uvicorn
from app.config import settings
from app.utils.logger import logger

def main():
    """主启动函数"""
    try:
        logger.info("🎬 启动视频内容系统...")
        
        # 配置uvicorn服务器
        config = uvicorn.Config(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True,
            workers=1 if settings.debug else 4,  # 生产环境使用多个worker
        )
        
        server = uvicorn.Server(config)
        
        logger.info(f"📍 服务器地址: http://{settings.host}:{settings.port}")
        logger.info(f"📚 API文档: http://{settings.host}:{settings.port}/docs")
        logger.info(f"🔧 调试模式: {'开启' if settings.debug else '关闭'}")
        logger.info(f"📊 日志级别: {settings.log_level}")
        
        # 启动服务器
        server.run()
        
    except KeyboardInterrupt:
        logger.info("👋 收到中断信号，优雅关闭服务器...")
    except Exception as e:
        logger.error(f"💥 启动失败: {str(e)}")
        raise

if __name__ == "__main__":
    main()