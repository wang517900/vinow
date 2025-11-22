商家板块6财务中心
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    CredentialsException, FinanceDataException, 
    SettlementException, ReconciliationException, ReportException
)


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""
    
    logger = logging.getLogger('error_handler')
    
    @app.exception_handler(CredentialsException)
    async def credentials_exception_handler(request: Request, exc: CredentialsException):
        """认证异常处理"""
        logger.warning(f"Authentication failed for {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": "认证失败",
                "error_code": "AUTHENTICATION_FAILED"
            },
            headers=exc.headers
        )
    
    @app.exception_handler(FinanceDataException)
    async def finance_data_exception_handler(request: Request, exc: FinanceDataException):
        """财务数据异常处理"""
        logger.error(f"Finance data error for {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": "FINANCE_DATA_ERROR"
            }
        )
    
    @app.exception_handler(SettlementException)
    async def settlement_exception_handler(request: Request, exc: SettlementException):
        """结算异常处理"""
        logger.error(f"Settlement error for {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": "SETTLEMENT_ERROR"
            }
        )
    
    @app.exception_handler(ReconciliationException)
    async def reconciliation_exception_handler(request: Request, exc: ReconciliationException):
        """对账异常处理"""
        logger.error(f"Reconciliation error for {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": "RECONCILIATION_ERROR"
            }
        )
    
    @app.exception_handler(ReportException)
    async def report_exception_handler(request: Request, exc: ReportException):
        """报表异常处理"""
        logger.error(f"Report error for {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": "REPORT_ERROR"
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """请求验证异常处理"""
        logger.warning(f"Validation error for {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "请求参数验证失败",
                "error_code": "VALIDATION_ERROR",
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """HTTP异常处理"""
        logger.warning(f"HTTP error {exc.status_code} for {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": "HTTP_ERROR"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理"""
        logger.error(f"Unexpected error for {request.url}", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误",
                "error_code": "INTERNAL_SERVER_ERROR"
            }
        )