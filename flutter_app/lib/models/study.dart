class Study {
  final int id;
  final String title;
  final int categoryId;
  final String categoryName;
  final String targetAudience;
  final String? summary;
  final String? contentBody;
  final String? attachmentUrl;
  final String? attachmentName;
  final String? attachmentType;
  final String? publishDate;
  final String author;
  final int viewsCount;
  final int downloadsCount;
  final bool isFeatured;
  final String? tags;
  final String createdAt;
  final bool isRead;

  Study({
    required this.id,
    required this.title,
    required this.categoryId,
    required this.categoryName,
    required this.targetAudience,
    this.summary,
    this.contentBody,
    this.attachmentUrl,
    this.attachmentName,
    this.attachmentType,
    this.publishDate,
    required this.author,
    required this.viewsCount,
    required this.downloadsCount,
    required this.isFeatured,
    this.tags,
    required this.createdAt,
    required this.isRead,
  });

  factory Study.fromJson(Map<String, dynamic> json) {
    return Study(
      id: json['id'] ?? 0,
      title: json['title'] ?? '',
      categoryId: json['category_id'] ?? 0,
      categoryName: json['category_name'] ?? '',
      targetAudience: json['target_audience'] ?? '',
      summary: json['summary'],
      contentBody: json['content_body'],
      attachmentUrl: json['attachment_url'],
      attachmentName: json['attachment_name'],
      attachmentType: json['attachment_type'],
      publishDate: json['publish_date'],
      author: json['author'] ?? '',
      viewsCount: json['views_count'] ?? 0,
      downloadsCount: json['downloads_count'] ?? 0,
      isFeatured: json['is_featured'] ?? false,
      tags: json['tags'],
      createdAt: json['created_at'] ?? '',
      isRead: json['is_read'] ?? false,
    );
  }
}

class StudyCategory {
  final int id;
  final String name;
  final String? description;
  final int displayOrder;

  StudyCategory({
    required this.id,
    required this.name,
    this.description,
    required this.displayOrder,
  });

  factory StudyCategory.fromJson(Map<String, dynamic> json) {
    return StudyCategory(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      description: json['description'],
      displayOrder: json['display_order'] ?? 0,
    );
  }
}

