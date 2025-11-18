/// Donation Model
class Donation {
  final int id;
  final int? donationTypeId;
  final String? donationTypeName;
  final String? donationTypeNameAmharic;
  final String donorName;
  final String? christianName;
  final String? donorEmail;
  final String? donorPhone;
  final double amount;
  final String currency;
  final String paymentStatus;
  final String? paymentMethod;
  final String txRef;
  final String? chapaReference;
  final String? transactionId;
  final DateTime createdAt;
  final DateTime? paidAt;

  Donation({
    required this.id,
    this.donationTypeId,
    this.donationTypeName,
    this.donationTypeNameAmharic,
    required this.donorName,
    this.christianName,
    this.donorEmail,
    this.donorPhone,
    required this.amount,
    this.currency = 'ETB',
    required this.paymentStatus,
    this.paymentMethod,
    required this.txRef,
    this.chapaReference,
    this.transactionId,
    required this.createdAt,
    this.paidAt,
  });

  factory Donation.fromJson(Map<String, dynamic> json) {
    return Donation(
      id: json['id'] as int,
      donationTypeId: json['donation_type_id'] as int?,
      donationTypeName: json['donation_type_name'] as String?,
      donationTypeNameAmharic: json['donation_type_name_amharic'] as String?,
      donorName: json['donor_name'] as String? ?? 'Anonymous',
      christianName: json['christian_name'] as String?,
      donorEmail: json['donor_email'] as String?,
      donorPhone: json['donor_phone'] as String?,
      amount: (json['amount'] is int)
          ? (json['amount'] as int).toDouble()
          : (json['amount'] as num).toDouble(),
      currency: json['currency'] as String? ?? 'ETB',
      paymentStatus: json['payment_status'] as String? ?? 'Pending',
      paymentMethod: json['payment_method'] as String?,
      txRef: json['tx_ref'] as String? ?? '',
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
      'donation_type_id': donationTypeId,
      'donation_type_name': donationTypeName,
      'donation_type_name_amharic': donationTypeNameAmharic,
      'donor_name': donorName,
      'christian_name': christianName,
      'donor_email': donorEmail,
      'donor_phone': donorPhone,
      'amount': amount,
      'currency': currency,
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
  String toString() => 'Donation(id: $id, amount: $amount $currency, status: $paymentStatus)';
}

