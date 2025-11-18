import 'dart:async';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../services/api_service.dart';
import '../models/mewaco_type.dart';
import 'mewaco_success_screen.dart';

class MewacoPaymentScreen extends StatefulWidget {
  final String checkoutUrl;
  final String txRef;
  final double amount;
  final MewacoType mewacoType;

  const MewacoPaymentScreen({
    Key? key,
    required this.checkoutUrl,
    required this.txRef,
    required this.amount,
    required this.mewacoType,
  }) : super(key: key);

  @override
  State<MewacoPaymentScreen> createState() => _MewacoPaymentScreenState();
}

class _MewacoPaymentScreenState extends State<MewacoPaymentScreen> {
  late final WebViewController _controller;
  final ApiService _apiService = ApiService();
  bool _isLoading = true;
  bool _isVerifying = false;
  Timer? _verificationTimer;

  @override
  void initState() {
    super.initState();
    _initializeWebView();
    _startVerificationTimer();
  }

  void _initializeWebView() {
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (String url) {
            setState(() {
              _isLoading = true;
            });
            
            // Intercept thank-you page redirects
            if (url.contains('thank-you') || url.contains('success') || url.contains('/donation/') || url.contains('/mewaco/')) {
              // Don't load the backend thank-you page, just verify payment
              _verifyPayment();
              // Prevent navigation to HTTP thank-you page
              return;
            }
          },
          onPageFinished: (String url) {
            setState(() {
              _isLoading = false;
            });
            
            // Check if payment is completed based on URL
            if (url.contains('thank-you') || url.contains('success') || url.contains('chapa.co')) {
              _verifyPayment();
            }
          },
          onNavigationRequest: (NavigationRequest request) {
            // Intercept navigation to HTTP thank-you pages
            final url = request.url.toLowerCase();
            if (url.contains('thank-you') || url.contains('success')) {
              // Verify payment instead of loading the page
              _verifyPayment();
              return NavigationDecision.prevent;
            }
            return NavigationDecision.navigate;
          },
          onWebResourceError: (WebResourceError error) {
            // Check if it's a cleartext error
            if (error.description.contains('ERR_CLEARTEXT_NOT_PERMITTED') || 
                error.description.contains('cleartext')) {
              // Try to verify payment anyway
              _verifyPayment();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Verifying payment... Please wait.'),
                  backgroundColor: Colors.blue,
                  duration: Duration(seconds: 3),
                ),
              );
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Error loading payment page: ${error.description}'),
                  backgroundColor: Colors.red,
                ),
              );
            }
          },
        ),
      )
      ..loadRequest(Uri.parse(widget.checkoutUrl));
  }

  void _startVerificationTimer() {
    // Poll every 3 seconds to check payment status
    _verificationTimer = Timer.periodic(const Duration(seconds: 3), (timer) {
      _verifyPayment();
    });
  }

  Future<void> _verifyPayment() async {
    if (_isVerifying) return;

    setState(() {
      _isVerifying = true;
    });

    try {
      final result = await _apiService.verifyMewacoPayment(widget.txRef);

      if (result['success'] == true && result['data'] != null) {
        final paymentStatus = result['data']['payment_status'] as String;
        
        if (paymentStatus == 'Completed' || paymentStatus == 'Paid') {
          _verificationTimer?.cancel();
          
          if (mounted) {
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                builder: (context) => MewacoSuccessScreen(
                  txRef: widget.txRef,
                  amount: widget.amount,
                  mewacoType: widget.mewacoType,
                ),
              ),
            );
          }
        }
      }
    } catch (e) {
      // Silently fail - user might still be on payment page
      debugPrint('Verification error: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isVerifying = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _verificationTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Payment / ክፍያ'),
        backgroundColor: const Color(0xFF14860C),
        elevation: 0,
      ),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_isLoading)
            Container(
              color: Colors.white,
              child: const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('Loading payment page...'),
                  ],
                ),
              ),
            ),
          if (_isVerifying)
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                padding: const EdgeInsets.all(16),
                color: Colors.blue.withOpacity(0.9),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    ),
                    SizedBox(width: 12),
                    Text(
                      'Verifying payment...',
                      style: TextStyle(color: Colors.white),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

