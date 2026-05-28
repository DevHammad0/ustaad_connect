import 'package:flutter/foundation.dart';

class ApiEndpoints {
  // Base URL — replace with real server URL when deployed
  // From Postman collection: http://localhost:8001 (dev)
  static String get baseUrl {
    const envUrl = String.fromEnvironment('BACKEND_URL');
    if (envUrl.isNotEmpty) {
      return envUrl;
    }

    if (kDebugMode) {
      // Standard local development port. Change to 8001 if your local server runs on port 8001.
      const localPort = '8000';
      if (kIsWeb) {
        return 'http://localhost:$localPort';
      }
      return defaultTargetPlatform == TargetPlatform.android
          ? 'http://10.0.2.2:$localPort'
          : 'http://localhost:$localPort';
    }
    return 'https://ustaad-connect-941693721026.us-central1.run.app';
  }

  // Required header for all requests (from Postman: X-App-Secret)
  static const String appSecretHeader = 'X-App-Secret';
  
  static String get appSecret {
    const envSecret = String.fromEnvironment('APP_SECRET');
    if (envSecret.isNotEmpty) {
      return envSecret;
    }
    return '97361b6101404313c275dd4c6192f825f4de065f5f1e2a3a11b9b13a80ed2e86';
  }

  // Auth
  // POST /api/provider/login         { phone }
  static const String login = '/api/provider/login';
  // POST /api/provider/register      { name, phone, service_type, city, area, visit_fee, lat, lng, bio, cnic }
  static const String register = '/api/provider/register';

  // Provider Profile
  // GET  /api/provider/{id}/profile
  static String getProfile(String providerId) => '/api/provider/$providerId/profile';
  // PUT  /api/provider/{id}/profile  { is_active, visit_fee, bio, area, cnic }
  static String updateProfile(String providerId) => '/api/provider/$providerId/profile';

  // Active Job
  // GET  /api/provider/{id}/active-job
  static String getActiveJob(String providerId) => '/api/provider/$providerId/active-job';

  // Location
  // POST /api/provider/{id}/location { lat, lng }
  static String updateLocation(String providerId) => '/api/provider/$providerId/location';

  // Bookings
  // POST /api/provider/bookings/{id}/accept   { estimated_cost_min, estimated_cost_max }
  static String acceptBooking(String bookingId) => '/api/provider/bookings/$bookingId/accept';
  // POST /api/provider/bookings/{id}/confirm
  static String confirmBooking(String bookingId) => '/api/provider/bookings/$bookingId/confirm';
  // POST /api/provider/bookings/{id}/status   { status: en_route | arrived }
  static String updateBookingStatus(String bookingId) => '/api/provider/bookings/$bookingId/status';
  // POST /api/provider/bookings/{id}/complete { final_cost }
  static String completeBooking(String bookingId) => '/api/provider/bookings/$bookingId/complete';
  // POST /api/provider/bookings/{id}/cancel   { cancelled_by: provider }
  static String cancelBooking(String bookingId) => '/api/provider/bookings/$bookingId/cancel';
}
