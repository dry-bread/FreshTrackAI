#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreshTrackAI 完整流程测试
测试从图像识别到数据库更新的完整管道流程
"""

import sys
import os
import json
from datetime import datetime
import logging

# 添加项目根目录到路径
sys.path.append('/Users/limanting/code/FreshTrackAI')

from freshtrack_ai_recognizer import FreshTrackItemRecognizer
from data_processor import agent_process_and_update
from db import SessionLocal, get_all_items, create_tables

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"🔄 {title}")
    print("=" * 60)

def show_database_before():
    """显示测试前的数据库状态"""
    print_separator("测试前数据库状态")
    
    session = SessionLocal()
    try:
        items = get_all_items(session)
        print(f"📊 当前数据库中有 {len(items)} 个物品")
        
        if items:
            print("📋 现有物品列表:")
            for i, item in enumerate(items, 1):
                print(f"   {i}. {item.name} (ID: {item.id}) - {item.category}")
        else:
            print("💭 数据库为空，这是一个新测试")
            
    finally:
        session.close()

def test_ai_recognition():
    """测试AI图像识别功能"""
    print_separator("步骤1: AI图像识别")
    
    # 使用指定的测试图片
    test_image_url = "https://img0.baidu.com/it/u=2574745022,655714543&fm=253&fmt=auto&app=138&f=JPEG?w=200&h=300"
    device_id = "test_device_001"
    
    print(f"🖼️  测试图片URL: {test_image_url}")
    print(f"📱 设备ID: {device_id}")
    print("\n🤖 开始调用腾讯混元AI进行图像识别...")
    
    try:
        # 初始化识别器
        recognizer = FreshTrackItemRecognizer()
        
        # 进行识别
        result = recognizer.recognize_fridge_items(test_image_url, device_id)
        
        # 显示识别结果
        if result.get('success', False):
            items = result.get('items', [])
            print(f"✅ 识别成功！发现 {len(items)} 个物品")
            
            print("\n📋 识别到的物品详情:")
            for i, item in enumerate(items, 1):
                print(f"   {i}. 物品名称: {item.get('name', '未知')}")
                print(f"      分类: {item.get('category', '未知')}/{item.get('subcategory', '未知')}")
                print(f"      品牌: {item.get('brand', '无') or '无'}")
                print(f"      置信度: {item.get('confidence', 0):.2f}")
                print(f"      数量: {item.get('quantity', 1)}")
                print(f"      大小: {item.get('estimated_size', '未知')}")
                print(f"      新鲜度: {item.get('freshness', '未知')}")
                if item.get('additional_info'):
                    print(f"      额外信息: {item['additional_info']}")
                print()
            
            # 显示API使用情况
            if 'api_usage' in result:
                usage = result['api_usage']
                print(f"📊 API使用统计:")
                print(f"   • 输入tokens: {usage.get('prompt_tokens', 0)}")
                print(f"   • 输出tokens: {usage.get('completion_tokens', 0)}")
                print(f"   • 总计tokens: {usage.get('total_tokens', 0)}")
            
            return result
            
        else:
            print(f"❌ 识别失败: {result.get('error', '未知错误')}")
            if 'raw_content' in result:
                print(f"🔍 原始响应: {result['raw_content'][:200]}...")
            return None
            
    except Exception as e:
        print(f"❌ 识别过程异常: {e}")
        logger.exception("识别异常详情")
        return None

def prepare_items_for_processor(recognition_result: dict) -> list:
    """将识别结果转换为data_processor所需的格式"""
    if not recognition_result or not recognition_result.get('success'):
        return []
    
    items = recognition_result.get('items', [])
    current_time = datetime.now().isoformat()
    
    processed_items = []
    for item in items:
        processed_item = {
            "name": item.get('name', '未知物品'),
            "category": item.get('category', '其他'),
            "subcategory": item.get('subcategory', ''),
            "brand": item.get('brand', ''),
            "confidence": item.get('confidence', 0.0),
            "position": item.get('position', {}),
            "quantity": item.get('quantity', 1),
            "estimated_size": item.get('estimated_size', 'medium'),
            "freshness": item.get('freshness', 'unknown'),
            "additional_info": item.get('additional_info', {}),
            "image_url": recognition_result.get('image_url', ''),
            "put_in_time": current_time,
            "device_id": recognition_result.get('device_id', 'unknown')
        }
        processed_items.append(processed_item)
    
    return processed_items

def test_data_processing(recognition_result: dict | None):
    """测试数据处理和数据库更新"""
    print_separator("步骤2: 智能数据处理")
    
    if not recognition_result:
        print("❌ 没有识别结果，跳过数据处理")
        return False
    
    # 转换数据格式
    items_for_processing = prepare_items_for_processor(recognition_result)
    
    if not items_for_processing:
        print("❌ 没有可处理的物品数据")
        return
    
    print(f"📝 准备处理 {len(items_for_processing)} 个识别物品")
    print("🤖 调用AI Agent进行智能数据库更新...")
    
    try:
        # 调用data_processor进行处理
        result_messages = agent_process_and_update(items_for_processing)
        
        print("✅ 数据处理完成！")
        print(f"📊 AI Agent执行了 {len(result_messages)} 轮对话")
        
        # 显示处理结果概要
        print("\n💬 AI处理概要:")
        for i, msg in enumerate(result_messages):
            role = msg.get('Role', 'unknown')
            content = msg.get('Content', '')
            tool_calls = msg.get('ToolCalls', [])
            
            if role == 'user':
                print(f"   {i+1}. 用户指令已发送")
            elif role == 'assistant':
                if tool_calls:
                    print(f"   {i+1}. AI决定执行 {len(tool_calls)} 个工具操作")
                    for tool in tool_calls:
                        tool_func = tool.get('Function', {})
                        tool_name = tool_func.get('Name', 'unknown') if isinstance(tool_func, dict) else 'unknown'
                        print(f"      • {tool_name}")
                elif content:
                    print(f"   {i+1}. AI回复: {content[:50]}{'...' if len(content) > 50 else ''}")
            elif role == 'tool':
                print(f"   {i+1}. 工具执行完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据处理异常: {e}")
        logger.exception("数据处理异常详情")
        return False

def show_database_after():
    """显示测试后的数据库状态"""
    print_separator("步骤3: 测试后数据库状态")
    
    session = SessionLocal()
    try:
        items = get_all_items(session)
        print(f"📊 当前数据库中有 {len(items)} 个物品")
        
        if items:
            print("📋 更新后的物品列表:")
            for i, item in enumerate(items, 1):
                print(f"   {i}. {item.name} (ID: {item.id})")
                print(f"      分类: {item.category}/{item.subcategory}")
                print(f"      品牌: {item.brand or '无'}")
                print(f"      新鲜度: {item.freshness or '未知'}")
                print(f"      放入时间: {item.put_in_time}")
                if item.additional_info is not None:
                    print(f"      额外信息: {item.additional_info}")
                print()
        
    finally:
        session.close()

def main():
    """主测试函数"""
    print("🚀 FreshTrackAI 完整流程测试开始")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 确保数据库表存在
        create_tables()
        
        # 显示测试前状态
        show_database_before()
        
        # 步骤1: 图像识别
        recognition_result = test_ai_recognition()
        
        # 步骤2: 数据处理
        processing_success = test_data_processing(recognition_result)
        
        # 步骤3: 显示最终状态
        show_database_after()
        
        # 测试总结
        print_separator("测试总结")
        if recognition_result and recognition_result.get('success') and processing_success:
            print("🎉 完整流程测试成功！")
            print("✅ 图像识别: 成功")
            print("✅ 智能处理: 成功") 
            print("✅ 数据库更新: 成功")
        else:
            print("⚠️ 测试部分失败")
            print(f"{'✅' if recognition_result and recognition_result.get('success') else '❌'} 图像识别")
            print(f"{'✅' if processing_success else '❌'} 数据库更新")
        
        print("\n📝 测试说明:")
        print("   1. 本测试使用了真实的腾讯云API进行图像识别")
        print("   2. 使用了真实的PostgreSQL数据库进行数据存储")
        print("   3. AI Agent自动决策了数据库操作")
        print("   4. 整个流程模拟了实际生产环境的使用场景")
        
        return recognition_result and recognition_result.get('success') and processing_success
        
    except Exception as e:
        print(f"❌ 测试过程异常: {e}")
        logger.exception("测试异常详情")
        return False

if __name__ == "__main__":
    success = main()
    exit_code = 0 if success else 1
    print(f"\n🏁 测试结束，退出码: {exit_code}")
    sys.exit(exit_code)