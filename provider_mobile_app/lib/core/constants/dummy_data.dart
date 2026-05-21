import '../../features/profile/models/profile_model.dart';
import '../../features/booking_requests/models/booking_request_model.dart';
import '../../features/history/models/history_booking_model.dart';
import '../../features/notifications/models/notification_model.dart';
import '../../shared/models/service_booking.dart';
import '../../shared/widgets/status_chip.dart';

class DummyData {
  // Service Categories
  static const List<String> serviceCategories = [
    'AC Repair',
    'Electrician',
    'Plumbing',
    'Cleaning',
    'Appliance Repair',
    'Carpenter',
    'Painter',
  ];

  // Service Areas
  static const List<String> serviceAreas = [
    'Islamabad',
    'Rawalpindi',
    'G-13, Islamabad',
    'F-10, Islamabad',
    'F-11, Islamabad',
    'Bahria Town, Rawalpindi',
    'DHA Phase 2, Islamabad',
    'Peshawar',
    'Hayatabad, Peshawar',
    'University Road, Peshawar',
  ];

  // Dashboard Stats
  static const Map<String, dynamic> dashboardStats = {
    'todaysEarnings': 4500.0,
    'pendingJobs': 2,
    'completionRate': 94,
    'rating': 4.8,
  };

  // Provider Profile
  static ProviderProfileModel get profile => const ProviderProfileModel(
        id: 'PROV-1024',
        fullName: 'Ali AC Services',
        phoneNumber: '+92 300 1234567',
        rating: 4.8,
        bio: 'Expert AC Technician with over 5 years of experience handling split and window ACs across Islamabad and Rawalpindi.',
        experienceYears: 5,
        serviceCategory: 'AC Repair',
        visitFee: 500,
        serviceAreas: ['Islamabad', 'Rawalpindi', 'G-13', 'F-10'],
        isAvailable: true,
        workingDays: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        startTime: '09:00 AM',
        endTime: '08:00 PM',
        notifyNewRequests: true,
        notifyConfirmations: true,
        notifyReminders: true,
        notifyServiceUpdates: true,
      );

  // Booking Requests
  static List<BookingRequest> get requests {
    return const [
      BookingRequest(
        id: 'REQ-1001',
        serviceType: 'AC Repair',
        issueDescription: 'AC cooling nahi kar raha, gas leak lag rahi hai.',
        issueSummary: 'AC cooling nahi kar raha',
        customerLocation: 'G-13/4, Islamabad',
        requestedTime: 'Tomorrow, 10:00 AM',
        visitFee: 500.0,
        status: 'Pending',
      ),
      BookingRequest(
        id: 'REQ-1002',
        serviceType: 'Electrician',
        issueDescription: 'UPS installation and wiring setup.',
        issueSummary: 'UPS installation',
        customerLocation: 'Bahria Town Phase 7, Rawalpindi',
        requestedTime: 'Today, 05:00 PM',
        visitFee: 300.0,
        status: 'Pending',
        customerNote: 'Need this done before evening loadshedding.',
      ),
    ];
  }

  // Active Bookings (using shared ServiceBooking model)
  static List<ServiceBooking> get activeBookings {
    final now = DateTime.now();
    return [
      ServiceBooking(
        id: 'BKG-901',
        serviceType: 'AC Repair',
        customerName: 'Ahmed Khan',
        address: 'F-11 Markaz, Islamabad',
        scheduledTime: now,
        status: BookingStatus.accepted,
        price: 500,
      ),
      ServiceBooking(
        id: 'BKG-902',
        serviceType: 'Plumbing',
        customerName: 'Zainab Ali',
        address: 'DHA Phase 2, Sector A',
        scheduledTime: now.add(const Duration(hours: 3)),
        status: BookingStatus.pending,
        price: 400,
      ),
    ];
  }

  // Booking History
  static List<HistoryBookingModel> get history {
    final now = DateTime.now();
    return [
      HistoryBookingModel(
        id: 'BKG-880',
        serviceType: 'AC Repair',
        customerLocation: 'F-10/2, Islamabad',
        date: now.subtract(const Duration(days: 2)),
        status: 'Completed',
        visitFee: 500,
        estimateRange: 'Rs. 2,000 - 3,500',
        finalEarning: 3000,
        rating: 4.5,
      ),
      HistoryBookingModel(
        id: 'BKG-875',
        serviceType: 'AC Repair',
        customerLocation: 'I-8 Markaz, Islamabad',
        date: now.subtract(const Duration(days: 5)),
        status: 'Cancelled',
        visitFee: 500,
        estimateRange: 'Rs. 1,500 - 2,500',
        finalEarning: null,
        rating: null,
      ),
      HistoryBookingModel(
        id: 'BKG-820',
        serviceType: 'Electrician',
        customerLocation: 'G-11, Islamabad',
        date: now.subtract(const Duration(days: 12)),
        status: 'Completed',
        visitFee: 300,
        estimateRange: 'Rs. 500 - 1,000',
        finalEarning: 800,
        rating: 5.0,
      ),
    ];
  }

  // Notifications
  static List<NotificationModel> get notifications {
    final now = DateTime.now();
    return [
      NotificationModel(
        id: 'NOTIF-1',
        type: NotificationType.newRequest,
        title: 'New AC Repair Request!',
        message: 'You have a new request in G-13. Check details to provide an estimate.',
        time: now.subtract(const Duration(minutes: 10)),
        isRead: false,
        relatedBookingId: 'REQ-1001',
      ),
      NotificationModel(
        id: 'NOTIF-2',
        type: NotificationType.bookingConfirmed,
        title: 'Estimate Accepted',
        message: 'Customer accepted your Rs. 3,500 estimate for AC Repair.',
        time: now.subtract(const Duration(hours: 2)),
        isRead: false,
        relatedBookingId: 'BKG-901',
      ),
      NotificationModel(
        id: 'NOTIF-3',
        type: NotificationType.reminder,
        title: 'Upcoming Visit Reminder',
        message: 'You have a Plumbing visit scheduled in 3 hours at DHA Phase 2.',
        time: now.subtract(const Duration(hours: 4)),
        isRead: true,
        relatedBookingId: 'BKG-902',
      ),
      NotificationModel(
        id: 'NOTIF-4',
        type: NotificationType.customerCancelled,
        title: 'Job Cancelled',
        message: 'Ahmed cancelled the AC Repair booking.',
        time: now.subtract(const Duration(days: 1)),
        isRead: true,
        relatedBookingId: 'BKG-875',
      ),
    ];
  }
}
