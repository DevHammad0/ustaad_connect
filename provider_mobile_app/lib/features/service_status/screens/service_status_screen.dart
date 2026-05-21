import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/status_step_model.dart';
import '../providers/service_status_provider.dart';
import '../widgets/status_timeline_widget.dart';
import '../widgets/status_action_button.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../core/constants/app_colors.dart';

class ServiceStatusScreen extends ConsumerStatefulWidget {
  final String bookingId;

  const ServiceStatusScreen({super.key, required this.bookingId});

  @override
  ConsumerState<ServiceStatusScreen> createState() =>
      _ServiceStatusScreenState();
}

class _ServiceStatusScreenState extends ConsumerState<ServiceStatusScreen> {
  final _finalCostController = TextEditingController();

  @override
  void dispose() {
    _finalCostController.dispose();
    super.dispose();
  }

  void _confirmCompletion() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: Text('Complete Job',
            style: GoogleFonts.poppins(fontWeight: FontWeight.w700)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Enter the final amount charged (PKR) to complete this job.',
              style: GoogleFonts.inter(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _finalCostController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: 'Final Cost',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Cancel',
                style:
                    GoogleFonts.poppins(color: AppColors.textSecondary)),
          ),
          TextButton(
            onPressed: () {
              final cost = double.tryParse(_finalCostController.text) ?? 0.0;
              if (cost <= 0) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Please enter a valid amount')),
                );
                return;
              }
              Navigator.of(ctx).pop();
              ref
                  .read(serviceStatusProvider(widget.bookingId).notifier)
                  .completeJob(cost);
            },
            child: Text('Complete',
                style: GoogleFonts.poppins(
                    color: AppColors.success, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  void _confirmCancellation() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: Text('Cancel Job',
            style: GoogleFonts.poppins(fontWeight: FontWeight.w700)),
        content: Text(
          'Are you sure you want to cancel this job? Only do this if absolutely necessary.',
          style: GoogleFonts.inter(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Go Back',
                style:
                    GoogleFonts.poppins(color: AppColors.textSecondary)),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              ref
                  .read(serviceStatusProvider(widget.bookingId).notifier)
                  .cancelJob();
            },
            child: Text('Cancel Job',
                style: GoogleFonts.poppins(
                    color: AppColors.error, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  void _handleAdvance(ServiceStatusStep currentStatus) {
    if (currentStatus.nextStep == ServiceStatusStep.completed) {
      _confirmCompletion();
    } else {
      ref
          .read(serviceStatusProvider(widget.bookingId).notifier)
          .advanceStatus();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(serviceStatusProvider(widget.bookingId));

    ref.listen<ServiceStatusState>(
        serviceStatusProvider(widget.bookingId), (previous, next) {
      if (next.error != null) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(next.error!)));
      } else if (next.isJobFinished) {
        final router = GoRouter.of(context);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(next.currentStatus == ServiceStatusStep.completed
              ? 'Job completed successfully!'
              : 'Job cancelled.'),
          backgroundColor:
              next.currentStatus == ServiceStatusStep.completed
                  ? AppColors.success
                  : AppColors.error,
        ));
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) router.go('/history');
        });
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          // ── Header ────────────────────────────────────────────────
          SliverAppBar(
            pinned: true,
            expandedHeight: 150,
            backgroundColor: AppColors.darkTeal,
            elevation: 0,
            scrolledUnderElevation: 0,
            leading: GestureDetector(
              onTap: () => context.pop(),
              child: Container(
                margin: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.arrow_back_ios_new_rounded,
                    color: Colors.white, size: 16),
              ),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: AppColors.primaryGradient,
                  ),
                ),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 72, 24, 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text('Service Progress',
                            style: GoogleFonts.poppins(
                              color: Colors.white,
                              fontSize: 24,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.5,
                            )),
                        Text('Track and update this job\'s status',
                            style: GoogleFonts.inter(
                              color: AppColors.textOnDarkMuted,
                              fontSize: 13,
                              height: 1.35,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),

          // ── Content ───────────────────────────────────────────────
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 40),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                // Booking info card
                AppCard(
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(Icons.work_rounded,
                            color: AppColors.primary, size: 22),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Booking #${widget.bookingId}',
                              style: GoogleFonts.poppins(
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                                color: AppColors.textPrimary,
                              ),
                            ),
                            Text(
                              'AC Repair · Islamabad',
                              style: GoogleFonts.inter(
                                color: AppColors.textSecondary,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 28),
                Text(
                  'Status Timeline',
                  style: GoogleFonts.poppins(
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 20),
                StatusTimelineWidget(currentStatus: state.currentStatus),
                const SizedBox(height: 36),
                if (!state.isJobFinished) ...[
                  StatusActionButton(
                    currentStatus: state.currentStatus,
                    isLoading: state.isLoading,
                    onAdvance: () => _handleAdvance(state.currentStatus),
                  ),
                  const SizedBox(height: 12),
                  Center(
                    child: TextButton(
                      onPressed: state.isLoading ? null : _confirmCancellation,
                      child: Text(
                        'Cancel Job',
                        style: GoogleFonts.poppins(
                          color: AppColors.error,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ],
              ]),
            ),
          ),
        ],
      ),
    );
  }
}
