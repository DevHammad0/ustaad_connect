import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/profile_provider.dart';
import '../../../shared/widgets/app_primary_button.dart';
import '../../../core/constants/app_colors.dart';

class ServiceSettingsScreen extends ConsumerStatefulWidget {
  const ServiceSettingsScreen({super.key});

  @override
  ConsumerState<ServiceSettingsScreen> createState() =>
      _ServiceSettingsScreenState();
}

class _ServiceSettingsScreenState extends ConsumerState<ServiceSettingsScreen> {
  final _feeController = TextEditingController();
  String _selectedCategory = '';

  @override
  void initState() {
    super.initState();
    final profile = ref.read(profileProvider).value;
    if (profile != null) {
      _feeController.text = profile.visitFee.toStringAsFixed(0);
      _selectedCategory = profile.serviceCategory;
    }
  }

  @override
  void dispose() {
    _feeController.dispose();
    super.dispose();
  }

  void _save() async {
    final profile = ref.read(profileProvider).value;
    if (profile == null) return;
    final updated = profile.copyWith(
      serviceCategory: _selectedCategory,
      visitFee: double.tryParse(_feeController.text) ?? profile.visitFee,
    );

    final success = await ref.read(profileProvider.notifier).updateProfile(updated);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Service settings updated')),
        );
        context.pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to update settings.'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            pinned: true,
            expandedHeight: 130,
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
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text('Service Settings',
                            style: GoogleFonts.poppins(
                              color: Colors.white,
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.5,
                            )),
                        Text('Category, fees & coverage areas',
                            style: GoogleFonts.inter(
                              color: AppColors.textOnDarkMuted,
                              fontSize: 12,
                            )),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 40),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                _Label('Service Category'),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _selectedCategory.isNotEmpty
                      ? _selectedCategory
                      : null,
                  items: [
                    'AC Repair',
                    'Plumbing',
                    'Electrician',
                    'Carpenter',
                    'Cleaning'
                  ]
                      .map((e) => DropdownMenuItem(
                          value: e,
                          child: Text(e, style: GoogleFonts.inter())))
                      .toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => _selectedCategory = val);
                  },
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.build_circle_outlined),
                    hintText: 'Select category',
                    hintStyle: GoogleFonts.inter(
                        color: AppColors.textSecondary),
                  ),
                ),
                const SizedBox(height: 20),
                _Label('Default Visit Fee (Rs)'),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _feeController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.payments_outlined),
                    hintText: 'e.g. 500',
                  ),
                ),
                const SizedBox(height: 36),
                AppPrimaryButton(
                  text: 'Save Configuration',
                  icon: Icons.check_rounded,
                  onPressed: _save,
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _Label extends StatelessWidget {
  final String text;
  const _Label(this.text);
  @override
  Widget build(BuildContext context) => Text(
        text,
        style: GoogleFonts.poppins(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
      );
}
