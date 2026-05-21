import 'package:flutter/foundation.dart';
import '../../../core/network/dio_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../core/session/session_manager.dart';
import '../../../core/constants/dummy_data.dart';
import '../../../shared/models/service_booking.dart';
import '../../../shared/widgets/status_chip.dart';

class ActiveBookingsService {
  final DioClient _client = DioClient();

  /// GET /api/provider/{id}/active-job
  /// Returns the current active booking for the provider.
  Future<List<ServiceBooking>> getActiveBookings() async {
    final providerId = SessionManager.instance.providerId;

    // Fallback to dummy data in preview/dev mode
    if (providerId == null) return DummyData.activeBookings;

    try {
      final response =
          await _client.get(ApiEndpoints.getActiveJob(providerId));

      final data = response.data;

      // API returns a single booking object or null/empty
      if (data == null) return [];
      if (data is Map<String, dynamic>) {
        final booking = _mapToBooking(data);
        return booking != null ? [booking] : [];
      }
      if (data is List) {
        return data
            .whereType<Map<String, dynamic>>()
            .map(_mapToBooking)
            .whereType<ServiceBooking>()
            .toList();
      }
    } catch (e) {
      // Handle 404 specifically as "No Active Bookings"
      if (e.toString().contains('404')) {
        return [];
      }
      // Log other errors but don't crash
      debugPrint('Error fetching active bookings: $e');
    }
    return [];
  }

  ServiceBooking? _mapToBooking(Map<String, dynamic>? data) {
    if (data == null) return null;
    return ServiceBooking(
      id: data['id']?.toString() ?? '',
      serviceType: _fromApiServiceType(data['service_type'] ?? ''),
      customerName: data['customer_name'] ?? data['customer']?['name'] ?? 'Customer',
      address: data['address'] ?? data['location'] ?? '',
      scheduledTime: data['scheduled_time'] != null
          ? DateTime.tryParse(data['scheduled_time'].toString()) ??
              DateTime.now()
          : DateTime.now(),
      status: _parseStatus(data['status']),
      price: (data['visit_fee'] ?? data['price'] ?? 0).toDouble(),
    );
  }

  BookingStatus _parseStatus(dynamic raw) {
    switch (raw?.toString()) {
      case 'accepted':
        return BookingStatus.accepted;
      case 'en_route':
      case 'arrived':
        return BookingStatus.inProgress;
      case 'completed':
        return BookingStatus.completed;
      case 'cancelled':
        return BookingStatus.cancelled;
      default:
        return BookingStatus.pending;
    }
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
