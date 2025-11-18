import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'providers/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/main_navigation_screen.dart';
import 'config/api_config.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
      ],
      child: MaterialApp(
        title: 'Mikha Denagil',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          primaryColor: const Color(0xFF14860C),
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF14860C),
            primary: const Color(0xFF14860C),
          ),
          useMaterial3: true,
        ),
        home: const SplashScreen(),
      ),
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<String?> _loadLogo() async {
    // Load logo from server
    try {
      final logoUrl = '${ApiConfig.baseUrl}/static/images/logo-white.png';
      // Quick check if URL is accessible (with timeout)
      final response = await http.head(Uri.parse(logoUrl)).timeout(
        const Duration(seconds: 2),
        onTimeout: () {
          throw Exception('Timeout');
        },
      );
      if (response.statusCode == 200) {
        return logoUrl;
      }
      return null;
    } catch (e) {
      // Fallback to regular logo or asset
      return '${ApiConfig.baseUrl}/static/images/logo.png';
    }
  }

  Widget _buildLogoFallback() {
    return Container(
      width: 180,
      height: 180,
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white.withOpacity(0.3), width: 3),
      ),
      child: const Icon(
        Icons.church,
        size: 100,
        color: Colors.white,
      ),
    );
  }

  Widget _buildLogoLoading() {
    return Container(
      width: 180,
      height: 180,
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white.withOpacity(0.3), width: 3),
      ),
      child: const CircularProgressIndicator(
        color: Colors.white,
        strokeWidth: 3,
      ),
    );
  }

  Future<void> _checkAuth() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final isAuthenticated = await authProvider.checkAuthentication();
    
    await Future.delayed(const Duration(seconds: 2));
    
    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => isAuthenticated
              ? const MainNavigationScreen()
              : const LoginScreen(),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF14860C), Color(0xFF106b09)],
          ),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Logo Image - Try network first, fallback to asset
              FutureBuilder<String>(
                future: _loadLogo(),
                builder: (context, snapshot) {
                  if (snapshot.hasData && snapshot.data != null) {
                    return Image.network(
                      snapshot.data!,
                      width: 180,
                      height: 180,
                      fit: BoxFit.contain,
                      errorBuilder: (context, error, stackTrace) {
                        return _buildLogoFallback();
                      },
                      loadingBuilder: (context, child, loadingProgress) {
                        if (loadingProgress == null) return child;
                        return _buildLogoLoading();
                      },
                    );
                  }
                  return _buildLogoFallback();
                },
              ),
              const SizedBox(height: 32),
              const Text(
                'Mikha Denagil\nምክሐ ደናግል',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  letterSpacing: 1.2,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Spiritual Society Management',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.white.withOpacity(0.9),
                  fontWeight: FontWeight.w300,
                ),
              ),
              const SizedBox(height: 48),
              const CircularProgressIndicator(
                color: Colors.white,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

