import '../../../core/network/dio_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../core/session/session_manager.dart';
import '../../../core/constants/dummy_data.dart';
import '../models/profile_model.dart';

class ProfileService {
  final DioClient _client = DioClient();

  /// GET /api/provider/{id}/profile
  Future<ProviderProfileModel> getProfile() async {
    final providerId = SessionManager.instance.providerId;

    // Fallback to dummy data if no session (dev/preview mode)
    if (providerId == null) return DummyData.profile;

    final response = await _client.get(ApiEndpoints.getProfile(providerId));
    final data = response.data as Map<String, dynamic>;
    return _mapToModel(data, providerId);
  }

  /// PUT /api/provider/{id}/profile
  /// Body: { name, phone, years_experience, is_active, visit_fee, bio, area, cnic, service_type }
  Future<bool> updateProfile(ProviderProfileModel updatedProfile) async {
    // Prioritize the ID from the profile object itself
    final providerId = updatedProfile.id;

    await _client.put(
      ApiEndpoints.updateProfile(providerId),
      data: {
        'name': updatedProfile.fullName,
        'phone': updatedProfile.phoneNumber,
        'years_experience': updatedProfile.experienceYears,
        'is_active': updatedProfile.isAvailable,
        'visit_fee': updatedProfile.visitFee.toInt(),
        'bio': updatedProfile.bio,
        'cnic': updatedProfile.cnic,
        'service_type': _toApiServiceType(updatedProfile.serviceCategory),
        'city': updatedProfile.serviceAreas.isNotEmpty
            ? updatedProfile.serviceAreas.first.toLowerCase()
            : '',
        'area': updatedProfile.serviceAreas.length > 1
            ? updatedProfile.serviceAreas[1]
            : '',
      },
    );
    return true;
  }

  /// Maps the raw API response to our [ProviderProfileModel]
  ProviderProfileModel _mapToModel(
      Map<String, dynamic> data, String providerId) {
    // Priority 1: Use average_rating directly if available
    // Priority 2: Calculate from total/count
    // Priority 3: Use other common field names
    double rating = 0.0;
    
    if (data['average_rating'] != null) {
      rating = (data['average_rating'] as num).toDouble();
    } else {
      final ratingTotal = data['rating_total'] ?? 0;
      final ratingCount = data['rating_count'] ?? 0;

      if (ratingCount is num && ratingCount > 0 && data['rating_total'] != null) {
        rating = (ratingTotal as num).toDouble() / (ratingCount as num).toDouble();
      } else {
        final rawRating = data['rating'] ?? data['avg_rating'] ?? 0;
        if (rawRating is num) {
          rating = rawRating.toDouble();
        }
      }
    }

    // Use id from response if available, otherwise use providerId
    final id = data['id']?.toString() ?? providerId;

    return ProviderProfileModel(
      id: id,
      fullName: data['name'] ?? '',
      phoneNumber: data['phone'] ?? '',
      profilePhotoUrl: data['profile_pic_url'] ?? '',
      rating: rating,
      bio: data['bio'] ?? '',
      experienceYears: data['years_experience'] ?? 0,
      cnic: data['cnic'] ?? '',
      serviceCategory: _fromApiServiceType(data['service_type'] ?? ''),
      visitFee: (data['visit_fee'] ?? 0).toDouble(),
      serviceAreas: _parseAreas(data),
      isAvailable: data['is_active'] ?? true,
      workingDays: const [
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'
      ],
      startTime: '09:00 AM',
      endTime: '08:00 PM',
    );
  }

  List<String> _parseAreas(Map<String, dynamic> data) {
    final city = data['city'] as String?;
    final area = data['area'] as String?;
    final areas = <String>[];
    if (city != null && city.isNotEmpty) areas.add(_capitalize(city));
    if (area != null && area.isNotEmpty) areas.add(area);
    return areas.isEmpty ? ['Islamabad'] : areas;
  }

  String _capitalize(String s) =>
      s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);

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
