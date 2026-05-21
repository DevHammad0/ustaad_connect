import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/history_booking_model.dart';
import '../services/history_service.dart';

enum HistoryFilter {
  all('All'),
  completed('Completed'),
  cancelled('Cancelled'),
  thisWeek('This Week'),
  thisMonth('This Month');

  final String label;
  const HistoryFilter(this.label);
}

final historyServiceProvider = Provider<HistoryService>((ref) {
  return HistoryService();
});

final historyFilterProvider = StateProvider<HistoryFilter>((ref) => HistoryFilter.all);

final rawHistoryProvider = FutureProvider<List<HistoryBookingModel>>((ref) async {
  final service = ref.watch(historyServiceProvider);
  return service.getHistoryBookings();
});

final filteredHistoryProvider = Provider<AsyncValue<List<HistoryBookingModel>>>((ref) {
  final filter = ref.watch(historyFilterProvider);
  final rawData = ref.watch(rawHistoryProvider);

  return rawData.whenData((bookings) {
    final now = DateTime.now();

    return bookings.where((booking) {
      switch (filter) {
        case HistoryFilter.all:
          return true;
        case HistoryFilter.completed:
          return booking.status == 'Completed';
        case HistoryFilter.cancelled:
          return booking.status == 'Cancelled';
        case HistoryFilter.thisWeek:
          // Check if date is within the last 7 days
          final diff = now.difference(booking.date).inDays;
          return diff <= 7;
        case HistoryFilter.thisMonth:
          // Check if date is within the current month/year
          return booking.date.month == now.month && booking.date.year == now.year;
      }
    }).toList();
  });
});

final historyAggregatesProvider = Provider<Map<String, dynamic>>((ref) {
  final filteredData = ref.watch(filteredHistoryProvider);

  return filteredData.maybeWhen(
    data: (bookings) {
      int totalCompleted = 0;
      double totalEarnings = 0;

      for (var booking in bookings) {
        if (booking.status == 'Completed') {
          totalCompleted++;
          totalEarnings += (booking.finalEarning ?? 0.0);
        }
      }

      return {
        'totalJobs': totalCompleted,
        'totalEarnings': totalEarnings,
      };
    },
    orElse: () => {
      'totalJobs': 0,
      'totalEarnings': 0.0,
    },
  );
});
