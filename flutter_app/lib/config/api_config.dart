/// API Configuration for Mikha Denagil Mobile App
class ApiConfig {
  // Base URL - Change this to your server URL
  static const String baseUrl = 'http://10.10.255.193:5001'; // Your server IP
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
  
  // Donation Endpoints
  static const String donationTypesEndpoint = '/donations/types';
  static const String donationInitiateEndpoint = '/donations/initiate';
  static const String donationVerifyEndpoint = '/donations/verify';
  static const String donationHistoryEndpoint = '/donations/my-history';
  static const String donationDetailsEndpoint = '/donations';
  
  // MEWACO Endpoints
  static const String mewacoTypesEndpoint = '/mewaco/types';
  static const String mewacoInitiateEndpoint = '/mewaco/initiate';
  static const String mewacoVerifyEndpoint = '/mewaco/verify';
  static const String mewacoContributionsEndpoint = '/mewaco/my-contributions';
  
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

