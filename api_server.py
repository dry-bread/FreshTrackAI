# -*- coding: utf-8 -*-
"""
FreshTrackAI - API服务器
为手机应用提供菜谱推荐和食材管理API
"""

import os
import json
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# 导入自定义模块
from db import SessionLocal, get_items_for_recommendation, get_current_fridge_summary
from meal_recommendation_agent import MealRecommendationAgent

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 初始化推荐代理
try:
    recommendation_agent = MealRecommendationAgent()
    logger.info("菜谱推荐代理初始化成功")
except Exception as e:
    logger.error(f"菜谱推荐代理初始化失败: {e}")
    recommendation_agent = None


@app.route('/api/meal-recommendation', methods=['POST'])
def meal_recommendation():
    """
    菜谱推荐API端点
    
    接收手机端请求，返回个性化菜谱推荐和食材管理建议
    """
    data = None
    device_id = None
    
    try:
        # 解析请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体为空或格式无效",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 400
        
        # 提取必要参数
        device_id = data.get('device_id')
        user_message = data.get('user_message')
        
        if not user_message:
            return jsonify({
                "success": False,
                "error": "缺少用户消息参数",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 400
        
        # 可选参数
        meal_type = data.get('meal_type')
        dietary_preferences = data.get('dietary_preferences')
        urgency_level = data.get('urgency_level', 'medium')
        
        logger.info(f"收到菜谱推荐请求 - 设备ID: {device_id}, 消息: {user_message}")
        
        # 检查推荐代理是否可用
        if not recommendation_agent:
            return jsonify({
                "success": False,
                "error": "推荐服务暂时不可用，请稍后重试",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "device_id": device_id
            }), 503
        
        # 从数据库获取食材数据
        session = SessionLocal()
        try:
            food_items = get_items_for_recommendation(session, device_id)
            logger.info(f"从数据库获取到 {len(food_items)} 个食材")
            
            if not food_items:
                return jsonify({
                    "success": True,
                    "message": "当前冰箱中没有食材，建议先添加一些新鲜食材。",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "device_id": device_id,
                    "food_inventory": {
                        "total_items": 0,
                        "fresh_items": [],
                        "expiring_soon": [],
                        "needs_attention": [],
                        "expired_items": []
                    },
                    "meal_recommendations": [],
                    "food_alerts": {
                        "urgent_count": 0,
                        "expiring_today": 0,
                        "expired_count": 0,
                        "recommendations": ["冰箱中暂无食材，建议购买一些新鲜食物"]
                    },
                    "api_usage": None
                })
            
            # 调用推荐代理生成推荐
            recommendation_result = recommendation_agent.recommend_meals(
                food_items=food_items,
                user_message=user_message,
                device_id=device_id,
                meal_type=meal_type,
                dietary_preferences=dietary_preferences
            )
            
            # 添加请求信息到响应
            recommendation_result.update({
                "request_info": {
                    "meal_type": meal_type,
                    "urgency_level": urgency_level,
                    "dietary_preferences": dietary_preferences,
                    "user_message": user_message
                }
            })
            
            logger.info(f"成功生成菜谱推荐 - 设备ID: {device_id}")
            return jsonify(recommendation_result)
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"API处理异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"服务器内部错误: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": device_id
        }), 500


@app.route('/api/fridge-status', methods=['GET'])
def fridge_status():
    """
    获取冰箱状态摘要
    
    返回当前冰箱中所有食材的基本统计信息
    """
    try:
        device_id = request.args.get('device_id')
        
        session = SessionLocal()
        try:
            summary = get_current_fridge_summary(session, device_id)
            logger.info(f"获取冰箱状态摘要 - 设备ID: {device_id}, 总计: {summary['total_items']} 个食材")
            
            return jsonify({
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "device_id": device_id,
                **summary
            })
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"获取冰箱状态异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取冰箱状态失败: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": request.args.get('device_id')
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "connected",
            "recommendation_agent": "available" if recommendation_agent else "unavailable",
            "api_server": "running"
        }
    })


@app.route('/', methods=['GET'])
def index():
    """API根端点"""
    return jsonify({
        "name": "FreshTrackAI API Server",
        "version": "1.0.0",
        "description": "智能冰箱管理系统API服务",
        "endpoints": {
            "POST /api/meal-recommendation": "获取个性化菜谱推荐",
            "GET /api/fridge-status": "获取冰箱状态摘要",
            "GET /api/health": "服务健康检查"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        "success": False,
        "error": "API端点不存在",
        "message": "请检查请求URL是否正确",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """405错误处理"""
    return jsonify({
        "success": False,
        "error": "HTTP方法不允许",
        "message": "请检查请求方法是否正确",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({
        "success": False,
        "error": "服务器内部错误",
        "message": "请稍后重试或联系技术支持",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"启动FreshTrackAI API服务器 - 端口: {port}, 调试模式: {debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)