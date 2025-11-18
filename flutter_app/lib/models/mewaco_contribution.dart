/// MEWACO Contribution Model
class MewacoContribution {
  // Helper method to parse amount from various types
  static double _parseAmount(dynamic value) {
    if (value == null) return 0.0;
    if (value is int) return value.toDouble();
    if (value is double) return value;
    if (value is String) {
      return double.tryParse(value) ?? 0.0;
    }
    if (value is num) return value.toDouble();
    return 0.0;
  }
  final int id;
  final int? mewacoTypeId;
  final String? typeName;
  final String? description;
  final DateTime contributionDate;
  final double amount;
  final String paymentStatus;
  final String? paymentMethod;
  final String? txRef;
  final String? chapaReference;
  final String? transactionId;
  final DateTime createdAt;
  final DateTime? paidAt;

  MewacoContribution({
    required this.id,
    this.mewacoTypeId,
    this.typeName,
    this.description,
    required this.contributionDate,
    required this.amount,
    required this.paymentStatus,
    this.paymentMethod,
    this.txRef,
    this.chapaReference,
    this.transactionId,
    required this.createdAt,
    this.paidAt,
  });

  factory MewacoContribution.fromJson(Map<String, dynamic> json) {
    return MewacoContribution(
      id: json['id'] as int,
      mewacoTypeId: json['mewaco_type_id'] as int?,
      typeName: json['type_name'] as String?,
      description: json['description'] as String?,
      contributionDate: DateTime.parse(json['contribution_date'] as String),
      amount: _parseAmount(json['amount']),
      paymentStatus: json['payment_status'] as String? ?? 'Pending',
      paymentMethod: json['payment_method'] as String?,
      txRef: json['tx_ref'] as String?,
      chapaReference: json['chapa_reference'] as String?,
      transactionId: json['transaction_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      paidAt: json['paid_at'] != null
          ? DateTime.parse(json['paid_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'mewaco_type_id': mewacoTypeId,
      'type_name': typeName,
      'description': description,
      'contribution_date': contributionDate.toIso8601String(),
      'amount': amount,
      'payment_status': paymentStatus,
      'payment_method': paymentMethod,
      'tx_ref': txRef,
      'chapa_reference': chapaReference,
      'transaction_id': transactionId,
      'created_at': createdAt.toIso8601String(),
      'paid_at': paidAt?.toIso8601String(),
    };
  }

  String get statusDisplay {
    switch (paymentStatus.toLowerCase()) {
      case 'completed':
      case 'paid':
        return 'Completed';
      case 'pending':
        return 'Pending';
      case 'failed':
        return 'Failed';
      default:
        return paymentStatus;
    }
  }

  @override
  String toString() => 'MewacoContribution(id: $id, amount: $amount, status: $paymentStatus)';
}

