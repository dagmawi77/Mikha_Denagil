# ✅ Chapa Payment Gateway - Test Keys Configured

## 🔑 Configured Test Credentials

Your Chapa test keys have been successfully configured in the system:

- **Public Key**: `CHAPUBK_TEST-L0hqsaiWfP8JXJMXBqFyRSRbyJHp2quS`
- **Secret Key**: `CHASECK_TEST-Gm6uD4CijZ2RSUrYPWEyV2i56gHU1nQp`
- **Encrypted Key**: `uFZFepcrugS4sGA7ofC6sX77` (stored for reference)

## 📍 Where Keys Are Stored

The keys are stored in the `donation_settings` table in your database. They can be accessed via:

1. **Admin Dashboard**: `/admin/donation/settings`
2. **Environment Variables** (recommended for production):
   ```bash
   export CHAPA_SECRET_KEY="CHASECK_TEST-Gm6uD4CijZ2RSUrYPWEyV2i56gHU1nQp"
   export CHAPA_PUBLIC_KEY="CHAPUBK_TEST-L0hqsaiWfP8JXJMXBqFyRSRbyJHp2quS"
   ```

## 🧪 Testing Donations

### 1. Test via Public Website
- Visit: `http://localhost:5001/donation`
- Fill in donation form
- Use test card numbers from Chapa documentation
- Complete payment flow

### 2. Test via Mobile API
```bash
# Get donation types
curl http://localhost:5001/api/v1/donations/types

# Initiate donation (requires JWT token)
curl -X POST http://localhost:5001/api/v1/donations/initiate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "donation_type_id": 1,
    "amount": 100,
    "donor_email": "test@example.com",
    "donor_name": "Test Donor"
  }'
```

### 3. Test Payment Flow
1. Go to `/donation` page
2. Select donation type
3. Enter amount (minimum 10 ETB)
4. Fill donor information
5. Click "Donate Now"
6. You'll be redirected to Chapa test payment page
7. Use test card: `4242 4242 4242 4242`
8. Any future expiry date and CVV
9. Complete payment

## 🔒 Security Notes

1. **Test Keys**: These are TEST keys. They will not process real payments.
2. **Production**: When ready for production:
   - Get production keys from Chapa dashboard
   - Update via `/admin/donation/settings` OR
   - Set environment variables
3. **Environment Variables**: For better security, use environment variables instead of storing in database:
   ```bash
   # Windows PowerShell
   $env:CHAPA_SECRET_KEY="CHASECK_TEST-Gm6uD4CijZ2RSUrYPWEyV2i56gHU1nQp"
   $env:CHAPA_PUBLIC_KEY="CHAPUBK_TEST-L0hqsaiWfP8JXJMXBqFyRSRbyJHp2quS"
   
   # Linux/Mac
   export CHAPA_SECRET_KEY="CHASECK_TEST-Gm6uD4CijZ2RSUrYPWEyV2i56gHU1nQp"
   export CHAPA_PUBLIC_KEY="CHAPUBK_TEST-L0hqsaiWfP8JXJMXBqFyRSRbyJHp2quS"
   ```

## 📋 Chapa Test Card Numbers

For testing payments, use these test card numbers:

- **Visa**: `4242 4242 4242 4242`
- **Mastercard**: `5555 5555 5555 4444`
- **Any future expiry date** (e.g., 12/25)
- **Any 3-digit CVV** (e.g., 123)

## 🔄 Callback URL Configuration

The callback URL is automatically set to:
- `http://your-domain.com/donation/callback`

For local testing, you may need to use a service like ngrok to expose your local server:
```bash
ngrok http 5001
# Then update callback_url in settings with the ngrok URL
```

## ✅ Next Steps

1. ✅ Test keys configured
2. ✅ Test donation flow on public website
3. ✅ Verify callback handling
4. ✅ Check donation records in admin dashboard (`/admin/donation/records`)
5. ✅ View donation reports (`/reports/donation`)

## 📞 Support

If you encounter any issues:
1. Check Chapa dashboard for transaction logs
2. Check application logs for errors
3. Verify callback URL is accessible
4. Ensure donation module is enabled in settings

---

**Status**: ✅ Ready for Testing
**Environment**: Test Mode
**Last Updated**: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}

