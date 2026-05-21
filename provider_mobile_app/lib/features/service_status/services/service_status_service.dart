import '../../../core/network/dio_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../models/status_step_model.dart';

class ServiceStatusService {
  final DioClient _client = DioClient();

  /// Maps our local status enum → API status strings
  String _toApiStatus(ServiceStatusStep status) {
    switch (status) {
      case ServiceStatusStep.enRoute:
        return 'en_route';
      case ServiceStatusStep.arrived:
        return 'arrived';
      default:
        return status.name;
    }
  }

  /// POST /api/provider/bookings/{id}/confirm
  /// Called when provider confirms they are starting the job
  Future<bool> confirmBooking(String bookingId) async {
    await _client.post(ApiEndpoints.confirmBooking(bookingId));
    return true;
  }

  /// POST /api/provider/bookings/{id}/status
  /// Body: { "status": "en_route" | "arrived" }
  Future<bool> updateStatus(
      String bookingId, ServiceStatusStep newStatus) async {
    // For completion/cancellation, use dedicated endpoints
    if (newStatus == ServiceStatusStep.completed) {
      return completeBooking(bookingId);
    }
    if (newStatus == ServiceStatusStep.cancelled) {
      return cancelBooking(bookingId);
    }
    if (newStatus == ServiceStatusStep.workStarted) {
      return confirmBooking(bookingId);
    }

    await _client.post(
      ApiEndpoints.updateBookingStatus(bookingId),
      data: {'status': _toApiStatus(newStatus)},
    );
    return true;
  }

  /// POST /api/provider/bookings/{id}/complete
  /// Body: { "final_cost": 2500 }
  Future<bool> completeBooking(String bookingId, {int? finalCost}) async {
    await _client.post(
      ApiEndpoints.completeBooking(bookingId),
      data: {'final_cost': finalCost ?? 0},
    );
    return true;
  }

  /// POST /api/provider/bookings/{id}/cancel
  /// Body: { "cancelled_by": "provider" }
  Future<bool> cancelBooking(String bookingId) async {
    await _client.post(
      ApiEndpoints.cancelBooking(bookingId),
      data: {'cancelled_by': 'provider'},
    );
    return true;
  }

  /// No status-history endpoint in the collection — return default
  Future<List<ServiceStatusStep>> getStatusHistory(String bookingId) async {
    return [ServiceStatusStep.accepted];
  }
}
