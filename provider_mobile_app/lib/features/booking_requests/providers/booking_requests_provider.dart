import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/booking_request_model.dart';
import '../services/booking_requests_service.dart';

final bookingRequestsServiceProvider = Provider<BookingRequestsService>((ref) {
  return BookingRequestsService();
});

final pendingRequestsProvider = FutureProvider<List<BookingRequest>>((ref) async {
  final service = ref.watch(bookingRequestsServiceProvider);
  return service.getRequests();
});

final requestDetailProvider = FutureProvider.family<BookingRequest?, String>((ref, id) async {
  final service = ref.watch(bookingRequestsServiceProvider);
  return service.getRequestById(id);
});
