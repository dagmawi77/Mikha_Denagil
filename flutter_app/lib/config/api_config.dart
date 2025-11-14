/// API Configuration for Mikha Denagil Mobile App
class ApiConfig {
  // Base URL - Change this to your server URL
  static const String baseUrl = 'http://192.168.1.10:5001'; // Your server IP
  static const String apiVersion = '/api/v1';
  
  // Full API base URL
  static String get apiBaseUrl => '$baseUrl$apiVersion';
  
  // Endpoints
  static const String loginEndpoint = '/auth/login';
  static const String changePasswordEndpoint = '/auth/change-password';
  static const String profileEndpoint = '/member/profile';
  static const String postsEndpoint = '/posts';
  static const String postsStatsEndpoint = '/posts/stats';
  static const String healthEndpoint = '/health';
  static const String versionEndpoint = '/version';
  
  // Timeouts
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  
  // Storage Keys
  static const String tokenKey = 'auth_token';
  static const String userDataKey = 'user_data';
  static const String languageKey = 'app_language';
  
  // App Settings
  static const int postsPerPage = 20;
  static const int maxRetries = 3;
}

