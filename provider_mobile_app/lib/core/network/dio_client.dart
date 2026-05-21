import 'package:dio/dio.dart';
import 'api_endpoints.dart';
import 'network_exceptions.dart';
import '../session/session_manager.dart';

class DioClient {
  late final Dio _dio;

  DioClient() {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiEndpoints.baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        responseType: ResponseType.json,
      ),
    );

    _dio.interceptors.addAll([
      // Token Interceptor
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Inject the required X-App-Secret header for all requests
          options.headers[ApiEndpoints.appSecretHeader] = ApiEndpoints.appSecret;

          // Add Content-Type only for requests with a body (POST, PUT, PATCH)
          if (options.method == 'POST' || options.method == 'PUT' || options.method == 'PATCH') {
            options.headers['Content-Type'] = 'application/json';
          }

          return handler.next(options);
        },
        onError: (DioException error, handler) async {
          // TODO: Handle 401 Unauthorized (token refresh logic or logout)
          // if (error.response?.statusCode == 401) { ... }
          return handler.next(error);
        },
      ),
      // Logger Interceptor
      LogInterceptor(
        request: true,
        requestHeader: true,
        requestBody: true,
        responseHeader: true,
        responseBody: true,
        error: true,
      ),
    ]);
  }

  Dio get dio => _dio;

  // Placeholder functions for future integration
  
  Future<Response> get(String url, {Map<String, dynamic>? queryParameters}) async {
    try {
      final response = await _dio.get(url, queryParameters: queryParameters);
      return response;
    } on DioException catch (e) {
      throw NetworkExceptions.fromDioError(e);
    }
  }

  Future<Response> post(String url, {dynamic data, Map<String, dynamic>? queryParameters}) async {
    try {
      final response = await _dio.post(url, data: data, queryParameters: queryParameters);
      return response;
    } on DioException catch (e) {
      throw NetworkExceptions.fromDioError(e);
    }
  }

  Future<Response> put(String url, {dynamic data, Map<String, dynamic>? queryParameters}) async {
    try {
      final response = await _dio.put(url, data: data, queryParameters: queryParameters);
      return response;
    } on DioException catch (e) {
      throw NetworkExceptions.fromDioError(e);
    }
  }
}
