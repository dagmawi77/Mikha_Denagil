import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../models/member.dart';
import '../services/api_service.dart';
import '../config/api_config.dart';

class AuthProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  
  Member? _currentMember;
  bool _isLoading = false;
  String? _error;
  bool _isAuthenticated = false;

  Member? get currentMember => _currentMember;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _isAuthenticated;
  
  // Get user data as Map (for compatibility)
  Map<String, dynamic>? get userData {
    if (_currentMember == null) return null;
    return {
      'full_name': _currentMember!.fullName,
      'username': _currentMember!.username,
      'section': _currentMember!.section,
      'phone': _currentMember!.phone,
      'email': _currentMember!.email,
      'gender': _currentMember!.gender,
    };
  }

  // Login
  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await _apiService.login(username, password);
      _currentMember = Member.fromJson(response['member']);
      _isAuthenticated = true;
      
      // Save user data
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(ApiConfig.userDataKey, jsonEncode(response['member']));
      
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      _isAuthenticated = false;
      notifyListeners();
      return false;
    }
  }

  // Logout
  Future<void> logout() async {
    await _apiService.logout();
    _currentMember = null;
    _isAuthenticated = false;
    
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(ApiConfig.userDataKey);
    
    notifyListeners();
  }

  // Check if logged in
  Future<bool> checkAuthentication() async {
    try {
      final token = await _apiService.getToken();
      if (token == null) return false;

      final prefs = await SharedPreferences.getInstance();
      final userData = prefs.getString(ApiConfig.userDataKey);
      if (userData != null) {
        _currentMember = Member.fromJson(jsonDecode(userData));
        _isAuthenticated = true;
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
}

