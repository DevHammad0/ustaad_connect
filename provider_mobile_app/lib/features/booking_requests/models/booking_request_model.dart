class BookingRequest {
  final String id;
  final String serviceType;
  final String issueSummary;
  final String issueDescription;
  final String customerLocation;
  final String requestedTime;
  final double visitFee;
  final String status;
  final String? customerNote;
  final bool isNew;

  const BookingRequest({
    required this.id,
    required this.serviceType,
    required this.issueSummary,
    required this.issueDescription,
    required this.customerLocation,
    required this.requestedTime,
    required this.visitFee,
    required this.status,
    this.customerNote,
    this.isNew = true,
  });

  BookingRequest copyWith({
    String? id,
    String? serviceType,
    String? issueSummary,
    String? issueDescription,
    String? customerLocation,
    String? requestedTime,
    double? visitFee,
    String? status,
    String? customerNote,
    bool? isNew,
  }) {
    return BookingRequest(
      id: id ?? this.id,
      serviceType: serviceType ?? this.serviceType,
      issueSummary: issueSummary ?? this.issueSummary,
      issueDescription: issueDescription ?? this.issueDescription,
      customerLocation: customerLocation ?? this.customerLocation,
      requestedTime: requestedTime ?? this.requestedTime,
      visitFee: visitFee ?? this.visitFee,
      status: status ?? this.status,
      customerNote: customerNote ?? this.customerNote,
      isNew: isNew ?? this.isNew,
    );
  }
}
