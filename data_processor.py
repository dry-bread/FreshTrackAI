# -*- coding: utf-8 -*-
"""
data_processor.py
冰箱物品数据处理模块
- 接收AI识别结果
- 与数据库对比
- 调用agent api工具辅助判断
- 更新数据库
"""


import os
import json
from typing import List, Dict, Any, Optional
import requests
from db import (
    get_all_items,
    get_item_by_id,
    add_fridge_item,
    delete_item,
)

from db import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)

def get_current_fridge_items() -> List[Dict[str, Any]]:
    """获取数据库中当前所有冰箱物品"""
    session = SessionLocal()
    try:
        items = get_all_items(session)
        # 转为dict列表，排除SQLAlchemy内部字段
        result = []
        for item in items:
            item_dict = {
                'id': item.id,
                'name': item.name,
                'category': item.category,
                'subcategory': item.subcategory,
                'brand': item.brand,
                'confidence': float(item.confidence) if item.confidence is not None else None, # pyright: ignore[reportArgumentType]
                'image_url': item.image_url,
                'position': item.position,
                'item_amount_desc': item.item_amount_desc,
                'freshness': item.freshness,
                'expiry_estimate': item.expiry_estimate,
                'additional_info': item.additional_info,
                'detected_at': item.detected_at.isoformat() if item.detected_at is not None else None,
                'device_id': item.device_id,
                'put_in_time': item.put_in_time.isoformat() if item.put_in_time is not None else None
            }
            result.append(item_dict)
        return result
    finally:
        session.close()


def get_item_image_by_id(item_id: int) -> Optional[str]:
    """通过id获取物品截图（调用agent api的tool）"""
    # TODO: 调用agent api获取图片
    pass



def get_hunyuan_tools_schema() -> List[Dict[str, Any]]:
    """定义冰箱物品相关的 tool schema，供 agent functioncall 使用"""
    return [
        {
            "Type": "function",
            "Function": {
                "Name": "get_current_fridge_items",
                "Description": "获取当前冰箱中所有物品",
                "Parameters": "{}"
            }
        },
        {
            "Type": "function",
            "Function": {
                "Name": "get_item_image_by_id",
                "Description": "根据物品id获取物品截图",
                "Parameters": '{"type": "object", "properties": {"item_id": {"type": "integer"}}, "required": ["item_id"]}'
            }
        },
        {
            "Type": "function",
            "Function": {
                "Name": "add_fridge_item",
                "Description": "新增物品到冰箱数据库",
                "Parameters": '{"type": "object", "properties": {"item_info": {"type": "object"}}, "required": ["item_info"]}'
            }
        },
        {
            "Type": "function",
            "Function": {
                "Name": "update_fridge_item",
                "Description": "根据id更新冰箱物品信息",
                "Parameters": '{"type": "object", "properties": {"item_id": {"type": "integer"}, "item_info": {"type": "object"}}, "required": ["item_id", "item_info"]}'
            }
        },
        {
            "Type": "function",
            "Function": {
                "Name": "delete_fridge_item",
                "Description": "根据id删除冰箱物品",
                "Parameters": '{"type": "object", "properties": {"item_id": {"type": "integer"}}, "required": ["item_id"]}'
            }
        }
    ]


def call_hunyuan_agent_api(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], tool_choice: str = "auto") -> Dict[str, Any]:
    """调用腾讯混元 functioncall agent api，返回响应（使用官方SDK）"""
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
    import logging

    secret_id = os.getenv("TENCENTCLOUD_SECRET_ID")
    secret_key = os.getenv("TENCENTCLOUD_SECRET_KEY")
    if not secret_id or not secret_key:
        raise ValueError("请设置腾讯云API密钥环境变量")

    cred = credential.Credential(secret_id, secret_key)
    httpProfile = HttpProfile()
    httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
    httpProfile.reqTimeout = 120
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = hunyuan_client.HunyuanClient(cred, "", clientProfile)

    # 构造请求参数
    params = {
        "Model": "hunyuan-functioncall",
        "Stream": False,
        "Messages": messages,
        "Tools": tools,
        "ToolChoice": tool_choice,
        "Temperature": 0.1,
        "TopP": 0.9
    }
    req = models.ChatCompletionsRequest()
    req.from_json_string(json.dumps(params, ensure_ascii=False))
    try:
        resp = client.ChatCompletions(req)
        # SDK返回对象可能为generator或对象，需兼容
        if hasattr(resp, 'to_json_string'):
            resp_dict = json.loads(resp.to_json_string()) # type: ignore
        elif isinstance(resp, dict):
            resp_dict = resp
        else:
            # 兼容generator等
            resp_dict = json.loads(json.dumps(resp, default=lambda o: o.__dict__))
        return resp_dict
    except Exception as e:
        logging.error(f"调用混元agent api失败: {e}")
        return {"error": str(e)}


