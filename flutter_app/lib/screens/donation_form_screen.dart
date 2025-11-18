import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/api_service.dart';
import '../models/donation_type.dart';
import 'donation_payment_screen.dart';
import 'donation_history_screen.dart';

class DonationFormScreen extends StatefulWidget {
  final DonationType? donationType;

  const DonationFormScreen({Key? key, this.donationType}) : super(key: key);

  @override
  State<DonationFormScreen> createState() => _DonationFormScreenState();
}

class _DonationFormScreenState extends State<DonationFormScreen> {
  final ApiService _apiService = ApiService();
  final _formKey = GlobalKey<FormState>();
  final _amountController = TextEditingController();
  final _nameController = TextEditingController();
  final _christianNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();

  List<DonationType> _donationTypes = [];
  DonationType? _selectedType;
  bool _isAnonymous = false;
  bool _isLoading = false;
  bool _loadingTypes = true;

  @override
  void initState() {
    super.initState();
    _loadDonationTypes();
  }

  Future<void> _loadDonationTypes() async {
    try {
      final types = await _apiService.getDonationTypes();
      setState(() {
        _donationTypes = types;
        _loadingTypes = false;
        
        // Set selected type after loading
        if (widget.donationType != null) {
          // Find matching type in loaded list by ID
          final matchingType = types.firstWhere(
            (type) => type.id == widget.donationType!.id,
            orElse: () => types.isNotEmpty ? types.first : widget.donationType!,
          );
          _selectedType = matchingType;
        } else if (types.isNotEmpty) {
          _selectedType = types.first;
        }
      });
    } catch (e) {
      setState(() {
        _loadingTypes = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading donation types: $e')),
        );
      }
    }
  }

  Future<void> _submitDonation() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_selectedType == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a donation type')),
      );
      return;
    }

    final amount = double.tryParse(_amountController.text);
    if (amount == null || amount <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid amount')),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final result = await _apiService.initiateDonation(
        donationTypeId: _selectedType!.id,
        amount: amount,
        donorName: _isAnonymous ? null : _nameController.text.trim(),
        christianName: _isAnonymous ? null : _christianNameController.text.trim(),
        donorEmail: _emailController.text.trim().isEmpty ? null : _emailController.text.trim(),
        donorPhone: _phoneController.text.trim().isEmpty ? null : _phoneController.text.trim(),
        isAnonymous: _isAnonymous,
      );

      if (result['success'] == true && result['data'] != null) {
        final checkoutUrl = result['data']['checkout_url'] as String;
        final txRef = result['data']['tx_ref'] as String;

        if (mounted) {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => DonationPaymentScreen(
                checkoutUrl: checkoutUrl,
                txRef: txRef,
                amount: amount,
                donationType: _selectedType!,
              ),
            ),
          );
        }
      } else {
        throw Exception(result['error'] ?? 'Failed to initiate donation');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _amountController.dispose();
    _nameController.dispose();
    _christianNameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Make Donation / ለግስና ይስጡ'),
        backgroundColor: const Color(0xFF14860C),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const DonationHistoryScreen(),
                ),
              );
            },
            tooltip: 'Donation History',
          ),
        ],
      ),
      body: _loadingTypes
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Donation Type Selection
                    Card(
                      elevation: 2,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Donation Type / የለግስና አይነት',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            DropdownButtonFormField<DonationType>(
                              value: _selectedType,
                              decoration: InputDecoration(
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 12,
                                ),
                              ),
                              items: _donationTypes.map((type) {
                                return DropdownMenuItem<DonationType>(
                                  value: type,
                                  child: Text(
                                    type.nameAmharic.isNotEmpty
                                        ? type.nameAmharic
                                        : type.name,
                                  ),
                                );
                              }).toList(),
                              onChanged: _donationTypes.isEmpty ? null : (value) {
                                setState(() {
                                  _selectedType = value;
                                });
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Amount Input
                    Card(
                      elevation: 2,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Amount / መጠን (ETB)',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _amountController,
                              keyboardType: TextInputType.number,
                              inputFormatters: [
                                FilteringTextInputFormatter.allow(
                                  RegExp(r'^\d+\.?\d{0,2}'),
                                ),
                              ],
                              decoration: InputDecoration(
                                prefixText: 'ETB ',
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                hintText: 'Enter amount',
                              ),
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Please enter an amount';
                                }
                                final amount = double.tryParse(value);
                                if (amount == null || amount <= 0) {
                                  return 'Please enter a valid amount';
                                }
                                if (amount < 10) {
                                  return 'Minimum amount is 10 ETB';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              children: [100, 500, 1000, 5000].map((amount) {
                                return ChoiceChip(
                                  label: Text('ETB $amount'),
                                  selected: _amountController.text == amount.toString(),
                                  onSelected: (selected) {
                                    setState(() {
                                      _amountController.text = amount.toString();
                                    });
                                  },
                                );
                              }).toList(),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Anonymous Toggle
                    Card(
                      elevation: 2,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: SwitchListTile(
                        title: const Text('Anonymous Donation / ስም የማይገለጽ ለግስና'),
                        subtitle: const Text('Your name will not be displayed'),
                        value: _isAnonymous,
                        onChanged: (value) {
                          setState(() {
                            _isAnonymous = value;
                          });
                        },
                        activeColor: const Color(0xFF14860C),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Donor Information (if not anonymous)
                    if (!_isAnonymous) ...[
                      Card(
                        elevation: 2,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Donor Information / የለግስና ሰጪ መረጃ',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 16),
                              TextFormField(
                                controller: _nameController,
                                decoration: InputDecoration(
                                  labelText: 'Full Name / ሙሉ ስም',
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  prefixIcon: const Icon(Icons.person),
                                ),
                                validator: (value) {
                                  if (!_isAnonymous &&
                                      (value == null || value.isEmpty)) {
                                    return 'Please enter your name';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 12),
                              TextFormField(
                                controller: _christianNameController,
                                decoration: InputDecoration(
                                  labelText: 'Christian Name / የክርስትና ስም',
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  prefixIcon: const Icon(Icons.church),
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextFormField(
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                decoration: InputDecoration(
                                  labelText: 'Email / ኢሜይል (Optional)',
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  prefixIcon: const Icon(Icons.email),
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextFormField(
                                controller: _phoneController,
                                keyboardType: TextInputType.phone,
                                decoration: InputDecoration(
                                  labelText: 'Phone / ስልክ (Optional)',
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  prefixIcon: const Icon(Icons.phone),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],

                    // Submit Button
                    SizedBox(
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: _isLoading ? null : _submitDonation,
                        icon: _isLoading
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  valueColor:
                                      AlwaysStoppedAnimation<Color>(Colors.white),
                                ),
                              )
                            : const Icon(Icons.payment),
                        label: Text(
                          _isLoading
                              ? 'Processing...'
                              : 'Proceed to Payment / ወደ ክፍያ ይቀጥሉ',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF14860C),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}

