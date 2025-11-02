import 'package:flutter/material.dart';
import '../models/study.dart';
import '../services/api_service.dart';
import 'study_detail_screen.dart';

class StudiesListScreen extends StatefulWidget {
  const StudiesListScreen({Key? key}) : super(key: key);

  @override
  _StudiesListScreenState createState() => _StudiesListScreenState();
}

class _StudiesListScreenState extends State<StudiesListScreen> {
  final ApiService _apiService = ApiService();
  List<Study> _studies = [];
  List<StudyCategory> _categories = [];
  int? _selectedCategoryId;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadCategories();
    _loadStudies();
  }

  Future<void> _loadCategories() async {
    final result = await _apiService.getStudyCategories();
    if (result['success']) {
      setState(() {
        _categories = result['categories'];
      });
    }
  }

  Future<void> _loadStudies() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final result = await _apiService.getStudies(
      categoryId: _selectedCategoryId,
    );

    setState(() {
      _isLoading = false;
      if (result['success']) {
        _studies = result['studies'];
      } else {
        _error = result['error'];
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Study Materials\nየትምህርት ጽሁፎች'),
        backgroundColor: const Color(0xFF14860C),
        elevation: 0,
      ),
      body: Column(
        children: [
          // Category Filter
          if (_categories.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              color: Colors.white,
              child: Row(
                children: [
                  const Icon(Icons.filter_list, color: Color(0xFF14860C)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: DropdownButtonFormField<int?>(
                      value: _selectedCategoryId,
                      decoration: const InputDecoration(
                        labelText: 'Filter by Category',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                      items: [
                        const DropdownMenuItem<int?>(
                          value: null,
                          child: Text('All Categories / ሁሉም ምድቦች'),
                        ),
                        ..._categories.map((category) => DropdownMenuItem<int?>(
                              value: category.id,
                              child: Text(category.name),
                            )),
                      ],
                      onChanged: (value) {
                        setState(() {
                          _selectedCategoryId = value;
                        });
                        _loadStudies();
                      },
                    ),
                  ),
                ],
              ),
            ),

          // Studies List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.error_outline, size: 64, color: Colors.red),
                            const SizedBox(height: 16),
                            Text(_error!, style: const TextStyle(color: Colors.red)),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: _loadStudies,
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      )
                    : _studies.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: const [
                                Icon(Icons.book_outlined, size: 80, color: Colors.grey),
                                SizedBox(height: 16),
                                Text(
                                  'No Study Materials Available',
                                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                                ),
                                SizedBox(height: 8),
                                Text(
                                  'ምንም የትምህርት ጽሁፎች የሉም',
                                  style: TextStyle(fontSize: 16, color: Colors.grey),
                                ),
                              ],
                            ),
                          )
                        : RefreshIndicator(
                            onRefresh: _loadStudies,
                            child: ListView.builder(
                              padding: const EdgeInsets.all(16),
                              itemCount: _studies.length,
                              itemBuilder: (context, index) {
                                return _buildStudyCard(_studies[index]);
                              },
                            ),
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildStudyCard(Study study) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => StudyDetailScreen(studyId: study.id),
            ),
          ).then((_) => _loadStudies()); // Refresh after viewing
        },
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border(
              left: BorderSide(
                color: study.isFeatured ? Colors.amber : const Color(0xFF14860C),
                width: 4,
              ),
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Featured Badge
                if (study.isFeatured)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.amber,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(Icons.star, size: 14, color: Colors.black),
                        SizedBox(width: 4),
                        Text(
                          'FEATURED',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: Colors.black,
                          ),
                        ),
                      ],
                    ),
                  ),
                if (study.isFeatured) const SizedBox(height: 8),

                // Title
                Text(
                  study.title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF2c3e50),
                  ),
                ),
                const SizedBox(height: 8),

                // Meta Info
                Wrap(
                  spacing: 12,
                  runSpacing: 6,
                  children: [
                    _buildMetaChip(Icons.category, study.categoryName, Colors.blue),
                    _buildMetaChip(Icons.person, study.author, Colors.green),
                    if (study.publishDate != null)
                      _buildMetaChip(Icons.calendar_today, study.publishDate!, Colors.orange),
                    _buildMetaChip(Icons.visibility, '${study.viewsCount} views', Colors.grey),
                  ],
                ),
                const SizedBox(height: 12),

                // Summary
                if (study.summary != null && study.summary!.isNotEmpty)
                  Text(
                    study.summary!,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 14,
                      color: Colors.black87,
                      height: 1.5,
                    ),
                  ),
                const SizedBox(height: 12),

                // Badges
                Row(
                  children: [
                    // Category Badge
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.teal,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        study.categoryName,
                        style: const TextStyle(color: Colors.white, fontSize: 12),
                      ),
                    ),
                    const SizedBox(width: 8),

                    // Attachment Badge
                    if (study.attachmentUrl != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.green,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.attach_file, size: 12, color: Colors.white),
                            SizedBox(width: 4),
                            Text(
                              'Attachment',
                              style: TextStyle(color: Colors.white, fontSize: 12),
                            ),
                          ],
                        ),
                      ),

                    const Spacer(),

                    // Read Indicator
                    if (study.isRead)
                      const Icon(Icons.check_circle, size: 20, color: Colors.green)
                    else
                      const Icon(Icons.circle, size: 20, color: Colors.grey),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMetaChip(IconData icon, String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(fontSize: 12, color: Colors.grey[700]),
        ),
      ],
    );
  }
}

