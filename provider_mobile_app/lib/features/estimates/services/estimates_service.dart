import '../../../core/network/dio_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../models/estimate_model.dart';

class EstimatesService {
  final DioClient _client = DioClient();

  /// POST /api/provider/bookings/{id}/accept
  /// Body: { "estimated_cost_min": 2000, "estimated_cost_max": 3000 }
  Future<bool> submitEstimate(EstimateModel estimate) async {
    if (estimate.minCost <= 0 || estimate.maxCost <= estimate.minCost) {
      throw Exception('Invalid estimate: min must be > 0 and max must be > min');
    }

    await _client.post(
      ApiEndpoints.acceptBooking(estimate.requestId),
      data: {
        'estimated_cost_min': estimate.minCost.toInt(),
        'estimated_cost_max': estimate.maxCost.toInt(),
      },
    );
    return true;
  }

  /// There is no explicit reject endpoint in the collection.
  /// Cancel the booking on behalf of the provider instead.
  /// POST /api/provider/bookings/{id}/cancel
  Future<bool> rejectRequest(String requestId) async {
    await _client.post(
      ApiEndpoints.cancelBooking(requestId),
      data: {'cancelled_by': 'provider'},
    );
    return true;
  }
}
