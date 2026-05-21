class HistoryBookingModel {
  final String id;
  final String serviceType;
  final String customerLocation;
  final DateTime date;
  final String status;
  final double visitFee;
  final String estimateRange;
  final double? finalEarning;
  final double? rating;

  const HistoryBookingModel({
    required this.id,
    required this.serviceType,
    required this.customerLocation,
    required this.date,
    required this.status,
    required this.visitFee,
    required this.estimateRange,
    this.finalEarning,
    this.rating,
  });
}
