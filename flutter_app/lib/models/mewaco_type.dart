/// MEWACO Type Model
class MewacoType {
  final int id;
  final String typeName;
  final String? description;
  final double defaultAmount;
  final String status;

  MewacoType({
    required this.id,
    required this.typeName,
    this.description,
    required this.defaultAmount,
    required this.status,
  });

  factory MewacoType.fromJson(Map<String, dynamic> json) {
    // Handle default_amount which might be int, double, or string
    double parseAmount(dynamic value) {
      if (value == null) return 0.0;
      if (value is int) return value.toDouble();
      if (value is double) return value;
      if (value is String) {
        return double.tryParse(value) ?? 0.0;
      }
      if (value is num) return value.toDouble();
      return 0.0;
    }
    
    return MewacoType(
      id: json['id'] as int,
      typeName: json['type_name'] as String,
      description: json['description'] as String?,
      defaultAmount: parseAmount(json['default_amount']),
      status: json['status'] as String? ?? 'Active',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type_name': typeName,
      'description': description,
      'default_amount': defaultAmount,
      'status': status,
    };
  }

  @override
  String toString() => 'MewacoType(id: $id, name: $typeName)';
}