def execute_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """根据agent返回的ToolCall，自动调用本地对应函数并返回结果"""
    name = tool_call["Function"]["Name"]
    args = json.loads(tool_call["Function"].get("Arguments", "{}"))
    logging.info("[execute_tool_call] name: %s, args: %s", name, args)
    if name == "get_current_fridge_items":
        items = get_current_fridge_items()
        return {"items": items}  # items已经是字典列表了
    elif name == "get_item_image_by_id":
        item_id = args.get("item_id")
        return {"image_url": get_item_image_by_id(item_id)}
    elif name == "add_fridge_item":
        info = args.get("item_info")
        item = add_item_to_db(info)
        return {"item_id": item.id}
    elif name == "update_fridge_item":
        item_id = args.get("item_id")
        info = args.get("item_info")
        item = update_item_in_db(item_id, info)
        return {"item_id": item.id if item else None}
    elif name == "delete_fridge_item":
        item_id = args.get("item_id")
        ok = delete_item_from_db(item_id)
        return {"success": ok}
    else:
        return {"error": f"Unknown tool: {name}"}


def agent_process_and_update(new_items: List[Dict[str, Any]]):
    """
    主流程：
    - 构造messages和tools
    - 调用agent api
    - 自动执行tool call并多轮交互
    - 最终完成数据库自动更新
    """
    tools = get_hunyuan_tools_schema()
    logging.info("[agent_process_and_update] 启动，new_items: %s", json.dumps(new_items, ensure_ascii=False))
    # 获取数据库中上次冰箱物品信息
    last_items = get_current_fridge_items()
    # 说明部分
    instruction = (
        "你是FreshTrackAI智能冰箱管理系统的agent。请严格按照如下流程处理：\n\n"
        "**第一步：数据对比分析**\n"
        "1. 对比【数据库中上次冰箱物品信息】和【本次冰箱照片识别结果】\n"
        "2. 根据物品名称、分类、特征等判断哪些可能是同一种物品\n"
        "3. 对于疑似相同的物品，如果需要确认可调用get_item_image_by_id获取数据库中物品的图片进行比对\n\n"
        "**第二步：数据库更新操作**\n"
        "严格按照以下规则进行数据库操作：\n"
        "- 🆕 **新物品**: 如果识别结果中的物品在数据库中不存在，调用add_fridge_item新增\n"
        "- 🔄 **更新物品**: 如果物品存在但信息有变化(数量、位置、新鲜度等)，调用update_fridge_item更新\n"
        "- ❌ **删除物品**: 如果数据库中的物品在本次识别中消失，调用delete_fridge_item删除\n"
        "- ✅ **无变化**: 如果物品信息完全一致，无需操作\n\n"
        "**重要说明**:\n"
        "- 必须处理所有15个识别物品，不能遗漏\n"
        "- 优先基于物品名称和分类进行匹配，图片比对为辅助手段\n"
        "- 当无法确定是否为同一物品时，倾向于新增而非忽略\n"
        "- 完成所有操作后提供操作摘要\n\n"
        "请现在开始处理，确保每个识别出的物品都得到妥善处理。"
    )
    # 组装message
    messages = [
        {
            "Role": "user",
            "Content": (
                instruction +
                f"\n\n【数据库中上次冰箱物品信息】\n{json.dumps(last_items, ensure_ascii=False)}" +
                f"\n\n【本次冰箱照片识别结果】\n{json.dumps(new_items, ensure_ascii=False)}"
            )
        }
    ]
    while True:
        resp = call_hunyuan_agent_api(messages, tools)
        logging.info("[agent_process_and_update] agent api resp: %s", json.dumps(resp, ensure_ascii=False))
        # 兼容两种响应格式：有Response包装和直接Choices
        choices = resp.get("Response", {}).get("Choices", [])
        if not choices:
            choices = resp.get("Choices", [])
        if not choices:
            break
        msg = choices[0]["Message"]
        messages.append(msg)
        tool_calls = msg.get("ToolCalls", [])
        logging.info("[agent_process_and_update] tool_calls: %s", tool_calls)
        if not tool_calls:
            break
        # 执行所有tool call
        for tool_call in tool_calls:
            logging.info("[agent_process_and_update] 执行tool_call: %s", tool_call)
            tool_result = execute_tool_call(tool_call)
            logging.info("[agent_process_and_update] tool_result: %s", tool_result)
            messages.append({
                "Role": "tool",
                "ToolCallId": tool_call.get("Id", ""),
                "Content": json.dumps(tool_result, ensure_ascii=False)
            })
    # 最终结果
    return messages


