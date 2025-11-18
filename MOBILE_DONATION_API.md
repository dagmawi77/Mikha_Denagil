# 📱 Mobile Donation API Documentation

## Overview
Complete donation functionality for mobile apps (Flutter/React Native) with Chapa payment gateway integration.

## Base URL
```
http://your-server-ip:5001/api/v1
```

## Authentication
All donation endpoints (except `/donations/types`) require JWT authentication.

**Header:**
```
Authorization: Bearer <your_jwt_token>
```

---

## 📋 API Endpoints

### 1. Get Donation Types
**GET** `/donations/types`

**Description:** Get all active donation types available for donations.

**Authentication:** Not required

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "General Donation",
      "name_amharic": "አጠቃላይ ለግስና",
      "description": "General purpose donations",
      "description_amharic": "አጠቃላይ ዓላማ ለግስና",
      "status": "active"
    }
  ]
}
```

---

### 2. Initiate Donation Payment
**POST** `/donations/initiate`

**Description:** Initiate a donation payment via Chapa. Returns checkout URL for mobile app to open.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "donation_type_id": 1,
  "amount": 1000.00,
  "donor_name": "John Doe",
  "christian_name": "ሃይለ መስቀል",
  "donor_email": "john@example.com",  // Optional
  "donor_phone": "+251911234567",      // Optional
  "is_anonymous": false
}
```

**Required Fields:**
- `donation_type_id` (integer)
- `amount` (float)

**Optional Fields:**
- `donor_name` (string) - Uses member name if not provided
- `christian_name` (string)
- `donor_email` (string) - Uses member email if not provided
- `donor_phone` (string) - Uses member phone if not provided
- `is_anonymous` (boolean)

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "donation_id": 123,
    "checkout_url": "https://checkout.chapa.co/checkout/payment/...",
    "tx_ref": "MD_A2DD4BE5B67B45D5",
    "amount": 1000.00,
    "currency": "ETB"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Amount must be between 10 and 1000000 ETB"
}
```

**Mobile App Flow:**
1. Call this endpoint with donation details
2. Receive `checkout_url` in response
3. Open `checkout_url` in mobile WebView or browser
4. User completes payment on Chapa
5. Chapa redirects/callbacks to your server
6. Use `/donations/verify/<tx_ref>` to check payment status

---

### 3. Verify Donation Payment
**GET** `/donations/verify/<tx_ref>`

**Description:** Verify payment status from Chapa and update donation record.

**Authentication:** Required (Bearer token)

**Parameters:**
- `tx_ref` (path parameter) - Transaction reference from initiate response

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "donation": {
      "id": 123,
      "amount": 1000.00,
      "currency": "ETB",
      "payment_status": "Completed",
      "tx_ref": "MD_A2DD4BE5B67B45D5",
      "created_at": "2025-11-17T15:20:00",
      "paid_at": "2025-11-17T15:21:00",
      "donation_type_name": "General Donation",
      "donation_type_name_amharic": "አጠቃላይ ለግስና"
    },
    "chapa_status": "successful",
    "payment_status": "Completed"
  }
}
```

**Usage:**
- Call this endpoint after user completes payment
- Poll this endpoint if needed to check payment status
- Payment status is automatically updated to "Completed" (since transactions are auto-deducted)

---

### 4. Get My Donation History
**GET** `/donations/my-history`

**Description:** Get donation history for the logged-in member.

**Authentication:** Required (Bearer token)

**Query Parameters:**
- `limit` (optional, default: 100) - Number of records to return
- `offset` (optional, default: 0) - Pagination offset

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "amount": 1000.00,
      "currency": "ETB",
      "payment_status": "Completed",
      "payment_method": "Chapa",
      "tx_ref": "MD_A2DD4BE5B67B45D5",
      "chapa_reference": "MD_A2DD4BE5B67B45D5",
      "created_at": "2025-11-17T15:20:00",
      "paid_at": "2025-11-17T15:21:00",
      "donor_name": "John Doe",
      "christian_name": "ሃይለ መስቀል",
      "donation_type_name": "General Donation",
      "donation_type_name_amharic": "አጠቃላይ ለግስና"
    }
  ]
}
```

---

### 5. Get Donation Details
**GET** `/donations/<donation_id>`

**Description:** Get specific donation details by ID.

**Authentication:** Required (Bearer token)

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "donation_type_id": 1,
    "donor_name": "John Doe",
    "christian_name": "ሃይለ መስቀል",
    "donor_email": "john@example.com",
    "donor_phone": "+251911234567",
    "amount": 1000.00,
    "currency": "ETB",
    "payment_status": "Completed",
    "payment_method": "Chapa",
    "tx_ref": "MD_A2DD4BE5B67B45D5",
    "transaction_id": "chapa_txn_123",
    "created_at": "2025-11-17T15:20:00",
    "paid_at": "2025-11-17T15:21:00",
    "donation_type_name": "General Donation",
    "donation_type_name_amharic": "አጠቃላይ ለግስና"
  }
}
```

