import 'package:flutter/foundation.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'dart:io' as io;

/// Maximum allowed source file size before compression: 5 MB
const int kMaxSourceBytes = 5 * 1024 * 1024;

/// Target compressed size goal: 500 KB
const int kTargetCompressedBytes = 500 * 1024;

class ImageSizeException implements Exception {
  final String message;
  const ImageSizeException(this.message);
  @override
  String toString() => message;
}

class ImageUtils {
  /// Compresses [sourceFile] and returns a new [XFile].
  ///
  /// Throws [ImageSizeException] if the source file exceeds 5 MB.
  static Future<XFile> compressForUpload(XFile sourceFile) async {
    final sourceSize = await sourceFile.length();
    if (sourceSize > kMaxSourceBytes) {
      final kb = (sourceSize / 1024).round();
      throw ImageSizeException(
        'Image is too large ($kb KB). Please choose an image smaller than 5 MB.',
      );
    }

    if (kIsWeb) {
      // On Web, flutter_image_compress's file-based compression is not supported
      // and web assembly is required. We can try compressWithList or fallback.
      try {
        final bytes = await sourceFile.readAsBytes();
        final compressedBytes = await FlutterImageCompress.compressWithList(
          bytes,
          quality: 75,
          minWidth: 1024,
          minHeight: 1024,
        );
        if (compressedBytes.length < bytes.length) {
          return XFile.fromData(compressedBytes, mimeType: 'image/jpeg');
        }
      } catch (e) {
        // Fallback to original if compression fails or is unsupported on web
        debugPrint('Web image compression failed: $e');
      }
      return sourceFile;
    }

    // Mobile implementation (uses dart:io safely inside non-web block)
    final tempDir = io.Directory.systemTemp;
    final ts = DateTime.now().millisecondsSinceEpoch;
    final outPath = '${tempDir.path}/compressed_$ts.jpg';

    // First pass: quality 75
    XFile? result = await FlutterImageCompress.compressAndGetFile(
      sourceFile.path,
      outPath,
      quality: 75,
      minWidth: 1024,
      minHeight: 1024,
      keepExif: false,
      format: CompressFormat.jpeg,
    );

    if (result == null) {
      return sourceFile; // fallback: use original
    }

    final compressedFile = io.File(result.path);
    final compressedSize = await compressedFile.length();

    // Second pass if still > 500 KB
    if (compressedSize > kTargetCompressedBytes) {
      final outPath2 = '${tempDir.path}/compressed2_$ts.jpg';
      XFile? result2 = await FlutterImageCompress.compressAndGetFile(
        sourceFile.path,
        outPath2,
        quality: 50,
        minWidth: 1024,
        minHeight: 1024,
        keepExif: false,
        format: CompressFormat.jpeg,
      );
      if (result2 != null) {
        return result2;
      }
    }

    return result;
  }

  /// Returns a human-readable file size string e.g. "1.2 MB" or "340 KB"
  static String formatBytes(int bytes) {
    if (bytes >= 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / 1024).round()} KB';
  }
}
