import 'dart:async';
import '../../../core/network/dio_client.dart';
import '../../../core/session/session_manager.dart';
import '../../../core/constants/dummy_data.dart';
import '../models/history_booking_model.dart';

class HistoryService {
  final DioClient _client = DioClient();

  Future<List<HistoryBookingModel>> getHistoryBookings() async {
    final providerId = SessionManager.instance.providerId;
    if (providerId == null) return DummyData.history;

    try {
      final response = await _client.get('/api/provider/$providerId/bookings');
      final List<dynamic> data = response.data;
      return data.map((json) {
        final bookingId = json['booking_id'].toString();
        final rawStatus = json['status'].toString();
        final finalCost = json['final_cost'] != null ? (json['final_cost'] as num).toDouble() : null;
        final rating = json['customer_rating'] != null ? (json['customer_rating'] as num).toDouble() : null;
        final visitFee = json['visit_fee'] != null ? (json['visit_fee'] as num).toDouble() : 500.0;
        final minCost = json['estimated_cost_min'];
        final maxCost = json['estimated_cost_max'];
        final estimateRange = minCost != null && maxCost != null 
            ? 'Rs. $minCost - $maxCost'
            : 'Rs. 0';

        String status = 'Pending';
        if (rawStatus == 'completed') {
          status = 'Completed';
        } else if (rawStatus == 'cancelled') {
          status = 'Cancelled';
        } else if (rawStatus == 'accepted') {
          status = 'Accepted';
        } else if (rawStatus == 'confirmed') {
          status = 'Confirmed';
        } else if (rawStatus == 'en_route') {
          status = 'En Route';
        } else if (rawStatus == 'arrived') {
          status = 'Arrived';
        }

        return HistoryBookingModel(
          id: bookingId,
          serviceType: _fromApiServiceType(json['service_type'] ?? ''),
          customerLocation: json['customer_city'] ?? 'Islamabad',
          date: json['created_at'] != null 
              ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
              : DateTime.now(),
          status: status,
          visitFee: visitFee,
          estimateRange: estimateRange,
          finalEarning: finalCost,
          rating: rating,
        );
      }).toList();
    } catch (e) {
      return [];
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
