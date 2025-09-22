# -*- coding: utf-8 -*-
"""
FreshTrackAI - 菜谱推荐代理模块
基于腾讯混元大模型为用户提供个性化菜谱推荐
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MealRecommendationAgent:
    """FreshTrack菜谱推荐代理 - 基于腾讯混元大模型"""
    
    def __init__(self, secret_id: Optional[str] = None, secret_key: Optional[str] = None):
        """
        初始化推荐代理
        
        Args:
            secret_id: 腾讯云Secret ID，如果不提供则从环境变量获取
            secret_key: 腾讯云Secret Key，如果不提供则从环境变量获取
        """
        self.secret_id = secret_id or os.getenv("TENCENTCLOUD_SECRET_ID")
        self.secret_key = secret_key or os.getenv("TENCENTCLOUD_SECRET_KEY")
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("请设置腾讯云API密钥环境变量或传入参数")
        
        # 初始化腾讯云客户端
        try:
            cred = credential.Credential(self.secret_id, self.secret_key)
            httpProfile = HttpProfile()
            httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
            httpProfile.reqTimeout = 120
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile
            self.client = hunyuan_client.HunyuanClient(cred, "", clientProfile)
            logger.info("腾讯混元客户端初始化成功")
        except Exception as e:
            logger.error(f"腾讯混元客户端初始化失败: {e}")
            raise
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """
你是FreshTrackAI智能冰箱管理系统的专业营养师和菜谱推荐专家。你的任务是根据用户冰箱中的食材情况，提供个性化的菜谱推荐和食材管理建议。

**核心原则:**
1. 优先推荐使用即将过期的食材，避免浪费
2. 确保营养均衡搭配
3. 考虑制作难度和时间成本
4. 提供实用的食材处理建议

**返回JSON格式要求:**
```json
{
    "success": true,
    "message": "友好的回复消息，体现专业性和关怀",
    "food_inventory": {
        "total_items": 数字,
        "fresh_items": [
            {
                "id": 数字,
                "name": "食材名称",
                "category": "食材类别",
                "subcategory": "子类别",
                "brand": "品牌",
                "quantity": "数量描述", 
                "freshness": "good/fair/poor",
                "days_in_fridge": 数字,
                "expiry_estimate": "保质期估计",
                "put_in_time": "ISO时间格式"
            }
        ],
        "expiring_soon": [
            {
                "id": 数字,
                "name": "食材名称",
                "category": "食材类别",
                "days_remaining": 数字,
                "urgency": "medium/high",
                "put_in_time": "ISO时间格式"
            }
        ],
        "needs_attention": [
            {
                "id": 数字,
                "name": "食材名称", 
                "category": "食材类别",
                "freshness": "fair/poor",
                "days_remaining": 数字,
                "urgency": "high",
                "put_in_time": "ISO时间格式"
            }
        ],
        "expired_items": [
            {
                "id": 数字,
                "name": "食材名称",
                "category": "食材类别", 
                "days_expired": 数字,
                "action_needed": "清理"
            }
        ]
    },
    "meal_recommendations": [
        {
            "recipe_name": "菜谱名称",
            "main_ingredients": ["主要食材1", "主要食材2"],
            "difficulty": "简单/中等/复杂",
            "cooking_time": "制作时间",
            "nutrition_benefits": "营养价值说明",
            "priority_score": 数字(1-10),
            "uses_expiring_items": ["即将过期的食材"],
            "recipe_steps": [
                "步骤1",
                "步骤2",
                "步骤3"
            ]
        }
    ],
    "food_alerts": {
        "urgent_count": 数字,
        "expiring_today": 数字,
        "expired_count": 数字,
        "recommendations": [
            "具体建议1",
            "具体建议2"
        ]
    }
}
```

**食材新鲜度判断标准:**
- fresh: 放入时间 < 3天，新鲜度良好
- expiring_soon: 3-7天，需要优先使用
- needs_attention: 7-10天或新鲜度一般，需要尽快处理
- expired: >10天或新鲜度差，建议清理

**推荐优先级:**
1. 使用即将过期食材的菜谱得分最高
2. 营养均衡的搭配加分
3. 制作简单的菜谱适合忙碌时段
4. 能同时消耗多种食材的菜谱优先

