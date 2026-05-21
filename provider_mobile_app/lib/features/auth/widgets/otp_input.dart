import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/constants/app_colors.dart';

class OtpInput extends StatelessWidget {
  final TextEditingController controller;
  final int length;

  const OtpInput({
    super.key,
    required this.controller,
    this.length = 4,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: List.generate(
        length,
        (index) => _OtpBox(
          index: index,
          controller: controller,
        ),
      ),
    );
  }
}

class _OtpBox extends StatefulWidget {
  final int index;
  final TextEditingController controller;

  const _OtpBox({required this.index, required this.controller});

  @override
  State<_OtpBox> createState() => _OtpBoxState();
}

class _OtpBoxState extends State<_OtpBox> {
  bool _isFocused = false;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: 68,
      height: 72,
      decoration: BoxDecoration(
        color: _isFocused
            ? AppColors.primary.withValues(alpha: 0.06)
            : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: _isFocused ? AppColors.primary : Colors.black.withValues(alpha: 0.10),
          width: _isFocused ? 2 : 1,
        ),
        boxShadow: _isFocused
            ? [
                BoxShadow(
                  color: AppColors.primary.withValues(alpha: 0.18),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ]
            : [],
      ),
      child: Focus(
        onFocusChange: (focused) => setState(() => _isFocused = focused),
        child: TextField(
          controller: TextEditingController(
            text: widget.controller.text.length > widget.index
                ? widget.controller.text[widget.index]
                : '',
          ),
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: 1,
          style: GoogleFonts.poppins(
            fontSize: 26,
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
            counterText: '',
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
            fillColor: Colors.transparent,
          ),
          onChanged: (value) {
            if (value.isNotEmpty) {
              FocusScope.of(context).nextFocus();
            } else {
              FocusScope.of(context).previousFocus();
            }

            String currentText = widget.controller.text;
            if (value.isNotEmpty) {
              if (currentText.length <= widget.index) {
                widget.controller.text = currentText + value;
              } else {
                widget.controller.text =
                    currentText.replaceRange(widget.index, widget.index + 1, value);
              }
            } else {
              if (currentText.length > widget.index) {
                widget.controller.text =
                    currentText.replaceRange(widget.index, widget.index + 1, '');
              }
            }
          },
        ),
      ),
    );
  }
}
