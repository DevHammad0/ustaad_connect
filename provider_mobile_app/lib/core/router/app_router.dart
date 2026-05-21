import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/widgets/error_state_widget.dart';
import '../../features/dashboard/screens/main_scaffold.dart';
import '../../features/dashboard/screens/dashboard_screen.dart';
import '../../features/booking_requests/models/booking_request_model.dart';
import '../../features/booking_requests/screens/booking_requests_screen.dart';
import '../../features/booking_requests/screens/booking_request_detail_screen.dart';
import '../../features/active_bookings/screens/active_bookings_screen.dart';
import '../../features/active_bookings/screens/active_booking_detail_screen.dart';
import '../../features/service_status/screens/service_status_screen.dart';
import '../../features/estimates/screens/estimate_screen.dart';
import '../../features/history/screens/history_screen.dart';
import '../../features/history/screens/booking_history_detail_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/profile/screens/edit_profile_screen.dart';
import '../../features/profile/screens/service_settings_screen.dart';
import '../../features/profile/screens/availability_settings_screen.dart';
import '../../features/profile/screens/notification_settings_screen.dart';
import '../../features/notifications/screens/notifications_screen.dart';
import '../../features/auth/screens/splash_screen.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/otp_verification_screen.dart';
import '../../features/auth/screens/account_setup_screen.dart';

import '../../features/onboarding/screens/onboarding_flow_screen.dart';
import '../../features/onboarding/screens/steps/personal_info_step.dart';
import '../../features/onboarding/screens/steps/service_category_step.dart';
import '../../features/onboarding/screens/steps/service_area_step.dart';
import '../../features/onboarding/screens/steps/visit_fee_step.dart';
import '../../features/onboarding/screens/steps/experience_step.dart';
import '../../features/onboarding/screens/steps/working_hours_step.dart';
import '../../features/onboarding/screens/steps/onboarding_review_step.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'root');
final GlobalKey<NavigatorState> _mainShellNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'main_shell');
final GlobalKey<NavigatorState> _onboardingShellNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'onboarding_shell');

final GoRouter appRouter = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/splash',
  errorBuilder: (context, state) => Scaffold(
    appBar: AppBar(title: const Text('Route Not Found')),
    body: ErrorStateWidget(
      message: 'The screen you are looking for does not exist.\nPath: ${state.uri.path}',
      onRetry: () => context.go('/dashboard'),
    ),
  ),
  routes: [
    // Auth Routes
    GoRoute(
      path: '/splash',
      builder: (context, state) => const SplashScreen(),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
      GoRoute(
        path: '/verify-otp',
        builder: (context, state) {
          final phone = state.extra as String? ?? '';
          return OtpVerificationScreen(phone: phone);
        },
      ),
    GoRoute(
      path: '/account-setup',
      builder: (context, state) => const AccountSetupScreen(),
    ),

    // Onboarding Shell Route (Wizard)
    ShellRoute(
      navigatorKey: _onboardingShellNavigatorKey,
      builder: (context, state, child) {
        return OnboardingFlowScreen(child: child);
      },
      routes: [
        GoRoute(
          path: '/onboarding/personal-info',
          builder: (context, state) => const PersonalInfoStep(),
        ),
        GoRoute(
          path: '/onboarding/service-category',
          builder: (context, state) => const ServiceCategoryStep(),
        ),
        GoRoute(
          path: '/onboarding/service-area',
          builder: (context, state) => const ServiceAreaStep(),
        ),
        GoRoute(
          path: '/onboarding/visit-fee',
          builder: (context, state) => const VisitFeeStep(),
        ),
        GoRoute(
          path: '/onboarding/experience',
          builder: (context, state) => const ExperienceStep(),
        ),
        GoRoute(
          path: '/onboarding/working-hours',
          builder: (context, state) => const WorkingHoursStep(),
        ),
        GoRoute(
          path: '/onboarding/review',
          builder: (context, state) => const OnboardingReviewStep(),
        ),
      ],
    ),

    // Full Screen Profile Settings
    GoRoute(
      path: '/profile/edit',
      builder: (context, state) => const EditProfileScreen(),
    ),
    GoRoute(
      path: '/profile/service-settings',
      builder: (context, state) => const ServiceSettingsScreen(),
    ),
    GoRoute(
      path: '/profile/availability',
      builder: (context, state) => const AvailabilitySettingsScreen(),
    ),
    GoRoute(
      path: '/profile/notifications',
      builder: (context, state) => const NotificationSettingsScreen(),
    ),

    // Other Full Screens
    GoRoute(
      path: '/notifications',
      builder: (context, state) => const NotificationsScreen(),
    ),
    GoRoute(
      path: '/estimate/:requestId',
      builder: (context, state) {
        final request = state.extra as BookingRequest?;
        return EstimateScreen(request: request);
      },
    ),
    GoRoute(
      path: '/service-status/:bookingId',
      builder: (context, state) {
        final id = state.pathParameters['bookingId']!;
        return ServiceStatusScreen(bookingId: id);
      },
    ),

    // Main App Shell Route (Bottom Navigation)
    ShellRoute(
      navigatorKey: _mainShellNavigatorKey,
      builder: (context, state, child) {
        return MainScaffold(child: child);
      },
      routes: [
        GoRoute(
          path: '/dashboard',
          builder: (context, state) => const DashboardScreen(),
        ),
        GoRoute(
          path: '/requests',
          builder: (context, state) => const BookingRequestsScreen(),
          routes: [
            GoRoute(
              path: ':id',
              builder: (context, state) {
                final id = state.pathParameters['id']!;
                return BookingRequestDetailScreen(requestId: id);
              },
            ),
          ],
        ),
        GoRoute(
          path: '/active-bookings',
          builder: (context, state) => const ActiveBookingsScreen(),
          routes: [
            GoRoute(
              path: ':id',
              builder: (context, state) {
                final id = state.pathParameters['id']!;
                return ActiveBookingDetailScreen(bookingId: id);
              },
            ),
          ],
        ),
        GoRoute(
          path: '/history',
          builder: (context, state) => const HistoryScreen(),
          routes: [
            GoRoute(
              path: ':id',
              builder: (context, state) {
                final id = state.pathParameters['id']!;
                return BookingHistoryDetailScreen(bookingId: id);
              },
            ),
          ],
        ),
        GoRoute(
          path: '/profile',
          builder: (context, state) => const ProfileScreen(),
        ),
      ],
    ),
  ],
);