用中文回答，语气专业且温馨。
"""

    def analyze_food_freshness(self, food_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        分析食材新鲜度并分类
        
        Args:
            food_items: 食材列表
            
        Returns:
            Dict: 按新鲜度分类的食材
        """
        now = datetime.now(timezone.utc)
        categorized_foods = {
            "fresh_items": [],
            "expiring_soon": [],
            "needs_attention": [],
            "expired_items": []
        }
        
        for item in food_items:
            try:
                # 计算放入时间差
                put_in_time = datetime.fromisoformat(item.get('put_in_time', '').replace('Z', '+00:00'))
                days_in_fridge = (now - put_in_time).days
                
                # 获取新鲜度状态
                freshness = item.get('freshness', 'good')
                
                # 分类逻辑
                if days_in_fridge >= 10 or freshness == 'poor':
                    categorized_foods["expired_items"].append({
                        "id": item.get('id'),
                        "name": item.get('name'),
                        "category": item.get('category'),
                        "days_expired": max(0, days_in_fridge - 7),
                        "action_needed": "清理"
                    })
                elif days_in_fridge >= 7 or freshness == 'fair':
                    categorized_foods["needs_attention"].append({
                        "id": item.get('id'),
                        "name": item.get('name'),
                        "category": item.get('category'),
                        "freshness": freshness,
                        "days_remaining": max(0, 10 - days_in_fridge),
                        "urgency": "high",
                        "put_in_time": item.get('put_in_time')
                    })
                elif days_in_fridge >= 3:
                    categorized_foods["expiring_soon"].append({
                        "id": item.get('id'),
                        "name": item.get('name'),
                        "category": item.get('category'),
                        "days_remaining": max(0, 7 - days_in_fridge),
                        "urgency": "medium" if days_in_fridge < 6 else "high",
                        "put_in_time": item.get('put_in_time')
                    })
                else:
                    categorized_foods["fresh_items"].append({
                        "id": item.get('id'),
                        "name": item.get('name'),
                        "category": item.get('category'),
                        "subcategory": item.get('subcategory'),
                        "brand": item.get('brand'),
                        "quantity": item.get('item_amount_desc', '未知数量'),
                        "freshness": freshness,
                        "days_in_fridge": days_in_fridge,
                        "expiry_estimate": item.get('expiry_estimate'),
                        "put_in_time": item.get('put_in_time')
                    })
            except Exception as e:
                logger.warning(f"处理食材 {item.get('name')} 时出错: {e}")
                # 默认放入fresh_items
                categorized_foods["fresh_items"].append(item)
        
        return categorized_foods

    def recommend_meals(
        self,
        food_items: List[Dict[str, Any]],
        user_message: str,
        device_id: Optional[str] = None,
        meal_type: Optional[str] = None,
        dietary_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        推荐菜谱
        
        Args:
            food_items: 冰箱中的食材列表
            user_message: 用户消息
            device_id: 设备ID
            meal_type: 餐次类型 (breakfast/lunch/dinner)
            dietary_preferences: 饮食偏好
            
        Returns:
            Dict: 推荐结果
        """
        try:
            logger.info(f"开始生成菜谱推荐，设备ID: {device_id}")
            
            # 分析食材新鲜度
            categorized_foods = self.analyze_food_freshness(food_items)
            
            # 构建食材上下文
            food_context = self._build_food_context(food_items, categorized_foods)
            
            # 构建用户偏好上下文
            preference_context = self._build_preference_context(meal_type, dietary_preferences)
            
            # 创建请求对象
            req = models.ChatCompletionsRequest()
            
            # 构建完整的用户提示
            user_prompt = f"""
当前用户请求: {user_message}

冰箱食材情况:
{food_context}

用户偏好:
{preference_context}

请根据以上信息，提供专业的菜谱推荐和食材管理建议。
"""
            
            # 构建请求参数
            params = {
                "Model": "hunyuan-lite",  # 使用hunyuan-lite模型
                "Messages": [
                    {
                        "Role": "system",
                        "Content": self.get_system_prompt()
                    },
                    {
                        "Role": "user",
                        "Content": user_prompt
                    }
                ],
                "Stream": False,
                "Temperature": 0.3,  # 稍微降低随机性，保持创意
                "TopP": 0.9
            }
            
            req.from_json_string(json.dumps(params))
            
            # 发送请求
            resp = self.client.ChatCompletions(req)
            
            # 处理响应
            if hasattr(resp, 'Choices') and resp.Choices: # pyright: ignore[reportAttributeAccessIssue]
                content = resp.Choices[0].Message.Content # type: ignore
                logger.info(f"收到API响应，长度: {len(content)} 字符")
                
                # 解析JSON响应
                parsed_result = self._parse_response(content, categorized_foods)
                
                # 添加元数据
                parsed_result.update({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "device_id": device_id,
                    "model": "hunyuan-lite",
                    "api_usage": {
                        "prompt_tokens": getattr(resp.Usage, 'PromptTokens', 0) if hasattr(resp, 'Usage') else 0, # pyright: ignore[reportAttributeAccessIssue]
                        "completion_tokens": getattr(resp.Usage, 'CompletionTokens', 0) if hasattr(resp, 'Usage') else 0, # pyright: ignore[reportAttributeAccessIssue]
                        "total_tokens": getattr(resp.Usage, 'TotalTokens', 0) if hasattr(resp, 'Usage') else 0 # pyright: ignore[reportAttributeAccessIssue]
                    }
                })
                
                return parsed_result
            
            else:
                logger.error("API响应格式异常")
                return self._create_fallback_response(categorized_foods, device_id, "API响应格式异常")
                
        except TencentCloudSDKException as e:
            logger.error(f"腾讯云API错误: {e.message}")
            return self._create_fallback_response(categorized_foods if 'categorized_foods' in locals() else {}, device_id, f"腾讯云API错误: {e.message}")
        except Exception as e:
            logger.error(f"推荐过程异常: {str(e)}")
            return self._create_fallback_response(categorized_foods if 'categorized_foods' in locals() else {}, device_id, f"推荐过程异常: {str(e)}")

    def _build_food_context(self, food_items: List[Dict[str, Any]], categorized_foods: Dict[str, List[Dict[str, Any]]]) -> str:
        """构建食材上下文描述"""
        context = f"总共有 {len(food_items)} 种食材:\n\n"
        
        if categorized_foods["fresh_items"]:
            context += "新鲜食材:\n"
            for item in categorized_foods["fresh_items"]:
                context += f"- {item['name']} ({item['category']}) - {item.get('quantity', '未知数量')}\n"
            context += "\n"
        
        if categorized_foods["expiring_soon"]:
            context += "即将过期食材 (优先使用):\n"
            for item in categorized_foods["expiring_soon"]:
                context += f"- {item['name']} ({item['category']}) - 剩余 {item['days_remaining']} 天\n"
            context += "\n"
        
        if categorized_foods["needs_attention"]:
            context += "需要注意的食材 (急需处理):\n"
            for item in categorized_foods["needs_attention"]:
                context += f"- {item['name']} ({item['category']}) - 剩余 {item['days_remaining']} 天\n"
            context += "\n"
        
        if categorized_foods["expired_items"]:
            context += "已过期食材 (建议清理):\n"
            for item in categorized_foods["expired_items"]:
                context += f"- {item['name']} ({item['category']}) - 过期 {item['days_expired']} 天\n"
        
        return context

    def _build_preference_context(self, meal_type: Optional[str] = None, dietary_preferences: Optional[Dict[str, Any]] = None) -> str:
        """构建用户偏好上下文"""
        context = ""
        
        if meal_type:
            context += f"餐次类型: {meal_type}\n"
        
        if dietary_preferences:
            if dietary_preferences.get('vegetarian'):
                context += "饮食偏好: 素食\n"
            if dietary_preferences.get('allergies'):
                context += f"过敏信息: {', '.join(dietary_preferences['allergies'])}\n"
            if dietary_preferences.get('preferred_cuisine'):
                context += f"偏好菜系: {', '.join(dietary_preferences['preferred_cuisine'])}\n"
        
        return context or "无特殊偏好"

    def _parse_response(self, content: str, categorized_foods: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """解析API响应内容"""
        try:
            # 查找JSON块
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                parsed_data = json.loads(json_content)
                
                # 验证和补充数据
                if isinstance(parsed_data, dict):
                    # 确保包含必要的字段
                    parsed_data.setdefault('success', True)
                    parsed_data.setdefault('food_inventory', categorized_foods)
                    parsed_data.setdefault('meal_recommendations', [])
                    parsed_data.setdefault('food_alerts', {
                        "urgent_count": len(categorized_foods.get("needs_attention", [])),
                        "expiring_today": len([item for item in categorized_foods.get("expiring_soon", []) if item.get("days_remaining", 0) <= 1]),
                        "expired_count": len(categorized_foods.get("expired_items", [])),
                        "recommendations": []
                    })
                    
                    # 添加总数
                    if 'food_inventory' in parsed_data:
                        total_items = sum(len(items) for items in categorized_foods.values())
                        parsed_data['food_inventory']['total_items'] = total_items
                    
                    return parsed_data
            
            # 如果无法解析为JSON，创建默认响应
            logger.warning("无法解析为标准JSON，使用默认格式")
            return self._create_default_response(categorized_foods, content)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return self._create_default_response(categorized_foods, content, f"JSON解析错误: {str(e)}")
        except Exception as e:
            logger.error(f"响应解析异常: {e}")
            return self._create_default_response(categorized_foods, content, f"响应解析异常: {str(e)}")

    def _create_fallback_response(self, categorized_foods: Dict[str, List[Dict[str, Any]]], device_id: Optional[str], error_msg: str) -> Dict[str, Any]:
        """创建失败时的备用响应"""
        return {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": device_id,
            "food_inventory": categorized_foods,
            "meal_recommendations": [],
            "food_alerts": {
                "urgent_count": len(categorized_foods.get("needs_attention", [])),
                "expiring_today": len([item for item in categorized_foods.get("expiring_soon", []) if item.get("days_remaining", 0) <= 1]),
                "expired_count": len(categorized_foods.get("expired_items", [])),
                "recommendations": ["系统暂时无法提供推荐，请稍后重试"]
            },
            "api_usage": None
        }

    def _create_default_response(self, categorized_foods: Dict[str, List[Dict[str, Any]]], raw_content: str, error_msg: Optional[str] = None) -> Dict[str, Any]:
        """创建默认格式响应"""
        total_items = sum(len(items) for items in categorized_foods.values())
        
        return {
            "success": True,
            "message": raw_content if not error_msg else "系统解析异常，但已获取食材信息",
            "food_inventory": {
                "total_items": total_items,
                **categorized_foods
            },
            "meal_recommendations": [],
            "food_alerts": {
                "urgent_count": len(categorized_foods.get("needs_attention", [])),
                "expiring_today": len([item for item in categorized_foods.get("expiring_soon", []) if item.get("days_remaining", 0) <= 1]),
                "expired_count": len(categorized_foods.get("expired_items", [])),
                "recommendations": ["请检查即将过期和需要注意的食材"]
            },
            "raw_content": raw_content,
            "parsing_error": error_msg
        }


# 使用示例
if __name__ == "__main__":
    # 初始化推荐代理
    agent = MealRecommendationAgent()
    
    # 模拟食材数据
    test_foods = [
        {
            "id": 1,
            "name": "牛奶",
            "category": "乳制品",
            "subcategory": "牛奶",
            "brand": "伊利",
            "item_amount_desc": "1盒",
            "freshness": "good",
            "expiry_estimate": "7天",
            "put_in_time": "2024-09-18T10:00:00Z"
        },
        {
            "id": 2,
            "name": "苹果",
            "category": "水果类",
            "subcategory": "苹果",
            "brand": "红富士",
            "item_amount_desc": "3个",
            "freshness": "good",
            "expiry_estimate": "10天",
            "put_in_time": "2024-09-21T15:00:00Z"
        }
    ]
    
    # 生成推荐
    result = agent.recommend_meals(
        food_items=test_foods,
        user_message="请推荐今天的早餐",
        device_id="test_device_001",
        meal_type="breakfast"
    )
    
    print("\n菜谱推荐结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))