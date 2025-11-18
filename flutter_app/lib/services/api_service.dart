import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/api_config.dart';
import '../models/member.dart';
import '../models/post.dart';
import '../models/study.dart';
import '../models/donation_type.dart';
import '../models/donation.dart';
import '../models/mewaco_type.dart';
import '../models/mewaco_contribution.dart';

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
  // Study Materials
  // ====================

  Future<Map<String, dynamic>> getStudies({
    int limit = 20,
    int offset = 0,
    int? categoryId,
  }) async {
    try {
      final headers = await _getHeaders();
      String url = '${ApiConfig.apiBaseUrl}/studies?limit=$limit&offset=$offset';
      if (categoryId != null) {
        url += '&category_id=$categoryId';
      }

      final response = await http.get(
        Uri.parse(url),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'studies': (data['studies'] as List)
              .map((json) => Study.fromJson(json))
              .toList(),
          'count': data['count'],
        };
      } else {
        return {'success': false, 'error': 'Failed to load studies'};
      }
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>> getStudyDetails(int studyId) async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}/studies/$studyId'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'study': Study.fromJson(data['study']),
        };
      } else {
        return {'success': false, 'error': 'Study not found'};
      }
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>> getStudyCategories() async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}/study-categories'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'categories': (data['categories'] as List)
              .map((json) => StudyCategory.fromJson(json))
              .toList(),
        };
      } else {
        return {'success': false, 'error': 'Failed to load categories'};
      }
    } catch (e) {
      return {'success': false, 'error': e.toString()};
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

  // ====================
  // Donations
  // ====================

  /// Get all active donation types
  Future<List<DonationType>> getDonationTypes() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.donationTypesEndpoint}'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          return (data['data'] as List)
              .map((json) => DonationType.fromJson(json))
              .toList();
        }
        return [];
      } else {
        throw Exception('Failed to load donation types');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  /// Initiate a donation payment
  Future<Map<String, dynamic>> initiateDonation({
    required int donationTypeId,
    required double amount,
    String? donorName,
    String? christianName,
    String? donorEmail,
    String? donorPhone,
    bool isAnonymous = false,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.donationInitiateEndpoint}'),
        headers: await _getHeaders(),
        body: jsonEncode({
          'donation_type_id': donationTypeId,
          'amount': amount,
          if (donorName != null && donorName.isNotEmpty) 'donor_name': donorName,
          if (christianName != null && christianName.isNotEmpty) 'christian_name': christianName,
          if (donorEmail != null && donorEmail.isNotEmpty) 'donor_email': donorEmail,
          if (donorPhone != null && donorPhone.isNotEmpty) 'donor_phone': donorPhone,
          'is_anonymous': isAnonymous,
        }),
      ).timeout(ApiConfig.connectTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && data['success'] == true) {
        return data;
      } else {
        throw Exception(data['error'] ?? 'Failed to initiate donation');
      }
    } catch (e) {
      throw Exception('Donation error: $e');
    }
  }

  /// Verify donation payment status
  Future<Map<String, dynamic>> verifyDonation(String txRef) async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.donationVerifyEndpoint}/$txRef'),
        headers: await _getHeaders(),
      ).timeout(ApiConfig.connectTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && data['success'] == true) {
        return data;
      } else {
        throw Exception(data['error'] ?? 'Failed to verify donation');
      }
    } catch (e) {
      throw Exception('Verification error: $e');
    }
  }

  /// Get donation history for logged-in member
  Future<List<Donation>> getDonationHistory({
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final queryParams = {
        'limit': limit.toString(),
        'offset': offset.toString(),
      };

      final uri = Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.donationHistoryEndpoint}')
          .replace(queryParameters: queryParams);

      final response = await http.get(
        uri,
        headers: await _getHeaders(),
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          return (data['data'] as List)
              .map((json) => Donation.fromJson(json))
              .toList();
        }
        return [];
      } else {
        throw Exception('Failed to load donation history');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  /// Get specific donation details
  Future<Donation> getDonationDetails(int donationId) async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.donationDetailsEndpoint}/$donationId'),
        headers: await _getHeaders(),
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          return Donation.fromJson(data['data']);
        }
        throw Exception('Donation not found');
      } else {
        throw Exception('Failed to load donation details');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  // ====================
  // MEWACO Contributions
  // ====================

  /// Get all active MEWACO types
  Future<List<MewacoType>> getMewacoTypes() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.mewacoTypesEndpoint}'),
        headers: await _getHeaders(),
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          return (data['data'] as List)
              .map((json) => MewacoType.fromJson(json))
              .toList();
        }
        return [];
      } else {
        throw Exception('Failed to load MEWACO types');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  /// Initiate a MEWACO contribution payment
  Future<Map<String, dynamic>> initiateMewacoPayment({
    required int mewacoTypeId,
    required double amount,
    String? contributionDate,
    String? notes,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.mewacoInitiateEndpoint}'),
        headers: await _getHeaders(),
        body: jsonEncode({
          'mewaco_type_id': mewacoTypeId,
          'amount': amount,
          if (contributionDate != null && contributionDate.isNotEmpty) 'contribution_date': contributionDate,
          if (notes != null && notes.isNotEmpty) 'notes': notes,
        }),
      ).timeout(ApiConfig.connectTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && data['success'] == true) {
        return data;
      } else {
        throw Exception(data['error'] ?? 'Failed to initiate MEWACO payment');
      }
    } catch (e) {
      throw Exception('MEWACO payment error: $e');
    }
  }

  /// Verify MEWACO payment status
  Future<Map<String, dynamic>> verifyMewacoPayment(String txRef) async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.mewacoVerifyEndpoint}/$txRef'),
        headers: await _getHeaders(),
      ).timeout(ApiConfig.connectTimeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && data['success'] == true) {
        return data;
      } else {
        throw Exception(data['error'] ?? 'Failed to verify MEWACO payment');
      }
    } catch (e) {
      throw Exception('Verification error: $e');
    }
  }

  /// Get MEWACO contribution history for logged-in member
  Future<List<MewacoContribution>> getMewacoContributions({
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final queryParams = {
        'limit': limit.toString(),
        'offset': offset.toString(),
      };

      final uri = Uri.parse('${ApiConfig.apiBaseUrl}${ApiConfig.mewacoContributionsEndpoint}')
          .replace(queryParameters: queryParams);

      final response = await http.get(
        uri,
        headers: await _getHeaders(),
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          return (data['data'] as List)
              .map((json) => MewacoContribution.fromJson(json))
              .toList();
        }
        return [];
      } else {
        throw Exception('Failed to load MEWACO contributions');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }
}

