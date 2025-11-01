import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../models/post.dart';
import 'post_details_screen.dart';
import 'login_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _apiService = ApiService();
  final RefreshController _refreshController = RefreshController();
  
  List<Post> _posts = [];
  Map<String, int> _stats = {};
  bool _isLoading = true;
  String? _error;
  String _selectedType = '';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final posts = await _apiService.getPosts(type: _selectedType.isEmpty ? null : _selectedType);
      final stats = await _apiService.getPostsStats();
      
      setState(() {
        _posts = posts;
        _stats = stats;
        _isLoading = false;
      });
      
      _refreshController.refreshCompleted();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
      _refreshController.refreshFailed();
    }
  }

  Future<void> _logout() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    await authProvider.logout();
    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
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

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final member = authProvider.currentMember;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Mikha Denagil / ምክሃል ድንግል', style: TextStyle(fontSize: 16)),
            if (member != null)
              Text(
                member.fullName,
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.normal),
              ),
          ],
        ),
        backgroundColor: Color(0xFF14860C),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(Icons.logout),
            onPressed: _logout,
            tooltip: 'Logout / ውጣ',
          ),
        ],
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
                        onPressed: _loadData,
                        child: Text('Retry / እንደገና ሞክር'),
                      ),
                    ],
                  ),
                )
              : SmartRefresher(
                  controller: _refreshController,
                  onRefresh: _loadData,
                  child: SingleChildScrollView(
                    padding: EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Stats Cards
                        Row(
                          children: [
                            Expanded(
                              child: _StatCard(
                                title: 'Total\nጠቅላላ',
                                value: _stats['total_posts']?.toString() ?? '0',
                                icon: Icons.article,
                                color: Color(0xFF14860C),
                              ),
                            ),
                            SizedBox(width: 12),
                            Expanded(
                              child: _StatCard(
                                title: 'Read\nተነቧል',
                                value: _stats['read_posts']?.toString() ?? '0',
                                icon: Icons.done_all,
                                color: Colors.blue,
                              ),
                            ),
                            SizedBox(width: 12),
                            Expanded(
                              child: _StatCard(
                                title: 'Unread\nአልተነበበም',
                                value: _stats['unread_posts']?.toString() ?? '0',
                                icon: Icons.notifications_active,
                                color: Colors.orange,
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: 24),

                        // Filter
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Posts & Announcements',
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            SizedBox(height: 8),
                            SizedBox(
                              width: double.infinity,
                              child: DropdownButton<String>(
                                value: _selectedType.isEmpty ? null : _selectedType,
                                hint: Text('All Types'),
                                isExpanded: true,
                                items: [
                                  DropdownMenuItem(value: '', child: Text('All / ሁሉም')),
                                  DropdownMenuItem(value: 'Event', child: Text('Events / ዝግጅቶች')),
                                  DropdownMenuItem(value: 'Announcement', child: Text('Announcements')),
                                ],
                                onChanged: (value) {
                                  setState(() {
                                    _selectedType = value ?? '';
                                  });
                                  _loadData();
                                },
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: 16),

                        // Posts List
                        if (_posts.isEmpty)
                          Center(
                            child: Padding(
                              padding: EdgeInsets.all(48),
                              child: Column(
                                children: [
                                  Icon(Icons.inbox, size: 64, color: Colors.grey),
                                  SizedBox(height: 16),
                                  Text(
                                    'No posts available\nምንም ማስታወቂያዎች የሉም',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(color: Colors.grey),
                                  ),
                                ],
                              ),
                            ),
                          )
                        else
                          ListView.builder(
                            shrinkWrap: true,
                            physics: NeverScrollableScrollPhysics(),
                            itemCount: _posts.length,
                            itemBuilder: (context, index) {
                              final post = _posts[index];
                              return _PostCard(
                                post: post,
                                onTap: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => PostDetailsScreen(postId: post.id),
                                    ),
                                  ).then((_) => _loadData());
                                },
                              );
                            },
                          ),
                      ],
                    ),
                  ),
                ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  const _StatCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 4,
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icon, color: color, size: 32),
            SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            SizedBox(height: 4),
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 10),
            ),
          ],
        ),
      ),
    );
  }
}

class _PostCard extends StatelessWidget {
  final Post post;
  final VoidCallback onTap;

  const _PostCard({required this.post, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final priorityColor = post.priority == 'High'
        ? Colors.red
        : post.priority == 'Low'
            ? Colors.grey
            : Color(0xFF14860C);

    return Card(
      margin: EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: priorityColor,
          width: 2,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      post.title,
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  if (!post.isRead)
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.orange,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        'New',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                ],
              ),
              SizedBox(height: 8),
              Text(
                post.content.length > 150
                    ? '${post.content.substring(0, 150)}...'
                    : post.content,
                style: TextStyle(color: Colors.grey[700]),
              ),
              SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  Chip(
                    label: Text(post.type, style: TextStyle(fontSize: 12)),
                    backgroundColor: Colors.blue[100],
                  ),
                  if (post.isHighPriority)
                    Chip(
                      label: Text('High Priority', style: TextStyle(fontSize: 12)),
                      backgroundColor: Colors.red[100],
                    ),
                  if (post.hasAttachment)
                    Chip(
                      label: Text('Attachment', style: TextStyle(fontSize: 12)),
                      backgroundColor: Colors.green[100],
                      avatar: Icon(Icons.attach_file, size: 16),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

