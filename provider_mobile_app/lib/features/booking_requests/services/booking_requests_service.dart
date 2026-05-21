import 'dart:async';
import '../models/booking_request_model.dart';

import '../../../core/constants/dummy_data.dart';

class BookingRequestsService {
  // TODO: Connect real FastAPI backend later using Dio
  
  // Future API Endpoint: GET /provider/requests
  Future<List<BookingRequest>> getRequests() async {
    await Future.delayed(const Duration(seconds: 1)); // Simulate network latency

    return DummyData.requests;
  }

  // Future API Endpoint: GET /provider/requests/{id}
  Future<BookingRequest?> getRequestById(String id) async {
    await Future.delayed(const Duration(seconds: 1));
    final requests = await getRequests();
    try {
      return requests.firstWhere((req) => req.id == id);
    } catch (e) {
      return null;
    }
  }
}
