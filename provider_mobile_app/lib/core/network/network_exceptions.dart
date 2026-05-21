import 'package:dio/dio.dart';

class NetworkExceptions implements Exception {
  final String message;
  final int? statusCode;

  NetworkExceptions(this.message, {this.statusCode});

  factory NetworkExceptions.fromDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return NetworkExceptions('Connection timeout');
      case DioExceptionType.sendTimeout:
        return NetworkExceptions('Send timeout');
      case DioExceptionType.receiveTimeout:
        return NetworkExceptions('Receive timeout');
      case DioExceptionType.badCertificate:
        return NetworkExceptions('Bad certificate');
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        // Attempt to extract server error message if available
        final dynamic data = error.response?.data;
        String message = 'Unexpected error occurred';
        if (data is Map<String, dynamic>) {
          if (data['message'] != null) {
            message = data['message'].toString();
          } else if (data['detail'] != null) {
            message = data['detail'].toString();
          } else if (data['error'] != null) {
            message = data['error'].toString();
          }
        }
        return NetworkExceptions(message, statusCode: statusCode);
      case DioExceptionType.cancel:
        return NetworkExceptions('Request cancelled');
      case DioExceptionType.connectionError:
        return NetworkExceptions('No internet connection');
      case DioExceptionType.unknown:
        return NetworkExceptions('An unknown error occurred');
    }
  }

  @override
  String toString() => message;
}
