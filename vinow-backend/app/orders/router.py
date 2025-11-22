# [文件: app/orders/router.py] [行号: 601-800]
"""
订单中心路由 - v1.3.0
完整的订单管理、状态跟踪、订单历史功能
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.common.database import supabase
from app.common.models import (
    CreateOrderRequest, OrderResponse, OrderStatus, PaymentMethod, 
    PaymentStatus, OrderItem, SuccessResponse, PaginatedResponse, UserProfile
)
from app.common.auth import get_current_user

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

# 模拟数据存储（生产环境用数据库）
orders_storage = {}
order_items_storage = {}
order_status_logs_storage = {}

# 模拟商家数据
MOCK_MERCHANTS = {
    "merchant_1": {
        "id": "merchant_1",
        "name": "Pho 24",
        "cuisine": "越南菜",
        "rating": 4.5,
        "delivery_time": "20-30分钟",
        "min_order_amount": 50000,
        "delivery_fee": 15000,
        "image_url": "/images/merchants/pho24.jpg"
    },
    "merchant_2": {
        "id": "merchant_2", 
        "name": "Banh Mi Huynh Hoa",
        "cuisine": "越南菜", 
        "rating": 4.8,
        "delivery_time": "15-25分钟",
        "min_order_amount": 30000,
        "delivery_fee": 10000,
        "image_url": "/images/merchants/banhmi.jpg"
    },
    "merchant_3": {
        "id": "merchant_3",
        "name": "Pizza 4P's",
        "cuisine": "意大利菜",
        "rating": 4.7,
        "delivery_time": "30-40分钟", 
        "min_order_amount": 100000,
        "delivery_fee": 20000,
        "image_url": "/images/merchants/pizza4ps.jpg"
    }
}

# 模拟商品数据
MOCK_PRODUCTS = {
    "product_1": {
        "id": "product_1",
        "name": "Pho Bo",
        "description": "经典越南牛肉粉",
        "price": 65000,
        "category": "主食",
        "image_url": "/images/products/phobo.jpg",
        "merchant_id": "merchant_1",
        "available": True
    },
    "product_2": {
        "id": "product_2",
        "name": "Banh Mi Thit",
        "description": "越南烤肉三明治", 
        "price": 35000,
        "category": "快餐",
        "image_url": "/images/products/banhmithit.jpg",
        "merchant_id": "merchant_2",
        "available": True
    },
    "product_3": {
        "id": "product_3", 
        "name": "Margherita Pizza",
        "description": "经典玛格丽特披萨",
        "price": 120000,
        "category": "披萨",
        "image_url": "/images/products/pizza.jpg", 
        "merchant_id": "merchant_3",
        "available": True
    },
    "product_4": {
        "id": "product_4",
        "name": "Goi Cuon", 
        "description": "越南春卷",
        "price": 25000,
        "category": "小吃",
        "image_url": "/images/products/goicuon.jpg",
        "merchant_id": "merchant_1", 
        "available": True
    }
}

def generate_order_number() -> str:
    """生成订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = str(uuid.uuid4())[:8].upper()
    return f"VN{timestamp}{random_str}"

def calculate_order_totals(items: List[OrderItem], merchant_id: str) -> Dict[str, float]:
    """计算订单总金额"""
    subtotal = sum(item.unit_price * item.quantity for item in items)
    
    merchant = MOCK_MERCHANTS.get(merchant_id, {})
    delivery_fee = merchant.get("delivery_fee", 15000)
    min_order_amount = merchant.get("min_order_amount", 0)
    
    # 检查最低订单金额
    if subtotal < min_order_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单金额不能低于 {min_order_amount:,} VND"
        )
    
    # 模拟折扣（满减活动）
    discount = 0
    if subtotal >= 100000:
        discount = 10000
    elif subtotal >= 50000:
        discount = 5000
    
    final_amount = subtotal + delivery_fee - discount
    
    return {
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "discount_amount": discount,
        "final_amount": final_amount
    }

def log_order_status(order_id: str, from_status: str, to_status: str, note: str = ""):
    """记录订单状态变更日志"""
    log_data = {
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "from_status": from_status,
        "to_status": to_status,
        "note": note,
        "created_at": datetime.now().isoformat()
    }
    
    try:
        supabase.table("order_status_logs").insert(log_data).execute()
    except Exception:
        if order_id not in order_status_logs_storage:
            order_status_logs_storage[order_id] = []
        order_status_logs_storage[order_id].append(log_data)

