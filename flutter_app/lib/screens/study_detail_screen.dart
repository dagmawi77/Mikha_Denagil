import 'package:flutter/material.dart';
import '../models/study.dart';
import '../services/api_service.dart';

class StudyDetailScreen extends StatefulWidget {
  final int studyId;

  const StudyDetailScreen({Key? key, required this.studyId}) : super(key: key);

  @override
  _StudyDetailScreenState createState() => _StudyDetailScreenState();
}

class _StudyDetailScreenState extends State<StudyDetailScreen> {
  final ApiService _apiService = ApiService();
  Study? _study;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadStudy();
  }

  Future<void> _loadStudy() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final result = await _apiService.getStudyDetails(widget.studyId);

    setState(() {
      _isLoading = false;
      if (result['success']) {
        _study = result['study'];
      } else {
        _error = result['error'];
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Study Details'),
        backgroundColor: const Color(0xFF14860C),
        actions: [
          if (_study?.attachmentUrl != null)
            IconButton(
              icon: const Icon(Icons.download),
              onPressed: () {
                _showAttachmentDialog();
              },
            ),
        ],
      ),
      body: _isLoading
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
                        onPressed: _loadStudy,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Featured Badge
                      if (_study!.isFeatured)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.amber,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: const [
                              Icon(Icons.star, size: 16, color: Colors.black),
                              SizedBox(width: 6),
                              Text(
                                'FEATURED / ተለይቶ የቀረበ',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.black,
                                ),
                              ),
                            ],
                          ),
                        ),
                      if (_study!.isFeatured) const SizedBox(height: 16),

                      // Title
                      Text(
                        _study!.title,
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF2c3e50),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Meta Info Card
                      Card(
                        color: Colors.grey[100],
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            children: [
                              _buildMetaRow(Icons.category, 'Category', _study!.categoryName),
                              const Divider(),
                              _buildMetaRow(Icons.person, 'Author', _study!.author),
                              const Divider(),
                              _buildMetaRow(Icons.group, 'Target Audience', _study!.targetAudience),
                              if (_study!.publishDate != null) const Divider(),
                              if (_study!.publishDate != null)
                                _buildMetaRow(Icons.calendar_today, 'Published', _study!.publishDate!),
                              const Divider(),
                              _buildMetaRow(Icons.visibility, 'Views', '${_study!.viewsCount}'),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Attachment Card
                      if (_study!.attachmentUrl != null)
                        Card(
                          color: Colors.green[50],
                          child: ListTile(
                            leading: const Icon(Icons.attach_file, color: Colors.green, size: 32),
                            title: Text(
                              _study!.attachmentName ?? 'Attachment',
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Text(_study!.attachmentType ?? 'File'),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  '${_study!.downloadsCount} downloads',
                                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                                ),
                                const SizedBox(width: 8),
                                const Icon(Icons.arrow_forward_ios, size: 16),
                              ],
                            ),
                            onTap: _showAttachmentDialog,
                          ),
                        ),
                      if (_study!.attachmentUrl != null) const SizedBox(height: 20),

                      // Content Header
                      const Divider(thickness: 2),
                      const SizedBox(height: 10),
                      const Text(
                        'Study Content / የትምህርት ይዘት',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF14860C),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Content Body (HTML Rendering)
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.grey[300]!),
                        ),
                        child: _renderHtmlContent(_study!.contentBody ?? ''),
                      ),

                      const SizedBox(height: 20),

                      // Tags
                      if (_study!.tags != null && _study!.tags!.isNotEmpty)
                        Wrap(
                          spacing: 8,
                          children: _study!.tags!.split(',').map((tag) {
                            return Chip(
                              label: Text(tag.trim()),
                              backgroundColor: Colors.blue[100],
                            );
                          }).toList(),
                        ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildMetaRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, size: 20, color: const Color(0xFF14860C)),
        const SizedBox(width: 8),
        Text(
          '$label:',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 14),
            textAlign: TextAlign.right,
          ),
        ),
      ],
    );
  }

  // Simple HTML renderer (convert HTML to Flutter widgets)
  Widget _renderHtmlContent(String html) {
    // Strip HTML tags and render as formatted text
    // For basic HTML support without external packages
    String cleanText = html
        .replaceAll(RegExp(r'<br\s*/?>'), '\n')
        .replaceAll(RegExp(r'<p>'), '')
        .replaceAll(RegExp(r'</p>'), '\n\n')
        .replaceAll(RegExp(r'<h[1-6]>'), '')
        .replaceAll(RegExp(r'</h[1-6]>'), '\n\n')
        .replaceAll(RegExp(r'<li>'), '• ')
        .replaceAll(RegExp(r'</li>'), '\n')
        .replaceAll(RegExp(r'<[^>]*>'), '')
        .replaceAll('&nbsp;', ' ')
        .replaceAll('&amp;', '&')
        .replaceAll('&lt;', '<')
        .replaceAll('&gt;', '>')
        .replaceAll('&quot;', '"');

    return Text(
      cleanText.trim(),
      style: const TextStyle(
        fontSize: 16,
        height: 1.8,
        color: Colors.black87,
      ),
    );
  }

  void _showAttachmentDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Download Attachment'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('File: ${_study!.attachmentName ?? "Unknown"}'),
            const SizedBox(height: 8),
            Text('Type: ${_study!.attachmentType ?? "Unknown"}'),
            const SizedBox(height: 8),
            Text('Downloads: ${_study!.downloadsCount}'),
            const SizedBox(height: 16),
            const Text(
              'Note: Download feature requires additional implementation',
              style: TextStyle(fontSize: 12, color: Colors.grey, fontStyle: FontStyle.italic),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Download starting...')),
              );
              // TODO: Implement actual file download
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF14860C)),
            child: const Text('Download'),
          ),
        ],
      ),
    );
  }
}

