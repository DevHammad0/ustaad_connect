import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/booking_requests_provider.dart';
import '../widgets/request_detail_info_card.dart';
import '../../../shared/widgets/app_primary_button.dart';
import '../../../core/constants/app_colors.dart';

class BookingRequestDetailScreen extends ConsumerWidget {
  final String requestId;

  const BookingRequestDetailScreen({super.key, required this.requestId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requestAsyncValue = ref.watch(requestDetailProvider(requestId));

    return Scaffold(
      backgroundColor: AppColors.background,
      body: requestAsyncValue.when(
        data: (request) {
          if (request == null) {
            return const Center(child: Text('Request not found'));
          }

          return CustomScrollView(
            slivers: [
              // ── Header ──────────────────────────────────────────────
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
                    child: const Icon(
                      Icons.arrow_back_ios_new_rounded,
                      color: Colors.white,
                      size: 16,
                    ),
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
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Expanded(
                              child: Text(
                                request.serviceType,
                                style: GoogleFonts.poppins(
                                  color: Colors.white,
                                  fontSize: 24,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: -0.5,
                                ),
                              ),
                            ),
                            if (request.isNew)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 6),
                                decoration: BoxDecoration(
                                  color: AppColors.primaryBright,
                                  borderRadius: BorderRadius.circular(50),
                                ),
                                child: Text(
                                  'NEW',
                                  style: GoogleFonts.poppins(
                                    color: AppColors.darkTeal,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              // ── Detail cards ─────────────────────────────────────────
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 20, 16, 16),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
                    RequestDetailInfoCard(
                      icon: Icons.description_rounded,
                      title: 'Issue Summary',
                      content: request.issueSummary,
                    ),
                    const SizedBox(height: 10),
                    RequestDetailInfoCard(
                      icon: Icons.info_rounded,
                      title: 'Full Description',
                      content: request.issueDescription,
                    ),
                    const SizedBox(height: 10),
                    RequestDetailInfoCard(
                      icon: Icons.location_on_rounded,
                      title: 'Location (Approx 4.2 km away)',
                      content: request.customerLocation,
                    ),
                    const SizedBox(height: 10),
                    RequestDetailInfoCard(
                      icon: Icons.access_time_rounded,
                      title: 'Requested Time',
                      content: request.requestedTime,
                    ),
                    const SizedBox(height: 10),
                    RequestDetailInfoCard(
                      icon: Icons.payments_rounded,
                      title: 'Visit Fee',
                      content: 'Rs. ${request.visitFee.toStringAsFixed(0)}',
                    ),
                    if (request.customerNote != null &&
                        request.customerNote!.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      RequestDetailInfoCard(
                        icon: Icons.speaker_notes_rounded,
                        title: 'Customer Note',
                        content: request.customerNote!,
                      ),
                    ],
                    const SizedBox(height: 32),

                    // Action buttons
                    Row(
                      children: [
                        // Reject button
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
                              onPressed: () => context.pop(),
                              style: TextButton.styleFrom(
                                foregroundColor: AppColors.error,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(50),
                                ),
                              ),
                              child: Text(
                                'Reject',
                                style: GoogleFonts.poppins(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 15,
                                  color: AppColors.error,
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          flex: 2,
                          child: AppPrimaryButton(
                            text: 'Add Estimate',
                            icon: Icons.edit_rounded,
                            onPressed: () => context.push(
                                '/estimate/${request.id}',
                                extra: request),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),
                  ]),
                ),
              ),
            ],
          );
        },
        loading: () => const Center(
            child: CircularProgressIndicator(color: AppColors.primary)),
        error: (error, stack) =>
            Center(child: Text('Error loading details: $error')),
      ),
    );
  }
}
