# FreshTrackAI 手机端API数据结构设计

## 1. API请求格式

### 请求端点
```
POST /api/meal-recommendation
```

### 请求体格式
```json
{
    "device_id": "手机设备ID",
    "user_message": "请推荐今天的早餐",
    "meal_type": "breakfast|lunch|dinner",  // 可选：指定餐次类型
    "dietary_preferences": {               // 可选：饮食偏好
        "vegetarian": false,
        "allergies": ["peanuts", "shellfish"],
        "preferred_cuisine": ["chinese", "western"]
    },
    "urgency_level": "high|medium|low"     // 可选：推荐优先级
}
```

## 2. API响应格式

### 成功响应
```json
{
    "success": true,
    "timestamp": "2024-09-23T07:30:00Z",
    "device_id": "手机设备ID",
    "message": "LLM生成的回复消息",
    "food_inventory": {
        "total_items": 15,
        "fresh_items": [
            {
                "id": 1,
                "name": "新鲜苹果",
                "category": "水果类",
                "subcategory": "苹果",
                "brand": "红富士",
                "quantity": "3个",
                "freshness": "good",
                "days_in_fridge": 2,
                "expiry_estimate": "7天",
                "put_in_time": "2024-09-21T10:00:00Z"
            }
        ],
        "expiring_soon": [
            {
                "id": 2,
                "name": "牛奶",
                "category": "乳制品",
                "days_remaining": 2,
                "urgency": "medium",
                "put_in_time": "2024-09-18T15:30:00Z"
            }
        ],
        "needs_attention": [
            {
                "id": 3,
                "name": "青菜",
                "category": "蔬菜类",
                "freshness": "fair",
                "days_remaining": 1,
                "urgency": "high",
                "put_in_time": "2024-09-15T09:00:00Z"
            }
        ],
        "expired_items": [
            {
                "id": 4,
                "name": "过期酸奶",
                "category": "乳制品",
                "days_expired": 3,
                "action_needed": "清理"
            }
        ]
    },
    "meal_recommendations": [
        {
            "recipe_name": "苹果牛奶燕麦粥",
            "main_ingredients": ["苹果", "牛奶", "燕麦"],
            "difficulty": "简单",
            "cooking_time": "15分钟",
            "nutrition_benefits": "富含纤维和蛋白质，适合早餐",
            "priority_score": 8.5,
            "uses_expiring_items": ["牛奶"],
            "recipe_steps": [
                "将燕麦煮熟",
                "加入牛奶煮至浓稠",
                "切苹果块加入",
                "稍微煮制即可"
            ]
        }
    ],
    "food_alerts": {
        "urgent_count": 2,
        "expiring_today": 1,
        "expired_count": 1,
        "recommendations": [
            "建议优先使用即将过期的牛奶制作料理",
            "青菜需要尽快食用，建议今天处理",
            "酸奶已过期，请及时清理"
        ]
    },
    "api_usage": {
        "model": "hunyuan-t1",
        "prompt_tokens": 1250,
        "completion_tokens": 850,
        "total_tokens": 2100
    }
}
```

### 错误响应
```json
{
    "success": false,
    "error": "错误描述",
    "error_code": "ERROR_CODE",
    "timestamp": "2024-09-23T07:30:00Z",
    "device_id": "手机设备ID",
    "food_inventory": null,
    "meal_recommendations": [],
    "api_usage": null
}
```

## 3. 食物新鲜度分类逻辑

### 新鲜度等级
- **fresh (新鲜)**: 放入时间 < 3天，freshness = "good"
- **expiring_soon (即将过期)**: 3天 <= 放入时间 < 7天，freshness = "good/fair" 
- **needs_attention (需要注意)**: 7天 <= 放入时间 < 10天，或 freshness = "fair"
- **expired (已过期)**: 放入时间 >= 10天，或 freshness = "poor"

### 紧急程度
- **high**: 1天内需要处理
- **medium**: 2-3天内需要处理  
- **low**: 一周内处理即可

## 4. 推荐算法优先级

1. **即将过期食物优先**: 优先推荐使用即将过期的食材
2. **营养均衡**: 确保推荐的菜谱营养搭配合理
3. **制作难度**: 根据时间和场景推荐合适难度的菜谱
4. **食材利用率**: 优先推荐能同时使用多种现有食材的菜谱
5. **用户偏好**: 考虑用户的饮食偏好和过敏信息