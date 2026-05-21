import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../booking_requests/models/booking_request_model.dart';
import '../models/estimate_model.dart';
import '../providers/estimates_provider.dart';
import '../widgets/estimate_summary_card.dart';
import '../widgets/estimate_form.dart';
import '../../../shared/widgets/app_primary_button.dart';
import '../../../core/constants/app_colors.dart';

class EstimateScreen extends ConsumerStatefulWidget {
  final BookingRequest? request;

  const EstimateScreen({super.key, this.request});

  @override
  ConsumerState<EstimateScreen> createState() => _EstimateScreenState();
}

class _EstimateScreenState extends ConsumerState<EstimateScreen> {
  final _minCostController = TextEditingController();
  final _maxCostController = TextEditingController();
  final _noteController = TextEditingController();

  @override
  void dispose() {
    _minCostController.dispose();
    _maxCostController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  void _submitEstimate() {
    if (widget.request == null) return;
    final minCostStr = _minCostController.text.trim();
    final maxCostStr = _maxCostController.text.trim();
    if (minCostStr.isEmpty || maxCostStr.isEmpty) {
      _showError('Please enter both minimum and maximum estimated costs.');
      return;
    }
    final minCost = double.tryParse(minCostStr) ?? 0;
    final maxCost = double.tryParse(maxCostStr) ?? 0;
    if (maxCost <= minCost) {
      _showError('Maximum cost must be greater than the minimum cost.');
      return;
    }
    ref.read(estimatesProvider.notifier).submitEstimate(EstimateModel(
      requestId: widget.request!.id,
      minCost: minCost,
      maxCost: maxCost,
      note: _noteController.text.trim(),
    ));
  }

  void _rejectRequest() {
    if (widget.request == null) return;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Reject Request',
            style: GoogleFonts.poppins(fontWeight: FontWeight.w700)),
        content: Text(
            'Are you sure you want to reject this booking request?',
            style: GoogleFonts.inter()),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Cancel',
                style: GoogleFonts.poppins(color: AppColors.textSecondary)),
          ),
          TextButton(
            onPressed: () async {
              Navigator.of(ctx).pop();
              final success = await ref
                  .read(estimatesProvider.notifier)
                  .rejectRequest(widget.request!.id);
              if (success && mounted) context.go('/requests');
            },
            child: Text('Reject',
                style: GoogleFonts.poppins(
                    color: AppColors.error, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  void _showError(String message) =>
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));

  void _showSuccessDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        icon: Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: AppColors.success.withValues(alpha: 0.12),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.check_circle_rounded,
              color: AppColors.success, size: 36),
        ),
        title: Text('Estimate Submitted!',
            style: GoogleFonts.poppins(fontWeight: FontWeight.w700),
            textAlign: TextAlign.center),
        content: Text(
          'Your estimate has been sent to the customer. You\'ll be notified once they accept.',
          style: GoogleFonts.inter(color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: AppPrimaryButton(
              text: 'View Booking',
              onPressed: () {
                Navigator.of(ctx).pop();
                context.go('/active-bookings/${widget.request!.id}');
              },
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.request == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Create Estimate')),
        body: const Center(child: Text('Error: No request data found')),
      );
    }

    final state = ref.watch(estimatesProvider);

    ref.listen<EstimateState>(estimatesProvider, (previous, next) {
      if (next.isSuccess) _showSuccessDialog();
      else if (next.error != null) _showError(next.error!);
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          // ── Header ────────────────────────────────────────────────
          SliverAppBar(
            pinned: true,
            expandedHeight: 140,
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
                    padding: const EdgeInsets.fromLTRB(24, 60, 24, 20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text('Create Estimate',
                            style: GoogleFonts.poppins(
                              color: Colors.white,
                              fontSize: 24,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.5,
                            )),
                        Text('Set your price range for this job',
                            style: GoogleFonts.inter(
                              color: AppColors.textOnDarkMuted,
                              fontSize: 13,
                            )),
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
                EstimateSummaryCard(request: widget.request!),
                const SizedBox(height: 24),
                Text('Your Estimate',
                    style: GoogleFonts.poppins(
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                      color: AppColors.textPrimary,
                    )),
                const SizedBox(height: 14),
                EstimateForm(
                  minCostController: _minCostController,
                  maxCostController: _maxCostController,
                  noteController: _noteController,
                ),
                const SizedBox(height: 36),
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        height: 58,
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(50),
                          border: Border.all(
                            color: AppColors.error.withValues(alpha: 0.5),
                            width: 1.5,
                          ),
                        ),
                        child: TextButton(
                          onPressed: state.isLoading ? null : _rejectRequest,
                          style: TextButton.styleFrom(
                            foregroundColor: AppColors.error,
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(50)),
                          ),
                          child: Text('Reject',
                              style: GoogleFonts.poppins(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 15,
                                  color: AppColors.error)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 2,
                      child: AppPrimaryButton(
                        text: 'Submit Estimate',
                        isLoading: state.isLoading,
                        onPressed: _submitEstimate,
                      ),
                    ),
                  ],
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}
