# -*- coding: utf-8 -*-
# tests/test_merchant.py
"""
商家服务测试模块
包含对MerchantService各个方法的单元测试
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

# 导入被测试的服务和模型
from app.services.merchant_service import MerchantService
from app.models.merchant_models import (
    MerchantCreate, MerchantUpdate, ReviewCreate, MerchantSearchParams,
    BusinessCategory
)


# helper Response 类模拟 supabase.execute() 返回对象
def make_response(data=None, error=None, count=None):
    """
    创建模拟响应对象的辅助函数
    用于模拟 Supabase 的 execute() 方法返回值
    """
    class Response:
        def __init__(self, data, error, count):
            self.data = data
            self.error = error
            self.count = count
    return Response(data=data, error=error, count=count)


# Fixture：返回 service 和 mock supabase
@pytest.fixture
def mock_service():
    """
    Pytest fixture，用于创建模拟的 MerchantService 和 Supabase 客户端
    """
    mock_supabase = MagicMock()
    service = MerchantService(mock_supabase)
    return service, mock_supabase


# ------------------------------
# create_merchant - 成功 & 失败
# ------------------------------
def test_create_merchant_success(mock_service):
    """
    测试成功创建商家的情况
    """
    service, mock_supabase = mock_service

    # 模拟检查商家名称是否已存在，返回空数据表示名称可用
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response(data=None, error=None)

    # 准备插入后返回的数据
    inserted = {
        "id": "uuid-1",
        "name": "A Shop",
        "description": "desc",
        "category": BusinessCategory.CAFE.value,
        "address": "Addr",
        "latitude": 10.0,
        "longitude": 106.0,
        "phone": "0912345678",
        "email": "a@b.com",
        "website": None,
        "logo_url": None,
        "banner_url": None,
        "status": "pending",
        "owner_id": "owner-1",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # 模拟插入操作的返回结果
    mock_supabase.table.return_value.insert.return_value.execute.return_value = make_response(data=[inserted], error=None)

    # 构造 MerchantCreate 数据模型
    mc = MerchantCreate(
        name="A Shop",
        description="desc",
        category=BusinessCategory.CAFE,
        address="Addr",
        district=None,
        province=None,
        ward=None,
        latitude=10.0,
        longitude=106.0,
        phone="0912345678",
        email="a@b.com",
        website=None,
        logo_url=None,
        banner_url=None
    )

    # 调用被测试的方法
    resp = service.create_merchant(mc, owner_id="owner-1")
    
    # 验证返回结果
    assert resp.id == "uuid-1"
    assert resp.name == "A Shop"
    assert resp.owner_id == "owner-1"


def test_create_merchant_name_exists(mock_service):
    """
    测试商家名称已存在的情况
    """
    service, mock_supabase = mock_service

    # 模拟检查发现同名商家已存在
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response(data=[{"id": "ex-1"}], error=None)

    # 准备创建商家的数据
    mc = MerchantCreate(
        name="Exists",
        description=None,
        category=BusinessCategory.CAFE,
        address="A",
        district=None,
        province=None,
        ward=None,
        latitude=None,
        longitude=None,
        phone="0912345678",
        email=None,
        website=None,
        logo_url=None,
        banner_url=None
    )

    # 验证会抛出 ValueError 异常
    with pytest.raises(ValueError):
        service.create_merchant(mc, owner_id="owner-1")


# ------------------------------
# get_merchant - 成功 / 未找到
# ------------------------------
def test_get_merchant_success(mock_service):
    """
    测试成功获取商家信息的情况
    """
    service, mock_supabase = mock_service

    # 准备返回的商家数据
    row = {
        "id": "m-5",
        "name": "Coffee Store",
        "description": None,
        "category": BusinessCategory.RESTAURANT.value,
        "address": "some addr",
        "phone": "0912345678",
        "status": "active",
        "owner_id": "owner-5",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # 模拟查询单个商家的返回结果
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_response(data=row, error=None)

    # 调用被测试的方法
    resp = service.get_merchant("m-5")
    
    # 验证返回结果
    assert resp.id == "m-5"
    assert resp.name == "Coffee Store"


def test_get_merchant_not_found(mock_service):
    """
    测试商家未找到的情况
    """
    service, mock_supabase = mock_service

    # 模拟查询结果为空
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_response(data=None, error=None)

    # 调用被测试的方法
    resp = service.get_merchant("no-id")
    
    # 验证返回 None
    assert resp is None


# ------------------------------
# update_merchant - 成功 / 权限或未找到
# ------------------------------
def test_update_merchant_success(mock_service):
    """
    测试成功更新商家信息的情况
    """
    service, mock_supabase = mock_service

    # 模拟验证商家所有权成功
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_response(data={"id": "m3", "owner_id": "owner-3", "status": "active"}, error=None)

    # 准备更新后的商家数据
    updated_row = {
        "id": "m3",
        "name": "Updated Name",
        "category": BusinessCategory.CAFE.value,
        "address": "addr",
        "phone": "0912345678",
        "status": "active",
        "owner_id": "owner-3",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # 模拟更新操作的返回结果
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = make_response(data=[updated_row], error=None)

    # 准备更新数据
    mu = MerchantUpdate(name="Updated Name")
    
    # 调用被测试的方法
    resp = service.update_merchant("m3", mu, owner_id="owner-3")
    
    # 验证返回结果
    assert resp.id == "m3"
    assert resp.name == "Updated Name"


def test_update_merchant_no_permission(mock_service):
    """
    测试没有权限更新商家的情况
    """
    service, mock_supabase = mock_service

    # 模拟验证商家所有权失败（所有者不匹配）
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_response(data={"id":"mX","owner_id":"other"}, error=None)

    # 验证会抛出 PermissionError 异常
    with pytest.raises(PermissionError):
        mu = MerchantUpdate(name="X")
        service.update_merchant("mX", mu, owner_id="owner-3")


# ------------------------------
# delete_merchant (soft delete) - 成功 / 权限
# ------------------------------
def test_delete_merchant_success(mock_service):
    """
    测试成功删除（软删除）商家的情况
    """
    service, mock_supabase = mock_service

    # 模拟验证商家所有权成功
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_response(data={"id":"m9","owner_id":"owner9","status":"active"}, error=None)
    
    # 模拟更新状态为暂停的返回结果
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = make_response(data=[{"id":"m9"}], error=None)

    # 调用被测试的方法
    ok = service.delete_merchant("m9", owner_id="owner9")
    
    # 验证删除成功
    assert ok is True


def test_delete_merchant_no_permission(mock_service):
    """
    测试没有权限删除商家的情况
    """
    service, mock_supabase = mock_service
    
    # 模拟验证商家所有权失败
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_response(data={"id":"m9","owner_id":"other"}, error=None)

    # 验证会抛出 PermissionError 异常
    with pytest.raises(PermissionError):
        service.delete_merchant("m9", owner_id="owner9")


# ------------------------------
# list_merchants - 分页（注意方法签名）
# ------------------------------
def test_list_merchants_pagination(mock_service):
    """
    测试商家列表分页功能
    """
    service, mock_supabase = mock_service

    # 准备返回的商家列表数据
    rows = [
        {
            "id":"a1","name":"A","category":BusinessCategory.CAFE.value,
            "address":"x","phone":"0912345678","status":"active","owner_id":"ownerX",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "id":"a2","name":"B","category":BusinessCategory.CAFE.value,
            "address":"x2","phone":"0912345678","status":"active","owner_id":"ownerX",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    ]

    # 模拟分页查询的返回结果
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = make_response(data=rows, error=None)
    
    # 模拟总数查询的返回结果
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response(data=[{"id":"a1"}], count=2)

    # 调用被测试的方法
    res = service.list_merchants(owner_id="ownerX", page=1, page_size=2)
    
    # 验证返回结果
    assert res.total_count == 2
    assert len(res.merchants) == 2


# ------------------------------
# search_merchants - 使用 MerchantSearchParams
# ------------------------------
def test_search_merchants_basic(mock_service):
    """
    测试商家搜索功能
    """
    service, mock_supabase = mock_service

    # 准备搜索参数
    query_params = MerchantSearchParams(query="Tea", page=1, page_size=10)
    
    # 准备搜索结果数据
    rows = [
        {
            "id":"s1","name":"Tea House","category":BusinessCategory.CAFE.value,
            "address":"x","phone":"0912345678","status":"active","owner_id":"ownerS",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    ]
    
    # 模拟搜索查询的返回结果
    mock_supabase.table.return_value.select.return_value.or_.return_value.range.return_value.execute.return_value = make_response(data=rows, error=None)
    
    # 模拟总数查询的返回结果
    mock_supabase.table.return_value.select.return_value.or_.return_value.execute.return_value = make_response(data=[{"id":"s1"}], count=1)

    # 调用被测试的方法
    res = service.search_merchants(query_params)
    
    # 验证返回结果
    assert res.total_count == 1
    assert res.merchants[0].name == "Tea House"


# ------------------------------
# create_promotion / create_coupon - 返回 dict（service 返回 result.data[0]）
# ------------------------------
def test_create_promotion_success(mock_service):
    """
    测试成功创建促销活动的情况
    """
    service, mock_supabase = mock_service

    # 模拟验证商家所有权成功
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_response(
        data={"id": "merchant_123", "owner_id": "owner1", "status": "active"}, 
        error=None
    )

    # 准备促销活动数据
    promo = {
        "name":"50% OFF",
        "promotion_type":"discount",
        "start_date":"2025-01-01",
        "end_date":"2025-01-10"
    }
    
    # 模拟插入促销活动的返回结果
    mock_supabase.table.return_value.insert.return_value.execute.return_value = make_response(data=[{"id":"p1","name":"50% OFF"}], error=None)

    # 调用被测试的方法
    res = service.create_promotion(merchant_id="merchant_123", promotion_data=promo, owner_id="owner1")
    
    # 验证返回结果
    assert isinstance(res, dict)
    assert res["name"] == "50% OFF"


def test_create_coupon_success(mock_service):
    """
    测试成功创建优惠券的情况
    """
    service, mock_supabase = mock_service

    # 模拟验证商家所有权成功
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_response(
        data={"id": "merchant_123", "owner_id": "owner1", "status": "active"}, 
        error=None
    )

    # 准备优惠券数据
    coupon = {
        "code":"SAVE10","name":"Save 10","discount_type":"fixed","discount_value":10,
        "coupon_type":"public","valid_from":"2025-01-01","valid_to":"2025-02-01"
    }
    
    # 模拟插入优惠券的返回结果
    mock_supabase.table.return_value.insert.return_value.execute.return_value = make_response(data=[{"id":"c1","code":"SAVE10"}], error=None)

    # 调用被测试的方法
    res = service.create_coupon(merchant_id="merchant_123", coupon_data=coupon, owner_id="owner1")
    
    # 验证返回结果
    assert res["code"] == "SAVE10"


# ------------------------------
# create_review - 成功/失败
# ------------------------------
def test_create_review_success(mock_service, monkeypatch):
    """
    测试成功创建评价的情况
    """
    service, mock_supabase = mock_service

    # 使用 monkeypatch 模拟 get_merchant 方法返回成功结果
    monkeypatch.setattr(service, "get_merchant", lambda x: True)

    # 准备评价数据
    mock_supabase.table.return_value.insert.return_value.execute.return_value = make_response(data=[{
        "id":"r1","merchant_id":"m1","user_id":"u1","rating":5,"comment":"Nice",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }], error=None)

    # 准备创建评价的数据模型
    rc = ReviewCreate(merchant_id="m1", user_id="u1", rating=5, comment="Nice")
    
    # 调用被测试的方法
    resp = service.create_review(rc)
    
    # 验证返回结果
    assert resp.rating == 5
    assert resp.merchant_id == "m1"


def test_create_review_fail(mock_service, monkeypatch):
    """
    测试创建评价失败的情况
    """
    service, mock_supabase = mock_service

    # 使用 monkeypatch 模拟 get_merchant 方法返回成功结果
    monkeypatch.setattr(service, "get_merchant", lambda x: True)
    
    # 模拟插入评价失败的情况
    mock_supabase.table.return_value.insert.return_value.execute.return_value = make_response(data=None, error={"message":"fail"})

    # 准备创建评价的数据模型
    rc = ReviewCreate(merchant_id="m1", user_id="u1", rating=1, comment="Bad")
    
    # 验证会抛出 RuntimeError 异常
    with pytest.raises(RuntimeError):
        service.create_review(rc)