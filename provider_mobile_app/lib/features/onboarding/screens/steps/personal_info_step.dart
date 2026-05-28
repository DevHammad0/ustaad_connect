import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import '../../../../core/constants/app_colors.dart';
import '../../providers/onboarding_provider.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/utils/image_utils.dart';

class PersonalInfoStep extends ConsumerStatefulWidget {
  const PersonalInfoStep({super.key});

  @override
  ConsumerState<PersonalInfoStep> createState() => _PersonalInfoStepState();
}

class _PersonalInfoStepState extends ConsumerState<PersonalInfoStep> {
  final ImagePicker _picker = ImagePicker();
  
  late final TextEditingController _nameController;
  late final TextEditingController _cnicController;

  // Local preview files
  XFile? _localProfileFile;
  XFile? _localFrontFile;
  XFile? _localBackFile;

  // Loading states
  bool _profileUploading = false;
  bool _frontUploading = false;
  bool _backUploading = false;

  @override
  void initState() {
    super.initState();
    final draft = ref.read(onboardingProvider).draft;
    _nameController = TextEditingController(text: draft.fullName);
    _cnicController = TextEditingController(text: draft.cnic);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _cnicController.dispose();
    super.dispose();
  }

  Future<void> _pickAndUpload({
    required bool isProfile,
    required bool isFront,
    required bool isBack,
  }) async {
    try {
      final XFile? file = await _picker.pickImage(
        source: ImageSource.gallery,
        // imageQuality intentionally NOT set here — we compress manually below
      );
      if (file == null) return;

      // ── Compress & validate BEFORE showing preview ─────────────────────
      XFile compressed;
      try {
        compressed = await ImageUtils.compressForUpload(file);
      } on ImageSizeException catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(e.message),
              backgroundColor: Colors.red.shade700,
              duration: const Duration(seconds: 4),
            ),
          );
        }
        return;
      }

      setState(() {
        if (isProfile) {
          _localProfileFile = compressed;
          _profileUploading = true;
        } else if (isFront) {
          _localFrontFile = compressed;
          _frontUploading = true;
        } else if (isBack) {
          _localBackFile = compressed;
          _backUploading = true;
        }
      });

      final url =
          await ref.read(onboardingServiceProvider).uploadImage(compressed);

      final notifier = ref.read(onboardingProvider.notifier);
      final draft = ref.read(onboardingProvider).draft;

      if (isProfile) {
        notifier.updateDraft(draft.copyWith(profilePhotoUrl: url));
      } else if (isFront) {
        notifier.updateDraft(draft.copyWith(cnicFrontUrl: url));
      } else if (isBack) {
        notifier.updateDraft(draft.copyWith(cnicBackUrl: url));
      }
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
          if (isProfile) _profileUploading = false;
          if (isFront) _frontUploading = false;
          if (isBack) _backUploading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(onboardingProvider);
    final notifier = ref.read(onboardingProvider.notifier);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(28.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Tell us about yourself',
            style: GoogleFonts.poppins(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Provide your identity and verification documents to get started.',
            style: GoogleFonts.inter(
              fontSize: 15,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 30),
          
          // Profile Pic Selection
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
                  child: _profileUploading
                      ? const Center(child: CircularProgressIndicator())
                      : _localProfileFile != null
                          ? ClipOval(
                              child: kIsWeb
                                  ? Image.network(
                                      _localProfileFile!.path,
                                      width: 110,
                                      height: 110,
                                      fit: BoxFit.cover,
                                    )
                                  : Image.file(
                                      File(_localProfileFile!.path),
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
                      onPressed: () => _pickAndUpload(
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
          const SizedBox(height: 32),

          // Name and CNIC text inputs
          AppTextField(
            label: 'Full Name',
            controller: _nameController,
            hint: 'e.g. Ahmad Khan',
            prefixIcon: Icons.person_outline_rounded,
            onChanged: (val) {
              notifier.updateDraft(state.draft.copyWith(fullName: val));
            },
          ),
          const SizedBox(height: 20),
          AppTextField(
            label: 'CNIC Number',
            controller: _cnicController,
            hint: 'e.g. 35202-1234567-1',
            prefixIcon: Icons.badge_outlined,
            keyboardType: TextInputType.phone,
            onChanged: (val) {
              notifier.updateDraft(state.draft.copyWith(cnic: val));
            },
          ),
          const SizedBox(height: 32),

          // Verification Documents Card Section
          Text(
            'Verification Documents',
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Upload clear front and back photos of your CNIC.',
            style: GoogleFonts.inter(
              fontSize: 13,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 16),

          Row(
            children: [
              Expanded(
                child: _buildCnicCard(
                  label: 'CNIC Front',
                  localFile: _localFrontFile,
                  isUploading: _frontUploading,
                  onTap: () => _pickAndUpload(
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
                  localFile: _localBackFile,
                  isUploading: _backUploading,
                  onTap: () => _pickAndUpload(
                    isProfile: false,
                    isFront: false,
                    isBack: true,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCnicCard({
    required String label,
    required XFile? localFile,
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
            color: localFile != null
                ? AppColors.primary.withValues(alpha: 0.5)
                : Colors.black.withValues(alpha: 0.08),
            width: localFile != null ? 2 : 1,
          ),
        ),
        child: isUploading
            ? const Center(child: CircularProgressIndicator())
            : localFile != null
                ? Stack(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: kIsWeb
                            ? Image.network(
                                localFile.path,
                                width: double.infinity,
                                height: double.infinity,
                                fit: BoxFit.cover,
                              )
                            : Image.file(
                                File(localFile.path),
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
                      Icon(
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
