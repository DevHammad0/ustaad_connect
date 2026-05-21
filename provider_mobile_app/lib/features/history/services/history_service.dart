import 'dart:async';
import '../models/history_booking_model.dart';

import '../../../core/constants/dummy_data.dart';

class HistoryService {
  // TODO: Connect real FastAPI backend later using Dio
  // Future API Endpoint: GET /provider/bookings/history
  
  Future<List<HistoryBookingModel>> getHistoryBookings() async {
    await Future.delayed(const Duration(seconds: 1)); // Simulate network latency

    return DummyData.history;
  }
}
