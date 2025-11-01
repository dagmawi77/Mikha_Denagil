/// Post/Announcement model
class Post {
  final int id;
  final String title;
  final String content;
  final String type; // Event, Announcement, General Info
  final String targetSection;
  final DateTime? startDate;
  final DateTime? endDate;
  final String? attachmentUrl;
  final String? attachmentName;
  final String? attachmentType; // image, pdf, document
  final String priority; // High, Normal, Low
  final DateTime createdAt;
  final String createdBy;
  final int viewsCount;
  final String? medebeName;
  final bool isRead;

  Post({
    required this.id,
    required this.title,
    required this.content,
    required this.type,
    required this.targetSection,
    this.startDate,
    this.endDate,
    this.attachmentUrl,
    this.attachmentName,
    this.attachmentType,
    required this.priority,
    required this.createdAt,
    required this.createdBy,
    required this.viewsCount,
    this.medebeName,
    required this.isRead,
  });

  factory Post.fromJson(Map<String, dynamic> json) {
    return Post(
      id: json['id'] as int,
      title: json['title'] as String,
      content: json['content'] as String,
      type: json['type'] as String,
      targetSection: json['target_section'] as String,
      startDate: json['start_date'] != null
          ? DateTime.tryParse(json['start_date'])
          : null,
      endDate: json['end_date'] != null
          ? DateTime.tryParse(json['end_date'])
          : null,
      attachmentUrl: json['attachment_url'] as String?,
      attachmentName: json['attachment_name'] as String?,
      attachmentType: json['attachment_type'] as String?,
      priority: json['priority'] as String,
      createdAt: DateTime.parse(json['created_at']),
      createdBy: json['created_by'] as String,
      viewsCount: json['views_count'] as int,
      medebeName: json['medebe_name'] as String?,
      isRead: json['is_read'] as bool? ?? false,
    );
  }

  bool get hasAttachment => attachmentUrl != null;
  
  bool get isHighPriority => priority == 'High';
  
  bool get isEvent => type == 'Event';
  
  bool get isAnnouncement => type == 'Announcement';
  
  bool get hasStartDate => startDate != null;
  
  bool get hasEndDate => endDate != null;

  @override
  String toString() => 'Post(id: $id, title: $title, type: $type)';
}

