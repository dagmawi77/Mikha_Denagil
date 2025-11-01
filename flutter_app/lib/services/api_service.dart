import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/api_config.dart';
import '../models/member.dart';
import '../models/post.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String? _token;

  // Get stored token
  Future<String?> getToken() async {
    _token ??= await _storage.read(key: ApiConfig.tokenKey);
    return _token;
  }

  // Save token
  Future<void> saveToken(String token) async {
    _token = token;
    await _storage.write(key: ApiConfig.tokenKey, value: token);
  }

  // Clear token
  Future<void> clearToken() async {
    _token = null;
    await _storage.delete(key: ApiConfig.tokenKey);
  }

  // Get headers with auth token
  Future<Map<String, String>> _getHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // ====================
  // Authentication
  // ====================

  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.loginEndpoint}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      ).timeout(ApiConfig.connectTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        await saveToken(data['token']);
        return data;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Login failed');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  Future<void> logout() async {
    await clearToken();
  }

  Future<bool> changePassword(String oldPassword, String newPassword) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.changePasswordEndpoint}'),
        headers: await _getHeaders(),
        body: jsonEncode({
          'old_password': oldPassword,
          'new_password': newPassword,
        }),
      ).timeout(ApiConfig.connectTimeout);

      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Failed to change password: $e');
    }
  }

  // ====================
  // Member Profile
  // ====================

  Future<Map<String, dynamic>> getProfile() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.profileEndpoint}'),
        headers: await _getHeaders(),
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to load profile');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  // ====================
  // Posts
  // ====================

  Future<List<Post>> getPosts({
    int limit = 20,
    int offset = 0,
    String? type,
  }) async {
    try {
      final queryParams = {
        'limit': limit.toString(),
        'offset': offset.toString(),
        if (type != null && type.isNotEmpty) 'type': type,
      };

      final uri = Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.postsEndpoint}')
          .replace(queryParameters: queryParams);

      final response = await http.get(
        uri,
        headers: await _getHeaders(),
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final posts = (data['posts'] as List)
            .map((json) => Post.fromJson(json))
            .toList();
        return posts;
      } else {
        throw Exception('Failed to load posts');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  Future<Post> getPostDetails(int postId) async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.postsEndpoint}/$postId'),
        headers: await _getHeaders(),
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return Post.fromJson(data['post']);
      } else {
        throw Exception('Failed to load post details');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  Future<bool> markPostAsRead(int postId) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.postsEndpoint}/$postId/mark-read'),
        headers: await _getHeaders(),
      ).timeout(ApiConfig.connectTimeout);

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<Map<String, int>> getPostsStats() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.postsStatsEndpoint}'),
        headers: await _getHeaders(),
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'total_posts': data['total_posts'] as int,
          'read_posts': data['read_posts'] as int,
          'unread_posts': data['unread_posts'] as int,
        };
      } else {
        return {'total_posts': 0, 'read_posts': 0, 'unread_posts': 0};
      }
    } catch (e) {
      return {'total_posts': 0, 'read_posts': 0, 'unread_posts': 0};
    }
  }

  // ====================
  // Utility
  // ====================

  Future<bool> checkHealth() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.healthEndpoint}'),
      ).timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<Map<String, dynamic>> getVersion() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.versionEndpoint}'),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return {};
    } catch (e) {
      return {};
    }
  }
}

