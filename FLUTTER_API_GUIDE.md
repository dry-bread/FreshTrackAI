# FreshTrackAI API Flutter 集成指南

## 目录
1. [API 基础信息](#api-基础信息)
2. [Flutter HTTP 客户端设置](#flutter-http-客户端设置)
3. [API 端点详情](#api-端点详情)
4. [数据模型 (Dart Classes)](#数据模型-dart-classes)
5. [Flutter 服务类示例](#flutter-服务类示例)
6. [错误处理](#错误处理)
7. [使用示例](#使用示例)

## API 基础信息

**基础 URL:** `http://localhost:3000` (开发环境)  
**内容类型:** `application/json`  
**跨域支持:** 已启用 CORS  
**时区:** UTC  

## Flutter HTTP 客户端设置

### pubspec.yaml 依赖
```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  json_annotation: ^4.8.1

dev_dependencies:
  json_serializable: ^6.7.1
  build_runner: ^2.4.7
```

### HTTP 客户端配置
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiConfig {
  static const String baseUrl = 'http://localhost:3000';
  static const Duration timeout = Duration(seconds: 60);
  
  static Map<String, String> get headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };
}
```

## API 端点详情

### 1. 健康检查
```dart
// GET /api/health
Future<HealthResponse> checkHealth() async {
  final response = await http.get(
    Uri.parse('${ApiConfig.baseUrl}/api/health'),
    headers: ApiConfig.headers,
  ).timeout(ApiConfig.timeout);
  
  if (response.statusCode == 200) {
    return HealthResponse.fromJson(json.decode(response.body));
  }
  throw ApiException('健康检查失败', response.statusCode);
}
```

### 2. 服务信息
```dart
// GET /
Future<ServiceInfo> getServiceInfo() async {
  final response = await http.get(
    Uri.parse('${ApiConfig.baseUrl}/'),
    headers: ApiConfig.headers,
  ).timeout(ApiConfig.timeout);
  
  if (response.statusCode == 200) {
    return ServiceInfo.fromJson(json.decode(response.body));
  }
  throw ApiException('获取服务信息失败', response.statusCode);
}
```

### 3. 冰箱状态查询
```dart
// GET /api/fridge-status?device_id={device_id}
Future<FridgeStatusResponse> getFridgeStatus(String deviceId) async {
  final response = await http.get(
    Uri.parse('${ApiConfig.baseUrl}/api/fridge-status?device_id=$deviceId'),
    headers: ApiConfig.headers,
  ).timeout(ApiConfig.timeout);
  
  if (response.statusCode == 200) {
    return FridgeStatusResponse.fromJson(json.decode(response.body));
  }
  throw ApiException('获取冰箱状态失败', response.statusCode);
}
```

### 4. 菜谱推荐 (核心功能)
```dart
// POST /api/meal-recommendation
Future<MealRecommendationResponse> getMealRecommendation(
  MealRecommendationRequest request
) async {
  final response = await http.post(
    Uri.parse('${ApiConfig.baseUrl}/api/meal-recommendation'),
    headers: ApiConfig.headers,
    body: json.encode(request.toJson()),
  ).timeout(ApiConfig.timeout);
  
  if (response.statusCode == 200) {
    return MealRecommendationResponse.fromJson(json.decode(response.body));
  }
  throw ApiException('获取菜谱推荐失败', response.statusCode, response.body);
}
```

## 数据模型 (Dart Classes)

### 基础响应模型
```dart
import 'package:json_annotation/json_annotation.dart';

part 'api_models.g.dart';

@JsonSerializable()
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final String? details;
  
  ApiException(this.message, [this.statusCode, this.details]);
  
  @override
  String toString() => 'ApiException: $message (状态码: $statusCode)';
}
```

### 1. 健康检查响应
```dart
@JsonSerializable()
class HealthResponse {
  final String status;
  final String timestamp;
  final ServiceStatus services;
  
  HealthResponse({
    required this.status,
    required this.timestamp,
    required this.services,
  });
  
  factory HealthResponse.fromJson(Map<String, dynamic> json) =>
      _$HealthResponseFromJson(json);
  Map<String, dynamic> toJson() => _$HealthResponseToJson(this);
}

@JsonSerializable()
class ServiceStatus {
  final String database;
  @JsonKey(name: 'recommendation_agent')
  final String recommendationAgent;
  @JsonKey(name: 'api_server')
  final String apiServer;
  
  ServiceStatus({
    required this.database,
    required this.recommendationAgent,
    required this.apiServer,
  });
  
  factory ServiceStatus.fromJson(Map<String, dynamic> json) =>
      _$ServiceStatusFromJson(json);
  Map<String, dynamic> toJson() => _$ServiceStatusToJson(this);
}
```

### 2. 服务信息响应
```dart
@JsonSerializable()
class ServiceInfo {
  final String name;
  final String version;
  final String description;
  final Map<String, String> endpoints;
  final String timestamp;
  
  ServiceInfo({
    required this.name,
    required this.version,
    required this.description,
    required this.endpoints,
    required this.timestamp,
  });
  
  factory ServiceInfo.fromJson(Map<String, dynamic> json) =>
      _$ServiceInfoFromJson(json);
  Map<String, dynamic> toJson() => _$ServiceInfoToJson(this);
}
```

### 3. 冰箱状态响应
```dart
@JsonSerializable()
class FridgeStatusResponse {
  final bool success;
  final String timestamp;
  @JsonKey(name: 'device_id')
  final String? deviceId;
  @JsonKey(name: 'total_items')
  final int totalItems;
  final Map<String, int>? categories;
  
  FridgeStatusResponse({
    required this.success,
    required this.timestamp,
    this.deviceId,
    required this.totalItems,
    this.categories,
  });
  
  factory FridgeStatusResponse.fromJson(Map<String, dynamic> json) =>
      _$FridgeStatusResponseFromJson(json);
  Map<String, dynamic> toJson() => _$FridgeStatusResponseToJson(this);
}
```

### 4. 菜谱推荐请求
```dart
@JsonSerializable()
class MealRecommendationRequest {
  @JsonKey(name: 'device_id')
  final String deviceId;
  @JsonKey(name: 'user_message')
  final String userMessage;
  @JsonKey(name: 'meal_type')
  final String? mealType;
  @JsonKey(name: 'dietary_preferences')
  final DietaryPreferences? dietaryPreferences;
  @JsonKey(name: 'urgency_level')
  final String? urgencyLevel;
  
  MealRecommendationRequest({
    required this.deviceId,
    required this.userMessage,
    this.mealType,
    this.dietaryPreferences,
    this.urgencyLevel,
  });
  
  factory MealRecommendationRequest.fromJson(Map<String, dynamic> json) =>
      _$MealRecommendationRequestFromJson(json);
  Map<String, dynamic> toJson() => _$MealRecommendationRequestToJson(this);
}

@JsonSerializable()
class DietaryPreferences {
  final bool vegetarian;
  final List<String> allergies;
  @JsonKey(name: 'preferred_cuisine')
  final List<String> preferredCuisine;
  
  DietaryPreferences({
    required this.vegetarian,
    required this.allergies,
    required this.preferredCuisine,
  });
  
  factory DietaryPreferences.fromJson(Map<String, dynamic> json) =>
      _$DietaryPreferencesFromJson(json);
  Map<String, dynamic> toJson() => _$DietaryPreferencesToJson(this);
}
```

### 5. 菜谱推荐响应
```dart
@JsonSerializable()
class MealRecommendationResponse {
  final bool success;
  final String timestamp;
  @JsonKey(name: 'device_id')
  final String deviceId;
  final String? message;
  @JsonKey(name: 'food_inventory')
  final FoodInventory? foodInventory;
  @JsonKey(name: 'meal_recommendations')
  final List<Recipe>? mealRecommendations;
  @JsonKey(name: 'food_alerts')
  final FoodAlerts? foodAlerts;
  @JsonKey(name: 'request_info')
  final RequestInfo? requestInfo;
  @JsonKey(name: 'api_usage')
  final ApiUsage? apiUsage;
  
  MealRecommendationResponse({
    required this.success,
    required this.timestamp,
    required this.deviceId,
    this.message,
    this.foodInventory,
    this.mealRecommendations,
    this.foodAlerts,
    this.requestInfo,
    this.apiUsage,
  });
  
  factory MealRecommendationResponse.fromJson(Map<String, dynamic> json) =>
      _$MealRecommendationResponseFromJson(json);
  Map<String, dynamic> toJson() => _$MealRecommendationResponseToJson(this);
}

@JsonSerializable()
class FoodInventory {
  @JsonKey(name: 'total_items')
  final int totalItems;
  @JsonKey(name: 'fresh_items')
  final List<FoodItem> freshItems;
  @JsonKey(name: 'expiring_soon')
  final List<FoodItem> expiringSoon;
  @JsonKey(name: 'needs_attention')
  final List<FoodItem> needsAttention;
  @JsonKey(name: 'expired_items')
  final List<FoodItem> expiredItems;
  
  FoodInventory({
    required this.totalItems,
    required this.freshItems,
    required this.expiringSoon,
    required this.needsAttention,
    required this.expiredItems,
  });
  
  factory FoodInventory.fromJson(Map<String, dynamic> json) =>
      _$FoodInventoryFromJson(json);
  Map<String, dynamic> toJson() => _$FoodInventoryToJson(this);
}

@JsonSerializable()
class FoodItem {
  final String name;
  final String? category;
  @JsonKey(name: 'expiry_date')
  final String? expiryDate;
  final String? freshness;
  final int? quantity;
  final String? unit;
  
  FoodItem({
    required this.name,
    this.category,
    this.expiryDate,
    this.freshness,
    this.quantity,
    this.unit,
  });
  
  factory FoodItem.fromJson(Map<String, dynamic> json) =>
      _$FoodItemFromJson(json);
  Map<String, dynamic> toJson() => _$FoodItemToJson(this);
}

@JsonSerializable()
class Recipe {
  @JsonKey(name: 'recipe_name')
  final String recipeName;
  @JsonKey(name: 'main_ingredients')
  final List<String> mainIngredients;
  @JsonKey(name: 'cooking_time')
  final String? cookingTime;
  final String? difficulty;
  final String? description;
  @JsonKey(name: 'nutrition_info')
  final Map<String, dynamic>? nutritionInfo;
  
  Recipe({
    required this.recipeName,
    required this.mainIngredients,
    this.cookingTime,
    this.difficulty,
    this.description,
    this.nutritionInfo,
  });
  
  factory Recipe.fromJson(Map<String, dynamic> json) =>
      _$RecipeFromJson(json);
  Map<String, dynamic> toJson() => _$RecipeToJson(this);
}

@JsonSerializable()
class FoodAlerts {
  @JsonKey(name: 'urgent_count')
  final int urgentCount;
  @JsonKey(name: 'expiring_today')
  final int expiringToday;
  @JsonKey(name: 'expired_count')
  final int expiredCount;
  final List<String> recommendations;
  
  FoodAlerts({
    required this.urgentCount,
    required this.expiringToday,
    required this.expiredCount,
    required this.recommendations,
  });
  
  factory FoodAlerts.fromJson(Map<String, dynamic> json) =>
      _$FoodAlertsFromJson(json);
  Map<String, dynamic> toJson() => _$FoodAlertsToJson(this);
}

@JsonSerializable()
class RequestInfo {
  @JsonKey(name: 'meal_type')
  final String? mealType;
  @JsonKey(name: 'urgency_level')
  final String? urgencyLevel;
  @JsonKey(name: 'dietary_preferences')
  final DietaryPreferences? dietaryPreferences;
  @JsonKey(name: 'user_message')
  final String userMessage;
  
  RequestInfo({
    this.mealType,
    this.urgencyLevel,
    this.dietaryPreferences,
    required this.userMessage,
  });
  
  factory RequestInfo.fromJson(Map<String, dynamic> json) =>
      _$RequestInfoFromJson(json);
  Map<String, dynamic> toJson() => _$RequestInfoToJson(this);
}

@JsonSerializable()
class ApiUsage {
  @JsonKey(name: 'tokens_used')
  final int tokensUsed;
  @JsonKey(name: 'response_time')
  final double responseTime;
  
  ApiUsage({
    required this.tokensUsed,
    required this.responseTime,
  });
  
  factory ApiUsage.fromJson(Map<String, dynamic> json) =>
      _$ApiUsageFromJson(json);
  Map<String, dynamic> toJson() => _$ApiUsageToJson(this);
}
```

## Flutter 服务类示例

```dart
class FreshTrackApiService {
  static const String _baseUrl = 'http://localhost:3000';
  final http.Client _client = http.Client();
  
  // 单例模式
  static final FreshTrackApiService _instance = FreshTrackApiService._internal();
  factory FreshTrackApiService() => _instance;
  FreshTrackApiService._internal();
  
  /// 获取菜谱推荐 - 简单版本
  Future<MealRecommendationResponse> getSimpleRecommendation({
    required String deviceId,
    required String userMessage,
  }) async {
    final request = MealRecommendationRequest(
      deviceId: deviceId,
      userMessage: userMessage,
    );
    
    return getMealRecommendation(request);
  }
  
  /// 获取菜谱推荐 - 完整版本
  Future<MealRecommendationResponse> getDetailedRecommendation({
    required String deviceId,
    required String userMessage,
    String? mealType, // 'breakfast', 'lunch', 'dinner'
    bool vegetarian = false,
    List<String> allergies = const [],
    List<String> preferredCuisine = const ['chinese'],
    String urgencyLevel = 'medium', // 'low', 'medium', 'high'
  }) async {
    final request = MealRecommendationRequest(
      deviceId: deviceId,
      userMessage: userMessage,
      mealType: mealType,
      urgencyLevel: urgencyLevel,
      dietaryPreferences: DietaryPreferences(
        vegetarian: vegetarian,
        allergies: allergies,
        preferredCuisine: preferredCuisine,
      ),
    );
    
    return getMealRecommendation(request);
  }
  
  /// 基础API调用方法
  Future<MealRecommendationResponse> getMealRecommendation(
    MealRecommendationRequest request
  ) async {
    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/meal-recommendation'),
        headers: ApiConfig.headers,
        body: json.encode(request.toJson()),
      ).timeout(ApiConfig.timeout);
      
      if (response.statusCode == 200) {
        return MealRecommendationResponse.fromJson(json.decode(response.body));
      }
      
      // 处理错误响应
      final errorData = json.decode(response.body);
      throw ApiException(
        errorData['error'] ?? '未知错误',
        response.statusCode,
        response.body,
      );
      
    } on TimeoutException {
      throw ApiException('请求超时，请检查网络连接');
    } on SocketException {
      throw ApiException('网络连接失败，请检查服务器状态');
    } catch (e) {
      throw ApiException('请求失败: $e');
    }
  }
  
  /// 检查服务健康状态
  Future<bool> isServiceHealthy() async {
    try {
      final response = await checkHealth();
      return response.status == 'healthy';
    } catch (e) {
      return false;
    }
  }
  
  void dispose() {
    _client.close();
  }
}
```

## 错误处理

### 常见错误代码
```dart
class ApiErrorCodes {
  static const int badRequest = 400;      // 请求参数错误
  static const int notFound = 404;        // 端点不存在
  static const int methodNotAllowed = 405; // HTTP方法不允许
  static const int internalError = 500;   // 服务器内部错误
  static const int serviceUnavailable = 503; // 推荐服务不可用
}

class ErrorHandler {
  static String getErrorMessage(ApiException error) {
    switch (error.statusCode) {
      case ApiErrorCodes.badRequest:
        return '请求参数有误，请检查输入内容';
      case ApiErrorCodes.notFound:
        return 'API接口不存在';
      case ApiErrorCodes.methodNotAllowed:
        return '请求方法不正确';
      case ApiErrorCodes.serviceUnavailable:
        return '推荐服务暂时不可用，请稍后重试';
      case ApiErrorCodes.internalError:
        return '服务器出现问题，请稍后重试';
      default:
        return error.message;
    }
  }
}
```

## 使用示例

### 1. 基础用法 - Widget中调用
```dart
class MealRecommendationWidget extends StatefulWidget {
  @override
  _MealRecommendationWidgetState createState() => 
      _MealRecommendationWidgetState();
}

class _MealRecommendationWidgetState extends State<MealRecommendationWidget> {
  final FreshTrackApiService _apiService = FreshTrackApiService();
  bool _loading = false;
  MealRecommendationResponse? _recommendations;
  String? _error;
  
  Future<void> _getRecommendations() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    
    try {
      final response = await _apiService.getSimpleRecommendation(
        deviceId: 'user_device_123',
        userMessage: '请推荐早餐',
      );
      
      setState(() {
        _recommendations = response;
        _loading = false;
      });
      
    } on ApiException catch (e) {
      setState(() {
        _error = ErrorHandler.getErrorMessage(e);
        _loading = false;
      });
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('FreshTrackAI')),
      body: Column(
        children: [
          ElevatedButton(
            onPressed: _loading ? null : _getRecommendations,
            child: _loading 
                ? CircularProgressIndicator() 
                : Text('获取推荐'),
          ),
          
          if (_error != null)
            Container(
              padding: EdgeInsets.all(16),
              color: Colors.red.shade100,
              child: Text(_error!, style: TextStyle(color: Colors.red)),
            ),
            
          if (_recommendations != null)
            Expanded(
              child: _buildRecommendationList(),
            ),
        ],
      ),
    );
  }
  
  Widget _buildRecommendationList() {
    final recipes = _recommendations!.mealRecommendations ?? [];
    
    return ListView.builder(
      itemCount: recipes.length,
      itemBuilder: (context, index) {
        final recipe = recipes[index];
        return Card(
          margin: EdgeInsets.all(8),
          child: ListTile(
            title: Text(recipe.recipeName),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('主要食材: ${recipe.mainIngredients.join(', ')}'),
                if (recipe.cookingTime != null)
                  Text('烹饪时间: ${recipe.cookingTime}'),
                if (recipe.difficulty != null)
                  Text('难度: ${recipe.difficulty}'),
              ],
            ),
          ),
        );
      },
    );
  }
}
```

### 2. 使用Provider进行状态管理
```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class MealRecommendationProvider extends ChangeNotifier {
  final FreshTrackApiService _apiService = FreshTrackApiService();
  
  bool _loading = false;
  bool get loading => _loading;
  
  MealRecommendationResponse? _recommendations;
  MealRecommendationResponse? get recommendations => _recommendations;
  
  String? _error;
  String? get error => _error;
  
  Future<void> getRecommendations({
    required String deviceId,
    required String userMessage,
    String? mealType,
    bool vegetarian = false,
    List<String> allergies = const [],
  }) async {
    _loading = true;
    _error = null;
    notifyListeners();
    
    try {
      _recommendations = await _apiService.getDetailedRecommendation(
        deviceId: deviceId,
        userMessage: userMessage,
        mealType: mealType,
        vegetarian: vegetarian,
        allergies: allergies,
      );
    } on ApiException catch (e) {
      _error = ErrorHandler.getErrorMessage(e);
    }
    
    _loading = false;
    notifyListeners();
  }
}