@router.get("/", response_model=PaginatedResponse)
async def get_orders(
    current_user: UserProfile = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    merchant_id: Optional[str] = None
):
    """获取订单列表（支持分页和筛选）"""
    try:
        user_id = current_user.id
        
        # 从数据库获取订单
        try:
            query = supabase.table("orders").select("*").eq("user_id", user_id)
            if status:
                query = query.eq("status", status.value)
            if merchant_id:
                query = query.eq("merchant_id", merchant_id)
            result = query.execute()
            orders = result.data if result.data else []
        except Exception:
            orders = [order for order in orders_storage.values() if order.get("user_id") == user_id]
            if status:
                orders = [order for order in orders if order.get("status") == status.value]
            if merchant_id:
                orders = [order for order in orders if order.get("merchant_id") == merchant_id]
        
        # 获取订单商品
        for order in orders:
            order_id = order["id"]
            try:
                items_result = supabase.table("order_items").select("*").eq("order_id", order_id).execute()
                order["items"] = items_result.data if items_result.data else []
            except Exception:
                order["items"] = order_items_storage.get(order_id, [])
        
        # 按创建时间倒序排序
        orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = orders[start_idx:end_idx]
        
        return PaginatedResponse(
            items=paginated_items,
            total=len(orders),
            page=page,
            page_size=page_size,
            has_next=end_idx < len(orders)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取订单列表失败: {str(e)}"
        )

@router.post("/", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """创建新订单"""
    try:
        user_id = current_user.id
        
        # 验证商家是否存在
        merchant = MOCK_MERCHANTS.get(request.merchant_id)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商家不存在"
            )
        
        # 验证商品
        for item in request.items:
            product = MOCK_PRODUCTS.get(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"商品不存在: {item.product_id}"
                )
            if not product.get("available", True):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"商品已下架: {product['name']}"
                )
            if product.get("merchant_id") != request.merchant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"商品不属于该商家: {product['name']}"
                )
        
        # 计算订单金额
        totals = calculate_order_totals(request.items, request.merchant_id)
        
        # 生成订单数据
        order_id = str(uuid.uuid4())
        order_data = {
            "id": order_id,
            "order_number": generate_order_number(),
            "user_id": user_id,
            "merchant_id": request.merchant_id,
            "status": OrderStatus.PENDING.value,
            "total_amount": totals["subtotal"],
            "delivery_fee": totals["delivery_fee"],
            "discount_amount": totals["discount_amount"],
            "final_amount": totals["final_amount"],
            "payment_method": request.payment_method.value,
            "payment_status": PaymentStatus.PENDING.value,
            "delivery_address": request.delivery_address,
            "special_instructions": request.special_instructions,
            "estimated_preparation_time": merchant.get("delivery_time", "25-35").split("-")[1] + "分钟",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 保存订单到数据库
        try:
            order_result = supabase.table("orders").insert(order_data).execute()
            saved_order = order_result.data[0] if order_result.data else order_data
        except Exception:
            orders_storage[order_id] = order_data
            saved_order = order_data
        
        # 保存订单商品
        order_items = []
        for item in request.items:
            product = MOCK_PRODUCTS[item.product_id]
            item_data = {
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "product_id": item.product_id,
                "product_name": product["name"],
                "unit_price": float(item.unit_price),
                "quantity": item.quantity,
                "options": item.options,
                "subtotal": float(item.unit_price * item.quantity),
                "created_at": datetime.now().isoformat()
            }
            
            try:
                supabase.table("order_items").insert(item_data).execute()
            except Exception:
                if order_id not in order_items_storage:
                    order_items_storage[order_id] = []
                order_items_storage[order_id].append(item_data)
            
            order_items.append(item_data)
        
        # 记录状态变更日志
        log_order_status(order_id, "", OrderStatus.PENDING.value, "订单创建成功")
        
        # 构建响应
        response_data = {**saved_order, "items": order_items}
        
        print(f"✅ 订单创建成功: {order_id} - {saved_order['order_number']}")
        
        return OrderResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建订单失败: {str(e)}"
        )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_detail(
    order_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """获取订单详情"""
    try:
        user_id = current_user.id
        
        # 从数据库获取订单
        try:
            order_result = supabase.table("orders").select("*").eq("id", order_id).eq("user_id", user_id).execute()
            if not order_result.data:
                raise HTTPException(404, "订单不存在")
            order = order_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            order = orders_storage.get(order_id)
            if not order or order.get("user_id") != user_id:
                raise HTTPException(404, "订单不存在")
        
        # 获取订单商品
        try:
            items_result = supabase.table("order_items").select("*").eq("order_id", order_id).execute()
            order["items"] = items_result.data if items_result.data else []
        except Exception:
            order["items"] = order_items_storage.get(order_id, [])
        
        # 获取状态变更日志
        try:
            logs_result = supabase.table("order_status_logs").select("*").eq("order_id", order_id).execute()
            order["status_logs"] = logs_result.data if logs_result.data else []
        except Exception:
            order["status_logs"] = order_status_logs_storage.get(order_id, [])
        
        # 添加商家信息
        merchant_id = order.get("merchant_id")
        if merchant_id:
            order["merchant_info"] = MOCK_MERCHANTS.get(merchant_id, {})
        
        return OrderResponse(**order)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取订单详情失败: {str(e)}"
        )

