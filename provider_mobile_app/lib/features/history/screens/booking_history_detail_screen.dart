import 'package:flutter/material.dart';

class BookingHistoryDetailScreen extends StatelessWidget {
  final String bookingId;

  const BookingHistoryDetailScreen({super.key, required this.bookingId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('History Details'),
      ),
      body: Center(
        child: Text(
          'History Details Placeholder\nFor Booking ID: $bookingId',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleMedium,
        ),
      ),
    );
  }
}
