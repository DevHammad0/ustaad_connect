import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import '../../../../core/constants/app_colors.dart';
import '../../../../shared/widgets/app_primary_button.dart';
import '../../../../shared/utils/image_utils.dart';
import '../../profile/providers/profile_provider.dart';
import '../../profile/models/profile_model.dart';
import '../../onboarding/services/onboarding_service.dart';
import '../providers/auth_provider.dart';

class VerificationScreen extends ConsumerStatefulWidget {
  const VerificationScreen({super.key});

  @override
  ConsumerState<VerificationScreen> createState() => _VerificationScreenState();
}

class _VerificationScreenState extends ConsumerState<VerificationScreen>
    with SingleTickerProviderStateMixin {
  final ImagePicker _picker = ImagePicker();

  // Local picked file paths
  String? _localProfileUrl;
  String? _localFrontUrl;
  String? _localBackUrl;

  bool _isProfileUploading = false;
  bool _isFrontUploading = false;
  bool _isBackUploading = false;
  bool _isSubmitting = false;

  bool _editMode = false;

  late AnimationController _animController;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeOut);
    _animController.forward();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  Future<void> _pickAndUploadImage({
    required bool isProfile,
    required bool isFront,
    required bool isBack,
  }) async {
    try {
      final XFile? file = await _picker.pickImage(
        source: ImageSource.gallery,
      );
      if (file == null) return;

      // Compress and validate size
      XFile compressed;
      try {
        compressed = await ImageUtils.compressForUpload(file);
      } on ImageSizeException catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(e.message),
              backgroundColor: Colors.red.shade700,
            ),
          );
        }
        return;
      }

      setState(() {
        if (isProfile) _isProfileUploading = true;
        if (isFront) _isFrontUploading = true;
        if (isBack) _isBackUploading = true;
      });

      // Upload to server using OnboardingService's helper
      final url = await OnboardingService().uploadImage(compressed);

      setState(() {
        if (isProfile) _localProfileUrl = url;
        if (isFront) _localFrontUrl = url;
        if (isBack) _localBackUrl = url;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Upload failed: $e'),
            backgroundColor: Colors.red.shade700,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          if (isProfile) _isProfileUploading = false;
          if (isFront) _isFrontUploading = false;
          if (isBack) _isBackUploading = false;
        });
      }
    }
  }

  Future<void> _submitVerification(ProviderProfileModel currentProfile) async {
    final cnic = currentProfile.cnic;
    final profileUrl = _localProfileUrl ?? currentProfile.profilePhotoUrl;
    final frontUrl = _localFrontUrl ?? currentProfile.cnicFrontUrl;
    final backUrl = _localBackUrl ?? currentProfile.cnicBackUrl;

    if (cnic.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('CNIC is missing. Please re-register or contact support.')),
      );
      return;
    }
    if (profileUrl.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please upload your profile photo')),
      );
      return;
    }
    if (frontUrl.isEmpty || backUrl.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please upload both CNIC Front and Back photos')),
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    final updated = currentProfile.copyWith(
      cnic: cnic,
      profilePhotoUrl: profileUrl,
      cnicFrontUrl: frontUrl,
      cnicBackUrl: backUrl,
    );

    final success = await ref.read(profileProvider.notifier).updateProfile(updated);

    setState(() {
      _isSubmitting = false;
      if (success) {
        _editMode = false;
      }
    });

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Documents submitted successfully!'),
            backgroundColor: AppColors.primary,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Failed to submit documents. Please try again.'),
            backgroundColor: Colors.red.shade700,
          ),
        );
      }
    }
  }

  Future<void> _checkStatus() async {
    // Invalidate profileProvider to fetch fresh data from server
    ref.invalidate(profileProvider);
    final profileAsync = ref.read(profileProvider);
    profileAsync.whenOrNull(
      data: (profile) {
        if (profile.isVerified) {
          context.go('/dashboard');
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Still under review. We appreciate your patience!'),
              duration: Duration(seconds: 2),
            ),
          );
        }
      },
    );
  }

  void _handleLogout() {
    ref.read(authProvider.notifier).logout();
    context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(profileProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(
          'Verification Center',
          style: GoogleFonts.poppins(
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Colors.red),
            onPressed: _handleLogout,
            tooltip: 'Logout',
          ),
        ],
      ),
      body: profileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('Error loading profile: $error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.invalidate(profileProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (profile) {
          // If already verified, auto-redirect to dashboard
          if (profile.isVerified) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted) context.go('/dashboard');
            });
            return const Center(child: CircularProgressIndicator());
          }


          final hasSubmitted = profile.cnic.isNotEmpty &&
              profile.profilePhotoUrl.isNotEmpty &&
              profile.cnicFrontUrl.isNotEmpty &&
              profile.cnicBackUrl.isNotEmpty;

          final showPendingStatus = hasSubmitted && !_editMode;

          return FadeTransition(
            opacity: _fadeAnim,
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: showPendingStatus
                  ? _buildPendingStatusView(profile)
                  : _buildUploadFormView(profile),
            ),
          );
        },
      ),
    );
  }

  Widget _buildPendingStatusView(ProviderProfileModel profile) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const SizedBox(height: 40),
        Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.schedule_rounded,
            size: 56,
            color: AppColors.primary,
          ),
        ),
        const SizedBox(height: 28),
        Text(
          'Verification Pending',
          style: GoogleFonts.poppins(
            fontSize: 24,
            fontWeight: FontWeight.w800,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          'Your profile is currently under review by our administrative team. Verification typically completes within 24 hours.',
          textAlign: TextAlign.center,
          style: GoogleFonts.inter(
            fontSize: 15,
            color: AppColors.textSecondary,
            height: 1.6,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Once verified, you will immediately start receiving job offers.',
          textAlign: TextAlign.center,
          style: GoogleFonts.inter(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: AppColors.darkTeal,
            height: 1.6,
          ),
        ),
        const SizedBox(height: 48),
        AppPrimaryButton(
          text: 'Check Verification Status',
          onPressed: _checkStatus,
        ),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: () {
            setState(() {
              _editMode = true;
            });
          },
          icon: const Icon(Icons.edit_rounded),
          label: const Text('Update / Edit Documents'),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.textPrimary,
            minimumSize: const Size.fromHeight(50),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            side: BorderSide(color: Colors.black.withValues(alpha: 0.12)),
          ),
        ),
        const SizedBox(height: 16),
        TextButton(
          onPressed: _handleLogout,
          child: Text(
            'Logout',
            style: GoogleFonts.poppins(
              color: Colors.red,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildUploadFormView(ProviderProfileModel profile) {
    final profileUrl = _localProfileUrl ?? profile.profilePhotoUrl;
    final frontUrl = _localFrontUrl ?? profile.cnicFrontUrl;
    final backUrl = _localBackUrl ?? profile.cnicBackUrl;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 8,
          children: [
            Text(
              'Submit Documents',
              style: GoogleFonts.poppins(
                fontSize: 26,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
                letterSpacing: -0.5,
              ),
            ),
            const Icon(
              Icons.security_rounded,
              color: AppColors.primary,
              size: 28,
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Upload your profile photo and CNIC credentials to request admin verification.',
          style: GoogleFonts.inter(
            fontSize: 14,
            color: AppColors.textSecondary,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 28),

        // Profile Picture Upload
        Center(
          child: Stack(
            children: [
              Container(
                width: 110,
                height: 110,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: AppColors.primary.withValues(alpha: 0.2),
                    width: 2,
                  ),
                ),
                child: _isProfileUploading
                    ? const Center(child: CircularProgressIndicator())
                    : profileUrl.isNotEmpty
                        ? ClipOval(
                            child: Image.network(
                              profileUrl,
                              width: 110,
                              height: 110,
                              fit: BoxFit.cover,
                            ),
                          )
                        : const Icon(Icons.person_rounded,
                            size: 60, color: AppColors.primary),
              ),
              Positioned(
                bottom: 0,
                right: 0,
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.darkTeal,
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 2.5),
                  ),
                  child: IconButton(
                    padding: EdgeInsets.zero,
                    icon: const Icon(Icons.camera_alt_rounded,
                        color: Colors.white, size: 16),
                    onPressed: () => _pickAndUploadImage(
                      isProfile: true,
                      isFront: false,
                      isBack: false,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),


        // CNIC Front & Back Cards
        Text(
          'CNIC Scans',
          style: GoogleFonts.poppins(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildCnicCard(
                label: 'CNIC Front',
                url: frontUrl,
                isUploading: _isFrontUploading,
                onTap: () => _pickAndUploadImage(
                  isProfile: false,
                  isFront: true,
                  isBack: false,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _buildCnicCard(
                label: 'CNIC Back',
                url: backUrl,
                isUploading: _isBackUploading,
                onTap: () => _pickAndUploadImage(
                  isProfile: false,
                  isFront: false,
                  isBack: true,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 36),

        AppPrimaryButton(
          text: 'Submit for Verification',
          isLoading: _isSubmitting,
          onPressed: () => _submitVerification(profile),
        ),
        if (profile.cnic.isNotEmpty) ...[
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: TextButton(
              onPressed: () {
                setState(() {
                  _editMode = false;
                });
              },
              child: Text(
                'Cancel Edit',
                style: GoogleFonts.poppins(
                  fontWeight: FontWeight.w600,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildCnicCard({
    required String label,
    required String url,
    required bool isUploading,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: isUploading ? null : onTap,
      child: Container(
        height: 120,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: url.isNotEmpty
                ? AppColors.primary.withValues(alpha: 0.5)
                : Colors.black.withValues(alpha: 0.08),
            width: url.isNotEmpty ? 2 : 1,
          ),
        ),
        child: isUploading
            ? const Center(child: CircularProgressIndicator())
            : url.isNotEmpty
                ? Stack(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: Image.network(
                          url,
                          width: double.infinity,
                          height: double.infinity,
                          fit: BoxFit.cover,
                        ),
                      ),
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.black.withValues(alpha: 0.3),
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      const Center(
                        child: Icon(
                          Icons.edit_rounded,
                          color: Colors.white,
                          size: 28,
                        ),
                      ),
                    ],
                  )
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.cloud_upload_outlined,
                        color: AppColors.primary,
                        size: 32,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        label,
                        style: GoogleFonts.poppins(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
      ),
    );
  }
}
