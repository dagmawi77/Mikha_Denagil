# Mikha Denagil Mobile App

Flutter mobile application for Mikha Denagil Spiritual Society members.

## 📱 Features

- ✅ Member authentication (username/password)
- ✅ View posts and announcements filtered by section
- ✅ Event notifications with dates
- ✅ Read/Unread tracking
- ✅ Filter by type (Events/Announcements)
- ✅ Attachment viewing (images, PDFs, documents)
- ✅ Pull-to-refresh
- ✅ Amharic language support
- ✅ Green theme matching web app

## 🚀 Quick Start

### 1. Prerequisites
- Flutter SDK 3.0.0+
- Android Studio / Xcode
- Device or emulator

### 2. Install Dependencies
```bash
flutter pub get
```

### 3. Configure API URL

Edit `lib/config/api_config.dart`:
```dart
static const String baseUrl = 'http://YOUR_SERVER_IP:5001';
```

### 4. Run
```bash
flutter run
```

### 5. Build APK
```bash
flutter build apk --release
```

## 📁 Project Structure

```
lib/
├── main.dart                 # App entry point
├── config/
│   └── api_config.dart      # API configuration
├── models/
│   ├── member.dart          # Member model
│   └── post.dart            # Post model
├── services/
│   └── api_service.dart     # API integration
├── providers/
│   └── auth_provider.dart   # State management
├── screens/
│   ├── login_screen.dart    # Login UI
│   ├── dashboard_screen.dart # Main feed
│   └── post_details_screen.dart # Post view
└── utils/
    └── app_localizations.dart # Translations
```

## 🔧 Configuration

### API Endpoints
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/posts` - Get posts
- `GET /api/v1/posts/<id>` - Post details
- `POST /api/v1/posts/<id>/mark-read` - Mark read
- `GET /api/v1/posts/stats` - Statistics

### Colors
- Primary: #14860C (Green)
- Secondary: #106b09 (Dark Green)

## 📝 Login Credentials

Use existing member accounts:
- Username: Member's username
- Password: Member's password

## 🌍 Languages

- English
- Amharic (አማርኛ)

## 📱 Screens

1. **Login** - Authentication
2. **Dashboard** - Posts feed with stats
3. **Post Details** - Full post view

## 🔒 Security

- JWT token authentication
- Secure storage
- Auto-logout
- Token refresh

## 📦 Dependencies

See `pubspec.yaml` for full list.

Key packages:
- `provider` - State management
- `http` - API calls
- `flutter_secure_storage` - Token storage
- `cached_network_image` - Image caching

## 🐛 Troubleshooting

### Connection Error
- Check API URL is correct
- Verify phone and server on same network
- Test: http://YOUR_IP:5001/api/v1/health

### Build Errors
```bash
flutter clean
flutter pub get
flutter run
```

## 📄 License

Proprietary - Mikha Denagil Spiritual Society

## 👨‍💻 Development

Developed for Mikha Denagil Spiritual Society
Version: 1.0.0

