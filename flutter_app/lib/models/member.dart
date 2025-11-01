/// Member model
class Member {
  final int id;
  final String fullName;
  final String section;
  final String? phone;
  final String? email;
  final String gender;
  final String username;

  Member({
    required this.id,
    required this.fullName,
    required this.section,
    this.phone,
    this.email,
    required this.gender,
    required this.username,
  });

  factory Member.fromJson(Map<String, dynamic> json) {
    return Member(
      id: json['id'] as int,
      fullName: json['full_name'] as String,
      section: json['section'] as String,
      phone: json['phone'] as String?,
      email: json['email'] as String?,
      gender: json['gender'] as String,
      username: json['username'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'full_name': fullName,
      'section': section,
      'phone': phone,
      'email': email,
      'gender': gender,
      'username': username,
    };
  }

  @override
  String toString() => 'Member(id: $id, name: $fullName, section: $section)';
}