@router.put("/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    reason: str = Query(..., description="取消原因"),
    current_user: UserProfile = Depends(get_current_user)
):
    """取消订单"""
    try:
        user_id = current_user.id
        
        # 从数据库获取订单
        try:
            order_result = supabase.table("orders").select("*").eq("id", order_id).eq("user_id", user_id).execute()
            if not order_result.data:
                raise HTTPException(404, "订单不存在")
            order = order_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            order = orders_storage.get(order_id)
            if not order or order.get("user_id") != user_id:
                raise HTTPException(404, "订单不存在")
        
        current_status = order.get("status")
        
        # 检查订单状态是否可以取消
        cancellable_statuses = [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]
        if current_status not in cancellable_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前订单状态无法取消"
            )
        
        # 更新订单状态
        update_data = {
            "status": OrderStatus.CANCELLED.value,
            "cancelled_at": datetime.now().isoformat(),
            "cancellation_reason": reason,
            "updated_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("orders").update(update_data).eq("id", order_id).execute()
            order.update(update_data)
        except Exception:
            orders_storage[order_id].update(update_data)
        
        # 记录状态变更日志
        log_order_status(order_id, current_status, OrderStatus.CANCELLED.value, f"用户取消订单: {reason}")
        
        print(f"✅ 订单取消成功: {order_id}")
        
        return SuccessResponse(message="订单取消成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消订单失败: {str(e)}"
        )

@router.get("/{order_id}/track")
async def track_order(
    order_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """订单状态跟踪"""
    try:
        user_id = current_user.id
        
        # 获取订单基本信息
        try:
            order_result = supabase.table("orders").select("*").eq("id", order_id).eq("user_id", user_id).execute()
            if not order_result.data:
                raise HTTPException(404, "订单不存在")
            order = order_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            order = orders_storage.get(order_id)
            if not order or order.get("user_id") != user_id:
                raise HTTPException(404, "订单不存在")
        
        # 获取状态日志
        try:
            logs_result = supabase.table("order_status_logs").select("*").eq("order_id", order_id).execute()
            status_logs = logs_result.data if logs_result.data else []
        except Exception:
            status_logs = order_status_logs_storage.get(order_id, [])
        
        # 构建状态跟踪信息
        status_flow = [
            {"status": OrderStatus.PENDING.value, "name": "待确认", "completed": True},
            {"status": OrderStatus.CONFIRMED.value, "name": "已确认", "completed": order.get("status") != OrderStatus.PENDING.value},
            {"status": OrderStatus.PREPARING.value, "name": "制作中", "completed": order.get("status") in [OrderStatus.PREPARING.value, OrderStatus.READY.value, OrderStatus.COMPLETED.value]},
            {"status": OrderStatus.READY.value, "name": "待取餐", "completed": order.get("status") in [OrderStatus.READY.value, OrderStatus.COMPLETED.value]},
            {"status": OrderStatus.COMPLETED.value, "name": "已完成", "completed": order.get("status") == OrderStatus.COMPLETED.value}
        ]
        
        # 估算剩余时间（简化版）
        status_times = {
            OrderStatus.PENDING.value: 5,  # 5分钟
            OrderStatus.CONFIRMED.value: 2,  # 2分钟
            OrderStatus.PREPARING.value: 15,  # 15分钟
            OrderStatus.READY.value: 5  # 5分钟
        }
        
        estimated_remaining = 0
        current_status_index = next((i for i, s in enumerate(status_flow) if s["status"] == order.get("status")), 0)
        
        for i in range(current_status_index, len(status_flow)):
            if not status_flow[i]["completed"]:
                estimated_remaining += status_times.get(status_flow[i]["status"], 5)
        
        tracking_info = {
            "order_id": order_id,
            "order_number": order.get("order_number"),
            "current_status": order.get("status"),
            "status_flow": status_flow,
            "status_logs": sorted(status_logs, key=lambda x: x.get("created_at", ""), reverse=True),
            "estimated_remaining_minutes": estimated_remaining,
            "merchant_info": MOCK_MERCHANTS.get(order.get("merchant_id", ""), {}),
            "last_updated": order.get("updated_at")
        }
        
        return SuccessResponse(
            message="订单跟踪信息获取成功",
            data=tracking_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取订单跟踪信息失败: {str(e)}"
        )

@router.get("/stats/summary")
async def get_order_stats_summary(current_user: UserProfile = Depends(get_current_user)):
    """获取订单统计摘要"""
    try:
        user_id = current_user.id
        
        # 从数据库获取订单统计
        try:
            orders_result = supabase.table("orders").select("*").eq("user_id", user_id).execute()
            all_orders = orders_result.data if orders_result.data else []
        except Exception:
            all_orders = [order for order in orders_storage.values() if order.get("user_id") == user_id]
        
        # 计算统计信息
        total_orders = len(all_orders)
        completed_orders = len([o for o in all_orders if o.get("status") == OrderStatus.COMPLETED.value])
        pending_orders = len([o for o in all_orders if o.get("status") in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value, OrderStatus.PREPARING.value]])
        cancelled_orders = len([o for o in all_orders if o.get("status") == OrderStatus.CANCELLED.value])
        
        total_spent = sum(o.get("final_amount", 0) for o in all_orders if o.get("status") == OrderStatus.COMPLETED.value)
        money_saved = sum(o.get("discount_amount", 0) for o in all_orders)
        
        # 最近30天订单趋势
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_orders = [o for o in all_orders if datetime.fromisoformat(o.get("created_at", "2000-01-01")) >= thirty_days_ago]
        
        stats = {
            "summary": {
                "total_orders": total_orders,
                "completed_orders": completed_orders,
                "pending_orders": pending_orders,
                "cancelled_orders": cancelled_orders,
                "completion_rate": round((completed_orders / total_orders * 100) if total_orders > 0 else 0, 1),
                "total_spent": total_spent,
                "money_saved": money_saved
            },
            "recent_activity": {
                "last_30_days_orders": len(recent_orders),
                "average_order_value": round(total_spent / completed_orders, 2) if completed_orders > 0 else 0,
                "favorite_merchants": self._get_favorite_merchants(all_orders)
            }
        }
        
        return SuccessResponse(
            message="订单统计获取成功",
            data=stats
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取订单统计失败: {str(e)}"
        )

def _get_favorite_merchants(orders: List[Dict]) -> List[Dict]:
    """获取最常订购的商家"""
    from collections import Counter
    merchant_counts = Counter(order.get("merchant_id") for order in orders)
    top_merchants = merchant_counts.most_common(3)
    
    return [
        {
            "merchant_id": merchant_id,
            "merchant_name": MOCK_MERCHANTS.get(merchant_id, {}).get("name", "未知商家"),
            "order_count": count
        }
        for merchant_id, count in top_merchants
    ]

# 商家操作端点（模拟商家处理订单）
@router.put("/{order_id}/status")
async def update_order_status(
    order_id: str,
    new_status: OrderStatus,
    note: str = Query("", description="状态变更说明"),
    current_user: UserProfile = Depends(get_current_user)
):
    """更新订单状态（商家操作）"""
    try:
        # 从数据库获取订单
        try:
            order_result = supabase.table("orders").select("*").eq("id", order_id).execute()
            if not order_result.data:
                raise HTTPException(404, "订单不存在")
            order = order_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            order = orders_storage.get(order_id)
            if not order:
                raise HTTPException(404, "订单不存在")
        
        old_status = order.get("status")
        
        # 更新订单状态
        update_data = {
            "status": new_status.value,
            "updated_at": datetime.now().isoformat()
        }
        
        # 如果是完成状态，记录完成时间
        if new_status == OrderStatus.COMPLETED:
            update_data["completed_at"] = datetime.now().isoformat()
        
        try:
            supabase.table("orders").update(update_data).eq("id", order_id).execute()
            order.update(update_data)
        except Exception:
            orders_storage[order_id].update(update_data)
        
        # 记录状态变更日志
        log_order_status(order_id, old_status, new_status.value, note or f"状态更新: {old_status} -> {new_status.value}")
        
        print(f"✅ 订单状态更新: {order_id} - {old_status} -> {new_status.value}")
        
        return SuccessResponse(message="订单状态更新成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新订单状态失败: {str(e)}"
        )

# 开发环境调试端点
@router.get("/debug/data")
async def debug_order_data(current_user: UserProfile = Depends(get_current_user)):
    """查看订单数据（仅开发环境）"""
    user_id = current_user.id
    
    user_orders = [order for order in orders_storage.values() if order.get("user_id") == user_id]
    
    return {
        "orders": user_orders,
        "order_items": order_items_storage,
        "status_logs": order_status_logs_storage,
        "mock_merchants": MOCK_MERCHANTS,
        "mock_products": MOCK_PRODUCTS
    }