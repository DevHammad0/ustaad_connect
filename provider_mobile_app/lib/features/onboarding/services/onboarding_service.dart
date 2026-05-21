import '../../../core/network/dio_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../core/session/session_manager.dart';
import '../models/onboarding_model.dart';

class OnboardingService {
  final DioClient _client = DioClient();

  /// POST /api/provider/register
  /// Body: { name, phone, service_type, city, area, visit_fee, lat, lng,
  ///         years_experience, bio, cnic }
  Future<bool> saveProviderProfile(
    ProviderProfileDraft profile, {
    required String phone,
    // Default coordinates for Islamabad — update when GPS is integrated
    double lat = 33.6844,
    double lng = 73.0479,
  }) async {
    final body = {
      'name': profile.fullName,
      'phone': phone,
      'service_type': _toApiServiceType(profile.serviceCategory),
      'city': profile.serviceAreas.isNotEmpty
          ? profile.serviceAreas.first.toLowerCase()
          : 'islamabad',
      'area': profile.serviceAreas.length > 1 ? profile.serviceAreas[1] : '',
      'visit_fee': profile.visitFee.toInt(),
      'years_experience': profile.experienceYears,
      'bio': profile.shortBio,
      'cnic': profile.cnic,
      'lat': lat,
      'lng': lng,
    };

    final response = await _client.post(ApiEndpoints.register, data: body);
    final data = response.data;

    // Store provider_id from registration response
    if (data is Map && data['provider_id'] != null) {
      SessionManager.instance.setSession(
        providerId: data['provider_id'].toString(),
      );
    } else if (data is Map && data['id'] != null) {
      SessionManager.instance.setSession(
        providerId: data['id'].toString(),
      );
    }
    return true;
  }

  /// GET /api/provider/{id}/profile
  Future<ProviderProfileDraft?> getMyProfile() async {
    final providerId = SessionManager.instance.providerId;
    if (providerId == null) return null;
    final response =
        await _client.get(ApiEndpoints.getProfile(providerId));
    final data = response.data as Map<String, dynamic>;
    return ProviderProfileDraft(
      fullName: data['name'] ?? '',
      serviceCategory: _fromApiServiceType(data['service_type'] ?? ''),
      visitFee: (data['visit_fee'] ?? 0).toDouble(),
      shortBio: data['bio'] ?? '',
      experienceYears: data['years_experience'] ?? 0,
    );
  }

  // Converts display name → API snake_case service type
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

  // Converts API service type → display name
  String _fromApiServiceType(String apiType) {
    const map = {
      'ac_repair': 'AC Repair',
      'electrician': 'Electrician',
      'plumber': 'Plumbing',
      'cleaning': 'Cleaning',
      'appliance_repair': 'Appliance Repair',
      'carpenter': 'Carpenter',
      'painter': 'Painter',
    };
    return map[apiType] ?? apiType;
  }
}
