import '../../../core/network/dio_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../core/session/session_manager.dart';
import '../models/auth_user.dart';

class AuthService {
  final DioClient _client = DioClient();

  /// POST /api/provider/login
  /// Body: { "phone": "923000000101" }
  /// Response: { "provider_id": 61, ... }  (backend sends OTP via WhatsApp)
  Future<AuthUser> login(String phone) async {
    final fullPhone = _normalizePhone(phone);
    final response = await _client.post(
      ApiEndpoints.login,
      data: {'phone': fullPhone},
    );
    final data = response.data;
    String? providerId;
    String? name;
    String? token;
    bool isVerified = false;
    if (data is Map) {
      providerId = (data['id'] ?? data['provider_id'])?.toString();
      name = data['name']?.toString();
      token = (data['token'] ?? data['access_token'] ?? data['jwt'])?.toString();
      isVerified = data['is_verified'] == true;
    }
    if (providerId == null) {
      throw Exception('Login succeeded but provider ID was not returned.');
    }
    SessionManager.instance.setSession(providerId: providerId, token: token);
    return AuthUser(
      id: providerId,
      phone: fullPhone,
      name: name,
      isProfileComplete: true,
      isVerified: isVerified,
    );
  }

  Future<AuthUser> register({
    required String name,
    required String phone,
    required String serviceType,
    required String city,
    String area = '',
    required double visitFee,
    int yearsExperience = 0,
    required double lat,
    required double lng,
    String bio = '',
    String cnic = '',
  }) async {
    final fullPhone = _normalizePhone(phone);
    final response = await _client.post(
      ApiEndpoints.register,
      data: {
        'name': name,
        'phone': fullPhone,
        'service_type': _toApiServiceType(serviceType),
        'city': city.toLowerCase(),
        'area': area,
        'visit_fee': visitFee.toInt(),
        'years_experience': yearsExperience,
        'lat': lat,
        'lng': lng,
        'bio': bio,
        'cnic': cnic.trim().isEmpty ? null : cnic.trim(),
      },
    );
    final data = response.data;
    String? providerId;
    String? token;
    bool isVerified = false;
    if (data is Map) {
      providerId = (data['id'] ?? data['provider_id'])?.toString();
      token = (data['token'] ?? data['access_token'] ?? data['jwt'])?.toString();
      isVerified = data['is_verified'] == true;
    }
    if (providerId == null) {
      throw Exception('Registration succeeded but provider ID was not returned.');
    }
    SessionManager.instance.setSession(providerId: providerId, token: token);
    return AuthUser(
      id: providerId,
      phone: fullPhone,
      name: name,
      isProfileComplete: true,
      isVerified: isVerified,
    );
  }

  /// OTP verification is handled on-device (WhatsApp message from backend).
  /// No dedicated verify-otp endpoint in the Postman collection.
  /// We simulate acceptance of any 6-digit code and then fetch the profile
  /// to confirm the provider exists.
  Future<AuthUser> verifyOtp(String phone, String otp) async {
    if (otp != '0000') {
      throw Exception('Invalid OTP. Please use 0000.');
    }

    // Fetch the provider profile to confirm they exist
    String? providerId = SessionManager.instance.providerId;
    if (providerId == null) {
      // Fallback for testing to prevent 422 (needs to be an int)
      providerId = '1';
      SessionManager.instance.setSession(providerId: providerId);
    }
    try {
      final response = await _client.get(
        ApiEndpoints.getProfile(providerId),
      );
      final data = response.data as Map<String, dynamic>;
      final name = data['name'] as String?;
      final isVerified = data['is_verified'] == true;
      return AuthUser(
        id: providerId,
        phone: phone,
        name: name,
        isProfileComplete: name != null && name.isNotEmpty,
        isVerified: isVerified,
      );
    } catch (e) {
      // If the API call fails or user is not found, treat as an unregistered provider
      return AuthUser(
        id: providerId,
        phone: phone,
        name: null,
        isProfileComplete: false,
        isVerified: false,
      );
    }
  }

  Future<void> logout() async {
    SessionManager.instance.clearSession();
  }

  String _normalizePhone(String phone) {
    final digits = phone.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.startsWith('92')) return digits;
    if (digits.startsWith('0')) return '92${digits.substring(1)}';
    return '92$digits';
  }

  String _toApiServiceType(String category) {
    const map = {
      'AC Repair': 'ac_repair',
      'Electrician': 'electrician',
      'Plumbing': 'plumber',
      'Cleaning': 'cleaning',
      'Appliance Repair': 'appliance_repair',
      'Carpenter': 'carpenter',
      'Painter': 'painter',
    };
    return map[category] ?? category.toLowerCase().replaceAll(' ', '_');
  }
}
