enum NotificationType {
  newRequest,
  bookingConfirmed,
  reminder,
  customerCancelled,
  paymentUpdate,
  systemAlert
}

class NotificationModel {
  final String id;
  final NotificationType type;
  final String title;
  final String message;
  final DateTime time;
  final bool isRead;
  final String? relatedBookingId;

  const NotificationModel({
    required this.id,
    required this.type,
    required this.title,
    required this.message,
    required this.time,
    this.isRead = false,
    this.relatedBookingId,
  });

  NotificationModel copyWith({
    String? id,
    NotificationType? type,
    String? title,
    String? message,
    DateTime? time,
    bool? isRead,
    String? relatedBookingId,
  }) {
    return NotificationModel(
      id: id ?? this.id,
      type: type ?? this.type,
      title: title ?? this.title,
      message: message ?? this.message,
      time: time ?? this.time,
      isRead: isRead ?? this.isRead,
      relatedBookingId: relatedBookingId ?? this.relatedBookingId,
    );
  }
}
