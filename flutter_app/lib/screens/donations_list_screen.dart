import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/donation_type.dart';
import 'donation_form_screen.dart';

class DonationsListScreen extends StatefulWidget {
  const DonationsListScreen({Key? key}) : super(key: key);

  @override
  State<DonationsListScreen> createState() => _DonationsListScreenState();
}

class _DonationsListScreenState extends State<DonationsListScreen> {
  final ApiService _apiService = ApiService();
  List<DonationType> _donationTypes = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDonationTypes();
  }

  Future<void> _loadDonationTypes() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final types = await _apiService.getDonationTypes();
      setState(() {
        _donationTypes = types;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Donations / ለግስና'),
        backgroundColor: const Color(0xFF14860C),
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
                      const SizedBox(height: 16),
                      Text(
                        'Error loading donations',
                        style: TextStyle(fontSize: 18, color: Colors.grey[700]),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _error!,
                        style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton.icon(
                        onPressed: _loadDonationTypes,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Retry'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF14860C),
                        ),
                      ),
                    ],
                  ),
                )
              : _donationTypes.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.inbox, size: 64, color: Colors.grey[400]),
                          const SizedBox(height: 16),
                          Text(
                            'No donation types available',
                            style: TextStyle(fontSize: 18, color: Colors.grey[700]),
                          ),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _loadDonationTypes,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _donationTypes.length,
                        itemBuilder: (context, index) {
                          final type = _donationTypes[index];
                          return _buildDonationTypeCard(type);
                        },
                      ),
                    ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const DonationFormScreen(),
            ),
          ).then((_) => _loadDonationTypes());
        },
        icon: const Icon(Icons.add),
        label: const Text('Donate Now / ለግስና ይስጡ'),
        backgroundColor: const Color(0xFF14860C),
      ),
    );
  }

  Widget _buildDonationTypeCard(DonationType type) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => DonationFormScreen(donationType: type),
            ),
          ).then((_) => _loadDonationTypes());
        },
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Color(0xFF14860C), Color(0xFF106b09)],
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(
                  Icons.favorite,
                  color: Colors.white,
                  size: 30,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      type.nameAmharic.isNotEmpty ? type.nameAmharic : type.name,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                    if (type.nameAmharic.isNotEmpty && type.name != type.nameAmharic)
                      Text(
                        type.name,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey[600],
                        ),
                      ),
                    if (type.descriptionAmharic != null && type.descriptionAmharic!.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          type.descriptionAmharic!,
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                ),
              ),
              const Icon(
                Icons.arrow_forward_ios,
                color: Color(0xFF14860C),
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

