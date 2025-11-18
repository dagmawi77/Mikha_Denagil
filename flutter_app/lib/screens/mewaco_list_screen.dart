import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/mewaco_type.dart';
import 'mewaco_form_screen.dart';

class MewacoListScreen extends StatefulWidget {
  const MewacoListScreen({Key? key}) : super(key: key);

  @override
  State<MewacoListScreen> createState() => _MewacoListScreenState();
}

class _MewacoListScreenState extends State<MewacoListScreen> {
  final ApiService _apiService = ApiService();
  List<MewacoType> _mewacoTypes = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadMewacoTypes();
  }

  Future<void> _loadMewacoTypes() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final types = await _apiService.getMewacoTypes();
      setState(() {
        _mewacoTypes = types;
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
        title: const Text('MEWACO Contributions / መዋኮ'),
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
                        'Error loading MEWACO types',
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
                        onPressed: _loadMewacoTypes,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Retry'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF14860C),
                        ),
                      ),
                    ],
                  ),
                )
              : _mewacoTypes.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.inbox, size: 64, color: Colors.grey[400]),
                          const SizedBox(height: 16),
                          Text(
                            'No MEWACO types available',
                            style: TextStyle(fontSize: 18, color: Colors.grey[700]),
                          ),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _loadMewacoTypes,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _mewacoTypes.length,
                        itemBuilder: (context, index) {
                          final type = _mewacoTypes[index];
                          return _buildMewacoTypeCard(type);
                        },
                      ),
                    ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const MewacoFormScreen(),
            ),
          ).then((_) => _loadMewacoTypes());
        },
        icon: const Icon(Icons.payment),
        label: const Text('Pay MEWACO / መዋኮ ይክፈሉ'),
        backgroundColor: const Color(0xFF14860C),
      ),
    );
  }

  Widget _buildMewacoTypeCard(MewacoType type) {
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
              builder: (context) => MewacoFormScreen(mewacoType: type),
            ),
          ).then((_) => _loadMewacoTypes());
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
                  Icons.account_balance_wallet,
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
                      type.typeName,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                    if (type.description != null && type.description!.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          type.description!,
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    const SizedBox(height: 8),
                    Text(
                      'Default: ETB ${type.defaultAmount.toStringAsFixed(2)}',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: const Color(0xFF14860C),
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

