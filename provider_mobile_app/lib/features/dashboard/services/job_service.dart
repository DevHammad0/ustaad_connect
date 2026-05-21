import 'package:dio/dio.dart';
import '../../../core/network/dio_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../core/network/network_exceptions.dart';
import '../../../core/session/session_manager.dart';
import '../../../shared/models/service_booking.dart';
import '../../../shared/widgets/status_chip.dart';

class JobService {
  final DioClient _client = DioClient();

  Future<ServiceBooking?> getActiveJob() async {
    final providerId = SessionManager.instance.providerId;
    if (providerId == null) return null;

    try {
      final response = await _client.get(
        ApiEndpoints.getActiveJob(providerId),
      );
      final data = response.data;
      if (data == null) return null;

      final rawStatus = data['status']?.toString() ?? 'pending';
      // Backend returns single active job dict or throws 404
      return ServiceBooking(
        id: (data['booking_id'] ?? data['id']).toString(),
        customerName: data['customer_name']?.toString() ?? 'Customer',
        customerPhone: data['customer_phone']?.toString() ?? '',
        serviceType: _fromApiServiceType(data['service_type']?.toString() ?? ''),
        issueDescription: data['issue']?.toString() ?? 'No issue provided',
        address: data['customer_city']?.toString() ?? 'Unknown Location',
        latitude: _toDouble(data['customer_lat']),
        longitude: _toDouble(data['customer_lng']),
        scheduledTime: data['created_at'] != null
            ? DateTime.tryParse(data['created_at'].toString()) ?? DateTime.now()
            : DateTime.now(),
        status: _parseStatus(rawStatus),
        apiStatus: rawStatus,
        price: (data['visit_fee'] ?? data['estimated_cost_min'] ?? 0).toDouble(),
      );
    } catch (e) {
      if (e is NetworkExceptions && e.statusCode == 404) {
        return null; // No active job is a valid state
      }
      if (e is DioException && e.response?.statusCode == 404) {
        return null;
      }
      // If the error message itself contains 404 or "not found"
      // (sometimes happens if catch blocks aren't perfect)
      if (e.toString().contains('404') || e.toString().toLowerCase().contains('not found')) {
        return null;
      }
      rethrow;
    }
  }

  Future<void> acceptJob(String bookingId, double minCost, double maxCost) async {
    await _client.post(
      ApiEndpoints.acceptBooking(bookingId),
      data: {
        'estimated_cost_min': minCost,
        'estimated_cost_max': maxCost,
      },
    );
  }

  Future<void> updateStatus(String bookingId, String status) async {
    await _client.post(
      ApiEndpoints.updateBookingStatus(bookingId),
      data: {'status': status},
    );
  }

  Future<void> completeJob(String bookingId, double finalCost) async {
    await _client.post(
      ApiEndpoints.completeBooking(bookingId),
      data: {'final_cost': finalCost},
    );
  }

  Future<void> cancelJob(String bookingId) async {
    await _client.post(
      ApiEndpoints.cancelBooking(bookingId),
      data: {'cancelled_by': 'provider'},
    );
  }

  BookingStatus _parseStatus(dynamic raw) {
    switch (raw?.toString()) {
      case 'accepted':
      case 'confirmed':
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

  double? _toDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }
}