---

## 🔄 Complete Mobile App Flow

### Step 1: Get Donation Types
```dart
// Flutter example
final response = await http.get(
  Uri.parse('$baseUrl/donations/types'),
);
final data = jsonDecode(response.body);
List<DonationType> types = (data['data'] as List)
    .map((t) => DonationType.fromJson(t))
    .toList();
```

### Step 2: Initiate Donation
```dart
final response = await http.post(
  Uri.parse('$baseUrl/donations/initiate'),
  headers: {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  },
  body: jsonEncode({
    'donation_type_id': selectedTypeId,
    'amount': amount,
    'donor_name': userName,
    'christian_name': christianName,
    'donor_email': email, // Optional
    'donor_phone': phone,  // Optional
    'is_anonymous': false,
  }),
);

final result = jsonDecode(response.body);
if (result['success']) {
  String checkoutUrl = result['data']['checkout_url'];
  String txRef = result['data']['tx_ref'];
  
  // Open checkout URL in WebView
  await launchUrl(Uri.parse(checkoutUrl));
}
```

### Step 3: Verify Payment (After User Completes Payment)
```dart
// Poll or call after payment completion
final response = await http.get(
  Uri.parse('$baseUrl/donations/verify/$txRef'),
  headers: {
    'Authorization': 'Bearer $token',
  },
);

final result = jsonDecode(response.body);
if (result['success']) {
  String status = result['data']['payment_status'];
  if (status == 'Completed') {
    // Show success message
    showSuccessDialog();
  }
}
```

### Step 4: Get Donation History
```dart
final response = await http.get(
  Uri.parse('$baseUrl/donations/my-history'),
  headers: {
    'Authorization': 'Bearer $token',
  },
);

final result = jsonDecode(response.body);
List<Donation> donations = (result['data'] as List)
    .map((d) => Donation.fromJson(d))
    .toList();
```

---

## 🔐 Payment Status Values

- **Completed**: Payment successful (auto-deducted from payer)
- **Paid**: Payment received
- **Failed**: Payment failed
- **Pending**: Automatically converted to "Completed" (since transactions are auto-deducted)

---

## ⚙️ Configuration

Donation settings are managed in the admin dashboard:
- `/admin/donation/settings`

**Key Settings:**
- `min_donation_amount`: Minimum donation (default: 10 ETB)
- `max_donation_amount`: Maximum donation (default: 1,000,000 ETB)
- `default_currency`: Currency code (default: ETB)
- `chapa_secret_key`: Chapa secret key (from environment or database)
- `chapa_public_key`: Chapa public key (for mobile SDK)

---

## 📱 Mobile App Integration Tips

1. **WebView Integration:**
   - Use `flutter_inappwebview` or `webview_flutter` package
   - Handle URL callbacks to detect payment completion
   - Monitor WebView navigation to catch return URLs

2. **Payment Verification:**
   - Poll `/donations/verify/<tx_ref>` every 2-3 seconds after opening checkout
   - Stop polling when status is "Completed" or "Failed"
   - Show loading indicator during verification

3. **Error Handling:**
   - Handle network errors gracefully
   - Show user-friendly error messages
   - Allow retry on failure

4. **Offline Support:**
   - Cache donation types locally
   - Queue donation requests if offline
   - Sync when connection restored

---

## 🧪 Testing

**Test Credentials (Chapa Test Mode):**
- Public Key: `CHAPUBK_TEST-L0hqsaiWfP8JXJMXBqFyRSRbyJHp2quS`
- Secret Key: `CHASECK_TEST-Gm6uD4CijZ2RSUrYPWEyV2i56gHU1nQp`

**Test Card Numbers:**
- Use Chapa test card numbers from their documentation
- All test payments will be marked as "Completed"

---

## 📞 Support

For issues or questions:
- Check server logs for detailed error messages
- Verify Chapa credentials are configured correctly
- Ensure JWT token is valid and not expired
- Check donation settings in admin dashboard

---

**Last Updated:** November 2025
**API Version:** 1.0

