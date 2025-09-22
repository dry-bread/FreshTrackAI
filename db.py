from dotenv import load_dotenv
load_dotenv()
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Text, JSON, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

class FridgeItem(Base):
    __tablename__ = 'fridge_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    subcategory = Column(String(50))
    brand = Column(String(100))
    confidence = Column(Numeric(4, 3))
    image_url = Column(Text, nullable=False)
    position = Column(JSON)
    item_amount_desc = Column(String(100))  # 数量和体积等综合描述
    freshness = Column(String(20))
    expiry_estimate = Column(String(50))
    additional_info = Column(JSON)
    detected_at = Column(TIMESTAMP(timezone=True))
    device_id = Column(String(100))
    put_in_time = Column(TIMESTAMP(timezone=True))

# 数据库连接配置
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

def create_tables():
    Base.metadata.create_all(engine)

def add_fridge_item(session, item_data: dict):
    item = FridgeItem(**item_data)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def get_all_items(session):
    return session.query(FridgeItem).all()

def get_items_by_device(session, device_id: str):
    return session.query(FridgeItem).filter(FridgeItem.device_id == device_id).all()

def get_item_by_id(session, item_id: int):
    return session.query(FridgeItem).filter(FridgeItem.id == item_id).first()

def delete_item(session, item_id: int):
    item = get_item_by_id(session, item_id)
    if item:
        session.delete(item)
        session.commit()
        return True
    return False


def get_items_for_recommendation(session, device_id: Optional[str] = None):
    """
    获取用于菜谱推荐的食材列表，包含转换为推荐所需格式
    
    Args:
        session: 数据库会话
        device_id: 可选的设备ID筛选
        
    Returns:
        List[Dict]: 转换为推荐系统所需格式的食材列表
    """
    if device_id:
        items = session.query(FridgeItem).filter(FridgeItem.device_id == device_id).all()
    else:
        items = session.query(FridgeItem).all()
    
    # 转换为推荐系统所需的格式
    converted_items = []
    for item in items:
        converted_item = {
            "id": item.id,
            "name": item.name,
            "category": item.category or "未分类",
            "subcategory": item.subcategory,
            "brand": item.brand,
            "item_amount_desc": item.item_amount_desc or "未知数量",
            "freshness": item.freshness or "good",
            "expiry_estimate": item.expiry_estimate or "未知",
            "put_in_time": item.put_in_time.isoformat() if item.put_in_time else None,
            "detected_at": item.detected_at.isoformat() if item.detected_at else None,
            "additional_info": item.additional_info or {},
            "position": item.position or {},
            "confidence": float(item.confidence) if item.confidence else 0.0
        }
        converted_items.append(converted_item)
    
    return converted_items


def get_current_fridge_summary(session, device_id: Optional[str] = None):
    """
    获取当前冰箱状态摘要
    
    Args:
        session: 数据库会话  
        device_id: 可选的设备ID筛选
        
    Returns:
        Dict: 冰箱状态摘要
    """
    items = get_items_for_recommendation(session, device_id)
    
    # 统计信息
    total_items = len(items)
    categories = {}
    freshness_stats = {"good": 0, "fair": 0, "poor": 0}
    
    for item in items:
        # 统计分类
        category = item.get("category", "未分类")
        categories[category] = categories.get(category, 0) + 1
        
        # 统计新鲜度
        freshness = item.get("freshness", "good")
        if freshness in freshness_stats:
            freshness_stats[freshness] += 1
    
    return {
        "total_items": total_items,
        "categories": categories,
        "freshness_stats": freshness_stats,
        "items": items
    }


if __name__ == "__main__":
    import datetime
    print("1. 创建表...")
    create_tables()
    session = SessionLocal()
    try:
        print("2. 插入测试数据...")
        item_data = {
            'name': '测试牛奶',
            'category': '乳制品',
            'subcategory': '牛奶',
            'brand': '测试品牌',
            'confidence': 0.99,
            'image_url': 'https://example.com/test_milk.jpg',
            'position': {'x': 1, 'y': 2, 'width': 3, 'height': 4},
            'item_amount_desc': '1盒',
            'freshness': 'good',
            'expiry_estimate': '7天',
            'additional_info': {'color': '白色'},
            'detected_at': datetime.datetime.now(datetime.timezone.utc),
            'device_id': 'test_device',
            'put_in_time': datetime.datetime.now(datetime.timezone.utc)
        }
        item = add_fridge_item(session, item_data)
        print(f"插入成功，id={item.id}")
        print("3. 查询所有数据...")
        items = get_all_items(session)
        for i in items:
            print(f"id={i.id}, name={i.name}, put_in_time={i.put_in_time}")
        print("4. 删除测试数据...")
        if delete_item(session, item.id): # pyright: ignore[reportArgumentType]
            print("删除成功")
        else:
            print("删除失败")
    finally:
        session.close()