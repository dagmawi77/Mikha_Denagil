import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../models/post.dart';
import '../config/api_config.dart';

class PostDetailsScreen extends StatefulWidget {
  final int postId;

  const PostDetailsScreen({super.key, required this.postId});

  @override
  State<PostDetailsScreen> createState() => _PostDetailsScreenState();
}

class _PostDetailsScreenState extends State<PostDetailsScreen> {
  final ApiService _apiService = ApiService();
  Post? _post;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPost();
  }

  Future<void> _loadPost() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final post = await _apiService.getPostDetails(widget.postId);
      setState(() {
        _post = post;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Color _getPriorityColor(String priority) {
    switch (priority) {
      case 'High':
        return Colors.red;
      case 'Low':
        return Colors.grey;
      default:
        return Color(0xFF14860C);
    }
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'Event':
        return Icons.event;
      case 'Announcement':
        return Icons.campaign;
      default:
        return Icons.info;
    }
  }

  Future<void> _openAttachment(String url) async {
    final fullUrl = '${ApiConfig.baseUrl}$url';
    final uri = Uri.parse(fullUrl);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not open attachment')),
        );
      }
    }
  }

  String _formatDate(DateTime? date) {
    if (date == null) return 'N/A';
    return DateFormat('MMM dd, yyyy').format(date);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Post Details / ዝርዝር'),
        backgroundColor: Color(0xFF14860C),
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline, size: 64, color: Colors.red),
                      SizedBox(height: 16),
                      Text(_error!, textAlign: TextAlign.center),
                      SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadPost,
                        child: Text('Retry / እንደገና ሞክር'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Title
                      Text(
                        _post!.title,
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: _getPriorityColor(_post!.priority),
                        ),
                      ),
                      SizedBox(height: 16),

                      // Metadata
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          Chip(
                            avatar: Icon(
                              _getTypeIcon(_post!.type),
                              size: 18,
                            ),
                            label: Text(_post!.type),
                            backgroundColor: Colors.blue[100],
                          ),
                          if (_post!.isHighPriority)
                            Chip(
                              avatar: Icon(Icons.priority_high, size: 18),
                              label: Text('High Priority / ከፍተኛ ቅድሚያ'),
                              backgroundColor: Colors.red[100],
                            ),
                          Chip(
                            label: Text(_post!.targetSection),
                            backgroundColor: Colors.green[100],
                          ),
                        ],
                      ),
                      SizedBox(height: 16),

                      // Meta Info
                      Container(
                        padding: EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.grey[100],
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          children: [
                            _InfoRow(
                              icon: Icons.person,
                              label: 'Created By / በ',
                              value: _post!.createdBy,
                            ),
                            _InfoRow(
                              icon: Icons.access_time,
                              label: 'Posted / የተለጠፈበት',
                              value: _formatDate(_post!.createdAt),
                            ),
                            if (_post!.hasStartDate)
                              _InfoRow(
                                icon: Icons.calendar_today,
                                label: 'Start Date / የጅማሬ ቀን',
                                value: _formatDate(_post!.startDate),
                              ),
                            if (_post!.hasEndDate)
                              _InfoRow(
                                icon: Icons.event_busy,
                                label: 'End Date / የማብቂያ ቀን',
                                value: _formatDate(_post!.endDate),
                              ),
                            _InfoRow(
                              icon: Icons.visibility,
                              label: 'Views / እይታዎች',
                              value: _post!.viewsCount.toString(),
                            ),
                          ],
                        ),
                      ),
                      SizedBox(height: 24),

                      // Content
                      Text(
                        'Content / ይዘት',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      SizedBox(height: 12),
                      Text(
                        _post!.content,
                        style: TextStyle(
                          fontSize: 16,
                          height: 1.6,
                        ),
                      ),
                      SizedBox(height: 24),

                      // Attachment
                      if (_post!.hasAttachment) ...[
                        Text(
                          'Attachment / አባሪ',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: 12),
                        if (_post!.attachmentType == 'image')
                          ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: CachedNetworkImage(
                              imageUrl: '${ApiConfig.baseUrl}${_post!.attachmentUrl}',
                              placeholder: (context, url) => Center(
                                child: CircularProgressIndicator(),
                              ),
                              errorWidget: (context, url, error) => Container(
                                height: 200,
                                color: Colors.grey[300],
                                child: Center(
                                  child: Icon(Icons.error, size: 48),
                                ),
                              ),
                            ),
                          )
                        else
                          Card(
                            child: ListTile(
                              leading: Icon(
                                _post!.attachmentType == 'pdf'
                                    ? Icons.picture_as_pdf
                                    : Icons.insert_drive_file,
                                size: 40,
                                color: Color(0xFF14860C),
                              ),
                              title: Text(_post!.attachmentName ?? 'Attachment'),
                              subtitle: Text(
                                _post!.attachmentType == 'pdf'
                                    ? 'PDF Document'
                                    : 'Document',
                              ),
                              trailing: Icon(Icons.download),
                              onTap: () => _openAttachment(_post!.attachmentUrl!),
                            ),
                          ),
                        SizedBox(height: 24),
                      ],

                      // Read Status
                      Center(
                        child: Container(
                          padding: EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.green[100],
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.check_circle, color: Colors.green, size: 20),
                              SizedBox(width: 8),
                              Text(
                                'Marked as Read / እንደተነበበ ተመዝግቧል',
                                style: TextStyle(
                                  color: Colors.green[900],
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Color(0xFF14860C)),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.w500,
                color: Colors.grey[700],
              ),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

