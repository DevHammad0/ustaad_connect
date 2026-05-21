import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import '../../../core/constants/app_colors.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../shared/widgets/app_location_map.dart';
import '../../../shared/widgets/app_primary_button.dart';
import '../providers/active_job_provider.dart';
import '../widgets/radar_scanner.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  final TextEditingController _minCostController = TextEditingController();
  final TextEditingController _maxCostController = TextEditingController();
  final TextEditingController _finalCostController = TextEditingController();
  String? _lastShownError;

  @override
  void dispose() {
    _minCostController.dispose();
    _maxCostController.dispose();
    _finalCostController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(activeJobProvider);

    ref.listen<ActiveJobState>(activeJobProvider, (previous, next) {
      if (next.error != null && next.error != _lastShownError) {
        _lastShownError = next.error;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(next.error!)),
        );
      } else if (next.error == null) {
        _lastShownError = null;
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            backgroundColor: AppColors.darkTeal,
            elevation: 0,
            scrolledUnderElevation: 0,
            automaticallyImplyLeading: false,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: AppColors.primaryGradient,
                  ),
                ),
                child: Stack(
                  children: [
                    Positioned(
                      top: -30,
                      right: -20,
                      child: Container(
                        width: 160,
                        height: 160,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.primary.withValues(alpha: 0.10),
                        ),
                      ),
                    ),
                    SafeArea(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(24, 24, 24, 28),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 8,
                              ),
                              decoration: BoxDecoration(
                                color: AppColors.primary.withValues(alpha: 0.18),
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(
                                    Icons.handyman_rounded,
                                    color: AppColors.primaryLight,
                                    size: 16,
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Single Provider Console',
                                    style: GoogleFonts.poppins(
                                      color: AppColors.primaryLight,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 18),
                            Text(
                              'Job Workflow',
                              style: GoogleFonts.poppins(
                                color: Colors.white,
                                fontSize: 30,
                                fontWeight: FontWeight.w800,
                                letterSpacing: -0.6,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Login, poll, accept, travel, arrive, and complete from one simple flow.',
                              style: GoogleFonts.inter(
                                color: AppColors.textOnDarkMuted,
                                fontSize: 13,
                                height: 1.45,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                if (state.isLoading && state.job == null)
                  const Padding(
                    padding: EdgeInsets.only(top: 80),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (state.job == null)
                  _buildIdleState(state.isLoading)
                else
                  _buildActiveJob(state),
              ]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildIdleState(bool isBusy) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
      child: Column(
        children: [
          const RadarScanner(),
          const SizedBox(height: 28),
          Text(
            'Looking for jobs...',
            style: GoogleFonts.poppins(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Stay online to receive requests. This screen will automatically switch when a job appears.',
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              color: AppColors.textSecondary,
              fontSize: 14,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton(
            onPressed: isBusy
                ? null
                : () => ref.read(activeJobProvider.notifier).forcePoll(),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.darkTeal,
              side: BorderSide(
                color: AppColors.darkTeal.withValues(alpha: 0.2),
              ),
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(18),
              ),
            ),
            child: Text(
              isBusy ? 'Checking...' : 'Force Poll Now',
              style: GoogleFonts.poppins(fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActiveJob(ActiveJobState state) {
    final job = state.job!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppCard(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Active Job',
                          style: GoogleFonts.poppins(
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Booking #${job.id}',
                          style: GoogleFonts.inter(
                            color: AppColors.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                  _StatusPill(status: job.apiStatus),
                ],
              ),
              const SizedBox(height: 20),
              _DetailRow(label: 'Customer', value: _customerText(job)),
              _DetailRow(label: 'Issue', value: job.issueDescription),
              _DetailRow(label: 'Location', value: job.address),
              if (job.latitude != null && job.longitude != null) ...[
                _DetailRow(
                  label: 'Time',
                  value: _timeText(job.scheduledTime),
                  isLast: false,
                ),
                const SizedBox(height: 16),
                AppLocationMap(
                  center: LatLng(job.latitude!, job.longitude!),
                  marker: LatLng(job.latitude!, job.longitude!),
                  height: 220,
                  zoom: 14,
                  label: 'Customer Pin Location',
                ),
              ] else
                _DetailRow(
                  label: 'Time',
                  value: _timeText(job.scheduledTime),
                  isLast: true,
                ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        _buildActionArea(state),
      ],
    );
  }

  Widget _buildActionArea(ActiveJobState state) {
    final job = state.job!;
    switch (job.apiStatus) {
      case 'pending':
        return AppCard(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Send Estimate',
                style: GoogleFonts.poppins(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Enter your minimum and maximum price range, then accept the job.',
                style: GoogleFonts.inter(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Expanded(
                    child: _NumberField(
                      controller: _minCostController,
                      hintText: 'Min Cost',
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _NumberField(
                      controller: _maxCostController,
                      hintText: 'Max Cost',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              AppPrimaryButton(
                text: 'Accept Job & Send Estimate',
                isLoading: state.isLoading,
                onPressed: () => _submitEstimate(job.id),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: state.isLoading
                    ? null
                    : () => ref.read(activeJobProvider.notifier).cancelJob(job.id),
                child: Text(
                  'Decline',
                  style: GoogleFonts.poppins(
                    color: AppColors.error,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        );
      case 'accepted':
        return AppCard(
          padding: const EdgeInsets.all(20),
          backgroundColor: AppColors.darkTeal,
          child: Column(
            children: [
              Icon(
                Icons.schedule_rounded,
                color: AppColors.primaryLight,
                size: 34,
              ),
              const SizedBox(height: 14),
              Text(
                'Waiting for customer confirmation',
                textAlign: TextAlign.center,
                style: GoogleFonts.poppins(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'This screen auto-polls every 5 seconds. Once the customer confirms, the next action will appear here.',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  color: AppColors.textOnDarkMuted,
                  fontSize: 13,
                  height: 1.45,
                ),
              ),
            ],
          ),
        );
      case 'confirmed':
        return _ActionCard(
          title: 'Customer Confirmed',
          subtitle: 'Head to the customer now and update your trip status.',
          child: Column(
            children: [
              AppPrimaryButton(
                text: 'Mark En Route',
                isLoading: state.isLoading,
                onPressed: () =>
                    ref.read(activeJobProvider.notifier).markEnRoute(job.id),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: state.isLoading
                    ? null
                    : () => ref.read(activeJobProvider.notifier).cancelJob(job.id),
                child: Text(
                  'Cancel Job',
                  style: GoogleFonts.poppins(
                    color: AppColors.error,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        );
      case 'en_route':
        return _ActionCard(
          title: 'On the way',
          subtitle: 'Update the customer when you reach the location.',
          child: Column(
            children: [
              AppPrimaryButton(
                text: 'Mark Arrived',
                isLoading: state.isLoading,
                onPressed: () =>
                    ref.read(activeJobProvider.notifier).markArrived(job.id),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: state.isLoading
                    ? null
                    : () => ref.read(activeJobProvider.notifier).cancelJob(job.id),
                child: Text(
                  'Cancel Job',
                  style: GoogleFonts.poppins(
                    color: AppColors.error,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        );
      case 'arrived':
        return _ActionCard(
          title: 'Complete Job',
          subtitle: 'Enter the final amount charged to finish this booking.',
          child: Column(
            children: [
              _NumberField(
                controller: _finalCostController,
                hintText: 'Final Amount Charged (PKR)',
              ),
              const SizedBox(height: 16),
              AppPrimaryButton(
                text: 'Complete Job',
                isLoading: state.isLoading,
                onPressed: () => _completeJob(job.id),
              ),
            ],
          ),
        );
      default:
        return _ActionCard(
          title: 'Job in progress',
          subtitle: 'This booking is being managed through the current live API state.',
          child: const SizedBox.shrink(),
        );
    }
  }

  Future<void> _submitEstimate(String bookingId) async {
    final minCost = double.tryParse(_minCostController.text.trim()) ?? 0;
    final maxCost = double.tryParse(_maxCostController.text.trim()) ?? 0;
    if (minCost <= 0 || maxCost <= minCost) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enter a valid estimate range before accepting the job'),
        ),
      );
      return;
    }

    await ref.read(activeJobProvider.notifier).acceptJob(
          bookingId: bookingId,
          minCost: minCost,
          maxCost: maxCost,
        );
  }

  Future<void> _completeJob(String bookingId) async {
    final finalCost = double.tryParse(_finalCostController.text.trim()) ?? 0;
    if (finalCost <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter the final charged amount')),
      );
      return;
    }

    await ref.read(activeJobProvider.notifier).completeJob(
          bookingId,
          finalCost,
        );
    _finalCostController.clear();
  }

  String _customerText(dynamic job) {
    if (job.customerPhone != null && job.customerPhone.isNotEmpty) {
      return '${job.customerName} (${job.customerPhone})';
    }
    return job.customerName;
  }

  String _timeText(DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);
    if (difference.inMinutes < 1) return 'Just now';
    if (difference.inMinutes < 60) return '${difference.inMinutes} min ago';
    if (difference.inHours < 24) return '${difference.inHours} hour(s) ago';
    return '${time.day}/${time.month}/${time.year}';
  }
}

class _ActionCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final Widget child;

  const _ActionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: GoogleFonts.inter(
              color: AppColors.textSecondary,
              fontSize: 13,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 18),
          child,
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final String status;

  const _StatusPill({required this.status});

  @override
  Widget build(BuildContext context) {
    final normalized = status.toUpperCase().replaceAll('_', ' ');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        normalized,
        style: GoogleFonts.poppins(
          color: AppColors.primary,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;
  final bool isLast;

  const _DetailRow({
    required this.label,
    required this.value,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsets.only(bottom: isLast ? 0 : 14),
      padding: EdgeInsets.only(bottom: isLast ? 0 : 14),
      decoration: BoxDecoration(
        border: isLast
            ? null
            : Border(
                bottom: BorderSide(
                  color: Colors.black.withValues(alpha: 0.06),
                ),
              ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.toUpperCase(),
            style: GoogleFonts.poppins(
              color: AppColors.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: GoogleFonts.poppins(
              color: AppColors.textPrimary,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _NumberField extends StatelessWidget {
  final TextEditingController controller;
  final String hintText;

  const _NumberField({
    required this.controller,
    required this.hintText,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: TextInputType.number,
      decoration: InputDecoration(
        hintText: hintText,
        hintStyle: GoogleFonts.inter(color: AppColors.textSecondary),
        filled: true,
        fillColor: Colors.white,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: Colors.black.withValues(alpha: 0.08)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: Colors.black.withValues(alpha: 0.08)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.4),
        ),
      ),
    );
  }
}
