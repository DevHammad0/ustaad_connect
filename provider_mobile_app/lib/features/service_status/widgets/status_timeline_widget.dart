import 'package:flutter/material.dart';
import '../models/status_step_model.dart';
import '../../../core/constants/app_colors.dart';

class StatusTimelineWidget extends StatelessWidget {
  final ServiceStatusStep currentStatus;

  const StatusTimelineWidget({super.key, required this.currentStatus});

  @override
  Widget build(BuildContext context) {
    if (currentStatus == ServiceStatusStep.cancelled) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Text(
            'This job was cancelled.',
            style: TextStyle(color: AppColors.error, fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ),
      );
    }

    final steps = [
      ServiceStatusStep.accepted,
      ServiceStatusStep.enRoute,
      ServiceStatusStep.arrived,
      ServiceStatusStep.workStarted,
      ServiceStatusStep.completed,
    ];

    final currentIndex = steps.indexOf(currentStatus);

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: steps.length,
      itemBuilder: (context, index) {
        final step = steps[index];
        final isCompleted = index < currentIndex;
        final isActive = index == currentIndex;
        final isLast = index == steps.length - 1;

        return _buildTimelineStep(step.label, isCompleted, isActive, isLast);
      },
    );
  }

  Widget _buildTimelineStep(String title, bool isCompleted, bool isActive, bool isLast) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isCompleted || isActive ? AppColors.primary : Colors.grey[300],
                border: isActive ? Border.all(color: AppColors.primaryLight, width: 4) : null,
              ),
              child: isCompleted
                  ? const Icon(Icons.check, size: 16, color: Colors.white)
                  : null,
            ),
            if (!isLast)
              Container(
                width: 2,
                height: 40,
                color: isCompleted ? AppColors.primary : Colors.grey[300],
              ),
          ],
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 2.0),
            child: Text(
              title,
              style: TextStyle(
                fontSize: 16,
                fontWeight: isActive ? FontWeight.bold : (isCompleted ? FontWeight.w600 : FontWeight.normal),
                color: isActive || isCompleted ? AppColors.textPrimary : AppColors.textSecondary,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
