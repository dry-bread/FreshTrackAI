# -*- coding: utf-8 -*-
"""
FreshTrackAI - 腾讯混元大模型集成模块
用于冰箱物品识别和分析
"""

import os
import json
import types
import logging
from typing import Dict, Any, List, Optional
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FreshTrackItemRecognizer:
    """FreshTrack冰箱物品识别器 - 基于腾讯混元大模型"""
    
    def __init__(self, secret_id: Optional[str] = None, secret_key: Optional[str] = None):
        """
        初始化识别器
        
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
            httpProfile.reqTimeout = 120  # 设置超时时间为120秒（原为60秒）
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
你是FreshTrackAI智能冰箱管理系统的物品识别专家。请仔细分析冰箱图片中的所有物品，并以JSON格式返回详细结果。

**返回JSON格式要求：**
```json
{
    "success": true,
    "items": [
        {
            "name": "具体物品名称",
            "category": "食品类别",
            "subcategory": "子类别",
            "brand": "品牌名称(如可识别)",
            "confidence": 0.95,
            "position": {
                "x": "图片的x坐标",
                "y": "图片的y坐标",
                "width": "物品宽度",
                "height": "物品高度"
            },
            "quantity": 1,
            "estimated_size": "large/medium/small",
            "freshness": "good/fair/poor",
            "additional_info": {
                "color": "颜色描述",
                "packaging": "包装情况",
                "expiry_estimate": "在冰箱保鲜层中的保质期估计"
            }
        }
    ],
}
```

**识别要求：**
1. 准确识别所有可见物品，包括部分遮挡的物品
2. 置信度范围0-1，反映识别的确定程度
3. 详细描述物品在冰箱中的位置
4. 评估物品的新鲜程度和大小
5. 尽可能识别品牌和包装信息
6. 对于相似物品要明确区分
7. 用中文回答，专业术语准确

**食品类别参考：**
- 蔬菜类：叶菜、根茎菜、茄果类、豆类等
- 水果类：柑橘类、浆果类、热带水果等  
- 肉类：猪肉、牛肉、鸡肉、鱼类等
- 乳制品：牛奶、酸奶、奶酪等
- 调料：酱料、香料、油类、醋类等
- 饮料：果汁、碳酸饮料、茶饮等
- 主食：米面制品、面包等
- 零食：坚果、饼干、糖果等
"""

    def recognize_fridge_items(self, image_url: str, device_id: str = None) -> Dict[str, Any]: # type: ignore
        """
        识别冰箱中的物品
        
        Args: 
            image_url: 图片URL
            device_id: 设备ID（可选）
            
        Returns:
            Dict: 识别结果
        """
        try:
            logger.info(f"开始识别冰箱物品，图片URL: {image_url}")
            
            # 创建请求对象
            req = models.ChatCompletionsRequest()
            
            # 构建请求参数
            params = {
                "Model": "hunyuan-t1-vision",
                "Messages": [
                    {
                        "Role": "system",
                        "Content": self.get_system_prompt()
                    },
                    {
                        "Role": "user",
                        "Contents": [
                            {
                                "Type": "text", 
                                "Text": f"请识别这张冰箱图片中的所有物品。设备ID: {device_id or 'unknown'}"
                            },
                            {
                                "Type": "image_url", 
                                "ImageUrl": {"Url": image_url}
                            }
                        ]
                    }
                ],
                "Stream": False,
                "Temperature": 0.1,  # 降低随机性
                "TopP": 0.9,
                "ResponseFormat": "json"  # 强制API返回JSON格式
            }
            
            req.from_json_string(json.dumps(params))
            
            # 发送请求
            resp = self.client.ChatCompletions(req)
            
            # 处理响应
            if hasattr(resp, 'Choices') and resp.Choices: # pyright: ignore[reportAttributeAccessIssue]
                content = resp.Choices[0].Message.Content # type: ignore
                logger.info(f"收到API响应，长度: {len(content)} 字符")
                
                # 解析JSON响应
                parsed_result = self._parse_response(content)
                
                # 添加元数据
                parsed_result.update({
                    "device_id": device_id,
                    "image_url": image_url,
                    "model": "hunyuan-t1-vision",
                    "api_usage": {
                        "prompt_tokens": getattr(resp.Usage, 'PromptTokens', 0) if hasattr(resp, 'Usage') else 0, # pyright: ignore[reportAttributeAccessIssue]
                        "completion_tokens": getattr(resp.Usage, 'CompletionTokens', 0) if hasattr(resp, 'Usage') else 0, # pyright: ignore[reportAttributeAccessIssue]
                        "total_tokens": getattr(resp.Usage, 'TotalTokens', 0) if hasattr(resp, 'Usage') else 0 # pyright: ignore[reportAttributeAccessIssue]
                    }
                })
                
                return parsed_result
            
            else:
                logger.error("API响应格式异常")
                return {
                    "success": False,
                    "error": "API响应格式异常",
                    "items": [],
                    "device_id": device_id
                }
                
        except TencentCloudSDKException as e:
            logger.error(f"腾讯云API错误: {e.message}")
            return {
                "success": False,
                "error": f"腾讯云API错误: {e.message}",
                "error_code": getattr(e, 'code', 'Unknown'),
                "items": [],
                "device_id": device_id
            }
        except Exception as e:
            logger.error(f"识别过程异常: {str(e)}")
            return {
                "success": False,
                "error": f"识别过程异常: {str(e)}",
                "items": [],
                "device_id": device_id
            }
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """
        解析API响应内容
        
        Args:
            content: API返回的文本内容
            
        Returns:
            Dict: 解析后的结构化数据
        """
        try:
            # 查找JSON块
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                parsed_data = json.loads(json_content)
                
                # 验证必要字段
                if isinstance(parsed_data, dict) and 'items' in parsed_data:
                    parsed_data['success'] = True
                    parsed_data['raw_content'] = content
                    return parsed_data
            
            # 如果无法解析为JSON，尝试从文本中提取信息
            logger.warning("无法解析为标准JSON，尝试文本解析")
            return {
                "success": False,
                "error": "响应格式不是有效JSON",
                "raw_content": content,
                "items": [],
                "parsing_attempted": True
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return {
                "success": False,
                "error": f"JSON解析错误: {str(e)}",
                "raw_content": content,
                "items": []
            }
        except Exception as e:
            logger.error(f"响应解析异常: {e}")
            return {
                "success": False,
                "error": f"响应解析异常: {str(e)}",
                "raw_content": content,
                "items": []
            }

# 使用示例
if __name__ == "__main__":
    # 初始化识别器
    recognizer = FreshTrackItemRecognizer()
    
    # 识别示例
    test_image_url = "https://img0.baidu.com/it/u=2574745022,655714543&fm=253&fmt=auto&app=138&f=JPEG?w=200&h=300"
    result = recognizer.recognize_fridge_items(test_image_url, "test_device_001")
    
    print("\n识别结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))