// 在main.dart中使用
class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => MealRecommendationProvider(),
      child: MaterialApp(
        title: 'FreshTrackAI',
        home: MealRecommendationScreen(),
      ),
    );
  }
}
```

### 3. 生成模型代码命令
```bash
# 在Flutter项目根目录运行
flutter packages pub run build_runner build --delete-conflicting-outputs
```

### 4. 测试用例示例
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';

void main() {
  group('FreshTrackApiService', () {
    late FreshTrackApiService apiService;
    
    setUp(() {
      apiService = FreshTrackApiService();
    });
    
    test('应该成功获取菜谱推荐', () async {
      final response = await apiService.getSimpleRecommendation(
        deviceId: 'test_device',
        userMessage: '推荐早餐',
      );
      
      expect(response.success, isTrue);
      expect(response.deviceId, equals('test_device'));
    });
    
    test('应该正确处理API错误', () async {
      expect(
        () => apiService.getSimpleRecommendation(
          deviceId: 'test_device',
          userMessage: '', // 空消息应该导致错误
        ),
        throwsA(isA<ApiException>()),
      );
    });
  });
}
```

## 注意事项

1. **网络权限**: 在Android的`android/app/src/main/AndroidManifest.xml`中添加:
   ```xml
   <uses-permission android:name="android.permission.INTERNET" />
   ```

2. **iOS配置**: 在iOS的`ios/Runner/Info.plist`中添加网络权限配置

3. **超时处理**: API调用设置了60秒超时，可根据需要调整

4. **错误重试**: 建议在网络错误时实现重试机制

5. **缓存策略**: 考虑对菜谱推荐结果进行本地缓存

6. **生产环境**: 将`baseUrl`修改为实际的服务器地址

这份文档提供了完整的Flutter集成方案，包括所有必要的数据模型、API调用方法和错误处理。你可以直接复制这些代码到Flutter项目中使用。