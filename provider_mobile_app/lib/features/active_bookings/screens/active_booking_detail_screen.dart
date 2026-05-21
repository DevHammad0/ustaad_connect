import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/widgets/app_primary_button.dart';

class ActiveBookingDetailScreen extends StatelessWidget {
  final String bookingId;

  const ActiveBookingDetailScreen({super.key, required this.bookingId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Active Booking'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Placeholder for Active Booking Details\nID: $bookingId', textAlign: TextAlign.center),
            const SizedBox(height: 32),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 48.0),
              child: AppPrimaryButton(
                text: 'Update Service Status',
                onPressed: () {
                  context.push('/service-status/$bookingId');
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