def add_item_to_db(item_info: Dict[str, Any]):
    logging.info("[add_item_to_db] item_info: %s", item_info)
    # 只保留ORM支持的字段，丢弃 quantity、estimated_size、fridge_closed_time
    orm_fields = {
        'name', 'category', 'subcategory', 'brand', 'confidence', 'image_url', 'position',
        'item_amount_desc', 'freshness', 'expiry_estimate', 'additional_info', 'detected_at',
        'device_id', 'put_in_time'
    }
    filtered_info = {k: v for k, v in item_info.items() if k in orm_fields}
    # 类型处理：position/additional_info 必须为 dict
    for key in ['position', 'additional_info']:
        if key in filtered_info and not isinstance(filtered_info[key], dict):
            try:
                filtered_info[key] = json.loads(filtered_info[key])
            except Exception:
                filtered_info[key] = None
    session = SessionLocal()
    try:
        item = add_fridge_item(session, item_data=filtered_info)
        logging.info("[add_item_to_db] 新增物品id: %s", getattr(item, 'id', None))
        return item
    except Exception as e:
        logging.error("[add_item_to_db] 插入异常: %s", e)
        raise
    finally:
        session.close()


def update_item_in_db(item_id: int, item_info: Dict[str, Any]):
    """更新数据库中的物品信息"""
    from db import FridgeItem
    session = SessionLocal()
    try:
        item = session.query(FridgeItem).filter_by(id=item_id).first()
        if not item:
            return None
        for k, v in item_info.items():
            setattr(item, k, v)
        session.commit()
        session.refresh(item)
        return item
    finally:
        session.close()


def delete_item_from_db(item_id: int):
    """删除数据库中的物品"""
    session = SessionLocal()
    try:
        return delete_item(session, item_id)
    finally:
        session.close()


# 你可以在这里实现主流程的调用示例
if __name__ == "__main__":
    # 示例：模拟AI识别结果（格式参考freshtrack_ai_recognizer.py输出）
    new_items_json = [
        {
            "name": "牛奶",
            "category": "乳制品",
            "subcategory": "牛奶",
            "brand": "伊利",
            "confidence": 0.98,
            "position": {"x": 120, "y": 80, "width": 60, "height": 120},
            "quantity": 2,
            "estimated_size": "medium",
            "freshness": "good",
            "additional_info": {"color": "白色", "packaging": "纸盒", "expiry_estimate": "7天"},
            "image_url": "https://example.com/milk.jpg",
            "put_in_time": "2025-09-20T18:00:00+08:00"
        },
        {
            "name": "鸡蛋",
            "category": "肉类",
            "subcategory": "蛋类",
            "brand": "",
            "confidence": 0.95,
            "position": {"x": 200, "y": 150, "width": 40, "height": 40},
            "quantity": 6,
            "estimated_size": "small",
            "freshness": "good",
            "additional_info": {"color": "褐色", "packaging": "散装", "expiry_estimate": "10天"},
            "image_url": "https://example.com/egg.jpg",
            "put_in_time": "2025-09-20T18:00:00+08:00"
        }
    ]
    # 假设本次识别发生在某次关门后
    fridge_closed_time = "2025-09-20T18:05:00+08:00"
    # 可将关门时间加入每个物品或单独传递
    for item in new_items_json:
        item["fridge_closed_time"] = fridge_closed_time

    # 调用agent自动处理
    result = agent_process_and_update(new_items_json)
    print("\nAgent多轮处理结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
