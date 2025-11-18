import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../models/mewaco_type.dart';
import 'mewaco_payment_screen.dart';
import 'mewaco_history_screen.dart';

class MewacoFormScreen extends StatefulWidget {
  final MewacoType? mewacoType;

  const MewacoFormScreen({Key? key, this.mewacoType}) : super(key: key);

  @override
  State<MewacoFormScreen> createState() => _MewacoFormScreenState();
}

class _MewacoFormScreenState extends State<MewacoFormScreen> {
  final ApiService _apiService = ApiService();
  final _formKey = GlobalKey<FormState>();
  final _amountController = TextEditingController();
  final _notesController = TextEditingController();
  final _dateController = TextEditingController();

  List<MewacoType> _mewacoTypes = [];
  MewacoType? _selectedType;
  bool _isLoading = false;
  bool _loadingTypes = true;

  @override
  void initState() {
    super.initState();
    _loadMewacoTypes();
    if (widget.mewacoType != null) {
      _selectedType = widget.mewacoType;
    }
    // Set default date to today
    _dateController.text = DateFormat('yyyy-MM-dd').format(DateTime.now());
  }

  Future<void> _loadMewacoTypes() async {
    try {
      final types = await _apiService.getMewacoTypes();
      setState(() {
        _mewacoTypes = types;
        _loadingTypes = false;
        
        // Set selected type after loading
        if (widget.mewacoType != null) {
          final matchingType = types.firstWhere(
            (type) => type.id == widget.mewacoType!.id,
            orElse: () => types.isNotEmpty ? types.first : widget.mewacoType!,
          );
          _selectedType = matchingType;
          if (_selectedType != null) {
            _amountController.text = _selectedType!.defaultAmount.toStringAsFixed(2);
          }
        } else if (types.isNotEmpty) {
          _selectedType = types.first;
          _amountController.text = types.first.defaultAmount.toStringAsFixed(2);
        }
      });
    } catch (e) {
      setState(() {
        _loadingTypes = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading MEWACO types: $e')),
        );
      }
    }
  }

  Future<void> _selectDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() {
        _dateController.text = DateFormat('yyyy-MM-dd').format(picked);
      });
    }
  }

  Future<void> _submitPayment() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_selectedType == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a MEWACO type')),
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
      final result = await _apiService.initiateMewacoPayment(
        mewacoTypeId: _selectedType!.id,
        amount: amount,
        contributionDate: _dateController.text.trim(),
        notes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
      );

      if (result['success'] == true && result['data'] != null) {
        final checkoutUrl = result['data']['checkout_url'] as String;
        final txRef = result['data']['tx_ref'] as String;

        if (mounted) {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => MewacoPaymentScreen(
                checkoutUrl: checkoutUrl,
                txRef: txRef,
                amount: amount,
                mewacoType: _selectedType!,
              ),
            ),
          );
        }
      } else {
        throw Exception(result['error'] ?? 'Failed to initiate payment');
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
    _notesController.dispose();
    _dateController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pay MEWACO / መዋኮ ይክፈሉ'),
        backgroundColor: const Color(0xFF14860C),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const MewacoHistoryScreen(),
                ),
              );
            },
            tooltip: 'Contribution History',
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
                    // MEWACO Type Selection
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
                              'MEWACO Type / የመዋኮ አይነት',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            DropdownButtonFormField<MewacoType>(
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
                              items: _mewacoTypes.map((type) {
                                return DropdownMenuItem<MewacoType>(
                                  value: type,
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(type.typeName),
                                      Text(
                                        'ETB ${type.defaultAmount.toStringAsFixed(2)}',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: Colors.grey[600],
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              }).toList(),
                              onChanged: _mewacoTypes.isEmpty ? null : (value) {
                                setState(() {
                                  _selectedType = value;
                                  if (value != null) {
                                    _amountController.text = value.defaultAmount.toStringAsFixed(2);
                                  }
                                });
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Date Selection
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
                              'Contribution Date / የመዋኮ ቀን',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _dateController,
                              decoration: InputDecoration(
                                suffixIcon: const Icon(Icons.calendar_today),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                hintText: 'Select date',
                              ),
                              readOnly: true,
                              onTap: _selectDate,
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Please select a date';
                                }
                                return null;
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
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Notes (Optional)
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
                              'Notes / ማስታወሻ (Optional)',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _notesController,
                              maxLines: 3,
                              decoration: InputDecoration(
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                hintText: 'Add any notes...',
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Submit Button
                    SizedBox(
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: _isLoading ? null : _submitPayment,
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

