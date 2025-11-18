/// Donation Type Model
class DonationType {
  final int id;
  final String name;
  final String nameAmharic;
  final String? description;
  final String? descriptionAmharic;
  final String status;

  DonationType({
    required this.id,
    required this.name,
    required this.nameAmharic,
    this.description,
    this.descriptionAmharic,
    required this.status,
  });

  factory DonationType.fromJson(Map<String, dynamic> json) {
    return DonationType(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      nameAmharic: json['name_amharic'] as String? ?? '',
      description: json['description'] as String?,
      descriptionAmharic: json['description_amharic'] as String?,
      status: json['status'] as String? ?? 'active',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'name_amharic': nameAmharic,
      'description': description,
      'description_amharic': descriptionAmharic,
      'status': status,
    };
  }

  @override
  String toString() => 'DonationType(id: $id, name: $name)';
}

