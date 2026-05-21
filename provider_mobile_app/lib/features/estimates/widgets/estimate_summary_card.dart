import 'package:flutter/material.dart';
import '../../booking_requests/models/booking_request_model.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../core/constants/app_colors.dart';

class EstimateSummaryCard extends StatelessWidget {
  final BookingRequest request;

  const EstimateSummaryCard({super.key, required this.request});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.build_circle_outlined, color: AppColors.primary, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  request.serviceType,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ),
            ],
          ),
          const Divider(height: 24),
          _SummaryRow(icon: Icons.description_outlined, text: request.issueSummary),
          const SizedBox(height: 8),
          _SummaryRow(icon: Icons.location_on_outlined, text: request.customerLocation),
          const SizedBox(height: 8),
          _SummaryRow(icon: Icons.access_time, text: request.requestedTime),
          const SizedBox(height: 8),
          _SummaryRow(
            icon: Icons.payments_outlined,
            text: 'Visit Fee: Rs. ${request.visitFee.toStringAsFixed(0)}',
            isHighlight: true,
          ),
        ],
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final IconData icon;
  final String text;
  final bool isHighlight;

  const _SummaryRow({
    required this.icon,
    required this.text,
    this.isHighlight = false,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: isHighlight ? AppColors.primary : AppColors.textSecondary),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontSize: 14,
              color: isHighlight ? AppColors.primary : AppColors.textPrimary,
              fontWeight: isHighlight ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ),
      ],
    );
  }
}
