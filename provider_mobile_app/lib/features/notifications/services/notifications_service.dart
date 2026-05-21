import 'dart:async';
import '../models/notification_model.dart';

class NotificationsService {
  // TODO: Implement Firebase Cloud Messaging (FCM) Integration later
  // 1. Initialize Firebase
  // 2. Request notification permissions
  // 3. Get FCM Token and POST /notifications/register-device
  // 4. Setup onMessage and onMessageOpenedApp listeners
  // 5. Use flutter_local_notifications for foreground display

  // Future API Endpoint: GET /notifications
  Future<List<NotificationModel>> getNotifications() async {
    await Future.delayed(const Duration(seconds: 1)); // Simulate network latency

    final now = DateTime.now();

    return [
      NotificationModel(
        id: 'NOTIF-1',
        type: NotificationType.newRequest,
        title: 'New Service Request!',
        message: 'You have a new AC Repair request in G-13.',
        time: now.subtract(const Duration(minutes: 5)),
        isRead: false,
        relatedBookingId: 'REQ-1001',
      ),
      NotificationModel(
        id: 'NOTIF-2',
        type: NotificationType.bookingConfirmed,
        title: 'Estimate Accepted',
        message: 'Customer accepted your Rs. 2500 estimate. Prepare for the visit!',
        time: now.subtract(const Duration(hours: 2)),
        isRead: false,
        relatedBookingId: 'BKG-889',
      ),
      NotificationModel(
        id: 'NOTIF-3',
        type: NotificationType.reminder,
        title: 'Upcoming Visit Reminder',
        message: 'You have a Plumbing visit scheduled in 1 hour.',
        time: now.subtract(const Duration(hours: 5)),
        isRead: true,
        relatedBookingId: 'BKG-880',
      ),
      NotificationModel(
        id: 'NOTIF-4',
        type: NotificationType.customerCancelled,
        title: 'Job Cancelled',
        message: 'The customer has cancelled their booking.',
        time: now.subtract(const Duration(days: 1)),
        isRead: true,
        relatedBookingId: 'BKG-850',
      ),
      NotificationModel(
        id: 'NOTIF-5',
        type: NotificationType.systemAlert,
        title: 'Welcome to Ustaad Connect',
        message: 'Your profile is now live! Ensure your availability is turned on to receive jobs.',
        time: now.subtract(const Duration(days: 3)),
        isRead: true,
      ),
    ];
  }

  // Future API Endpoint: PUT /notifications/{id}/read
  Future<void> markAsRead(String id) async {
    await Future.delayed(const Duration(milliseconds: 500));
  }
}
