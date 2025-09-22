# FreshTrackAI 菜谱推荐系统使用指南

## 功能概述

FreshTrackAI菜谱推荐系统为手机应用提供智能菜谱推荐API，基于用户冰箱中的食材情况，使用腾讯混元大模型生成个性化的菜谱推荐和食材管理建议。

## 核心功能

1. **智能菜谱推荐**: 根据冰箱现有食材推荐营养均衡的菜谱
2. **食材管理建议**: 优先推荐使用即将过期的食材，避免浪费
3. **新鲜度分析**: 自动分类食材新鲜程度，提供处理建议
4. **个性化定制**: 支持饮食偏好、过敏信息等个性化设置
5. **定时提醒**: 支持在特定时间(早餐前30分钟、午餐前30分钟等)主动推荐

## 环境配置

### 1. 安装依赖

```bash
# 激活虚拟环境
source freshTrack/bin/activate

# 安装Python依赖
pip install -r requirements.txt
```

### 2. 环境变量配置

创建 `.env` 文件并配置以下环境变量：

```env
# 腾讯云API密钥
TENCENTCLOUD_SECRET_ID=你的Secret_ID
TENCENTCLOUD_SECRET_KEY=你的Secret_Key

# 数据库连接
DATABASE_URL=postgresql://username:password@localhost/freshtrack_db

# Flask配置
FLASK_ENV=development
PORT=5000
```

### 3. 数据库初始化

```bash
# 创建数据库表
python db.py
```

## 启动服务

### 1. 启动API服务器

```bash
python api_server.py
```

服务器将在 `http://localhost:5000` 启动

### 2. 验证服务状态

```bash
# 健康检查
curl http://localhost:5000/api/health

# 查看API信息
curl http://localhost:5000/
```

## API使用说明

### 主要端点

#### 1. 菜谱推荐 API

**端点**: `POST /api/meal-recommendation`

**请求示例**:
```json
{
    "device_id": "mobile_device_001",
    "user_message": "请推荐今天的早餐",
    "meal_type": "breakfast",
    "dietary_preferences": {
        "vegetarian": false,
        "allergies": ["peanuts"],
        "preferred_cuisine": ["chinese", "western"]
    },
    "urgency_level": "medium"
}
```

**响应示例**:
```json
{
    "success": true,
    "timestamp": "2024-09-23T07:30:00Z",
    "device_id": "mobile_device_001",
    "message": "根据您冰箱中的食材，我为您推荐以下营养均衡的早餐...",
    "food_inventory": {
        "total_items": 8,
        "fresh_items": [...],
        "expiring_soon": [...],
        "needs_attention": [...],
        "expired_items": [...]
    },
    "meal_recommendations": [
        {
            "recipe_name": "苹果牛奶燕麦粥",
            "main_ingredients": ["苹果", "牛奶", "燕麦"],
            "difficulty": "简单",
            "cooking_time": "15分钟",
            "nutrition_benefits": "富含纤维和蛋白质",
            "priority_score": 8.5,
            "uses_expiring_items": ["牛奶"],
            "recipe_steps": [...]
        }
    ],
    "food_alerts": {
        "urgent_count": 2,
        "expiring_today": 1,
        "expired_count": 1,
        "recommendations": [...]
    }
}
```

#### 2. 冰箱状态查询

**端点**: `GET /api/fridge-status?device_id=mobile_device_001`

**响应**: 返回当前冰箱中所有食材的统计信息

#### 3. 健康检查

**端点**: `GET /api/health`

**响应**: 返回系统各组件的运行状态

## 手机端集成指南

### 1. 定时推荐实现

```javascript
// 设置定时推荐 (示例：JavaScript)
const scheduleRecommendations = () => {
    // 早餐推荐 - 6:30
    schedule.scheduleJob('30 6 * * *', () => {
        requestMealRecommendation('breakfast');
    });
    
    // 午餐推荐 - 11:30
    schedule.scheduleJob('30 11 * * *', () => {
        requestMealRecommendation('lunch');
    });
    
    // 晚餐推荐 - 17:30
    schedule.scheduleJob('30 17 * * *', () => {
        requestMealRecommendation('dinner');
    });
};

const requestMealRecommendation = async (mealType) => {
    const response = await fetch('http://your-server:5000/api/meal-recommendation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            device_id: getDeviceId(),
            user_message: `请推荐${mealType === 'breakfast' ? '早餐' : mealType === 'lunch' ? '午餐' : '晚餐'}`,
            meal_type: mealType,
            urgency_level: 'medium'
        })
    });
    
    const data = await response.json();
    // 显示推荐结果给用户
    showRecommendation(data);
};
```

### 2. 错误处理

```javascript
const handleApiError = (error, response) => {
    if (response?.status === 503) {
        showMessage('推荐服务暂时不可用，请稍后重试');
    } else if (response?.status >= 400) {
        showMessage('请求参数有误，请检查输入');
    } else {
        showMessage('网络连接异常，请检查网络设置');
    }
};
```

## 测试系统

### 运行完整测试

```bash
python test_meal_recommendation_system.py
```

测试包括：
1. 推荐代理功能测试
2. API端点测试
3. 错误场景测试
4. 数据完整性测试

### 手动测试

```bash
# 1. 设置测试数据
python -c "from test_meal_recommendation_system import setup_test_data; setup_test_data()"

# 2. 启动服务器
python api_server.py

# 3. 测试API调用
curl -X POST http://localhost:5000/api/meal-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test_device",
    "user_message": "请推荐早餐",
    "meal_type": "breakfast"
  }'
```

## 系统架构

```
手机应用端 → API服务器 → 推荐代理 → 腾讯混元模型
     ↓           ↓
    定时推荐    数据库查询
     ↓           ↓
   用户通知    食材数据
```

### 核心组件

1. **api_server.py**: Flask API服务器，处理HTTP请求
2. **meal_recommendation_agent.py**: 推荐代理，封装LLM调用逻辑
3. **db.py**: 数据库操作，管理食材数据
4. **freshtrack_ai_recognizer.py**: 图像识别（冰箱开关触发）
5. **data_processor.py**: 数据处理（冰箱开关触发）

## 部署指南

### 生产环境配置

1. **环境变量**:
```env
FLASK_ENV=production
DATABASE_URL=postgresql://prod_user:password@prod_db:5432/freshtrack_prod
```

2. **使用Gunicorn运行**:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
```

3. **Nginx配置**:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 常见问题

### Q1: API返回"推荐服务暂时不可用"？
A: 检查腾讯云API密钥配置是否正确，网络连接是否正常。

### Q2: 数据库连接失败？
A: 确认DATABASE_URL配置正确，数据库服务正在运行。

### Q3: 推荐结果不准确？
A: 检查食材数据是否完整，可以调整系统提示词优化推荐效果。

### Q4: 如何添加新的饮食偏好？
A: 在dietary_preferences中添加新字段，并在系统提示词中相应调整。

## 技术支持

如遇到问题，请检查：
1. 环境变量配置
2. 数据库连接状态
3. 腾讯云API额度
4. 系统日志输出

更多技术细节请参考源代码注释和API设计文档。