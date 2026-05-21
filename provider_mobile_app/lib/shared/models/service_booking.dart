import '../widgets/status_chip.dart';

class ServiceBooking {
  final String id;
  final String customerName;
  final String customerPhone;
  final String serviceType;
  final String issueDescription;
  final String address;
  final double? latitude;
  final double? longitude;
  final DateTime scheduledTime;
  final BookingStatus status;
  final String apiStatus;
  final double price;

  ServiceBooking({
    required this.id,
    required this.customerName,
    this.customerPhone = '',
    required this.serviceType,
    this.issueDescription = '',
    required this.address,
    this.latitude,
    this.longitude,
    required this.scheduledTime,
    required this.status,
    this.apiStatus = 'pending',
    required this.price,
  });

  // Dummy Data generator
  static List<ServiceBooking> get dummyBookings {
    return [
      ServiceBooking(
        id: 'BKG-1001',
        customerName: 'Ahmad Khan',
        serviceType: 'AC Repair & Service',
        issueDescription: 'Indoor unit not cooling properly.',
        address: 'House 45, Street 2, DHA Phase 1',
        latitude: 33.6844,
        longitude: 73.0479,
        scheduledTime: DateTime.now().add(const Duration(hours: 2)),
        status: BookingStatus.pending,
        apiStatus: 'pending',
        price: 2500,
      ),
      ServiceBooking(
        id: 'BKG-1002',
        customerName: 'Sara Ali',
        serviceType: 'Plumbing - Leak Fix',
        issueDescription: 'Kitchen sink leakage and pressure issue.',
        address: 'Apartment 3B, Askari 10',
        latitude: 33.5651,
        longitude: 73.0169,
        scheduledTime: DateTime.now().add(const Duration(days: 1)),
        status: BookingStatus.accepted,
        apiStatus: 'accepted',
        price: 1500,
      ),
      ServiceBooking(
        id: 'BKG-1003',
        customerName: 'Usman Tariq',
        serviceType: 'Electrical Wiring',
        issueDescription: 'Short circuit in the main switchboard.',
        address: 'House 12, Bahria Town',
        latitude: 33.5443,
        longitude: 73.1231,
        scheduledTime: DateTime.now().subtract(const Duration(hours: 24)),
        status: BookingStatus.completed,
        apiStatus: 'completed',
        price: 4500,
      ),
    ];
  }
}
