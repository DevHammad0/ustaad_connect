import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';
import 'core/session/session_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SessionManager.instance.init();
  SessionManager.onSessionExpired = () {
    appRouter.go('/login');
  };
  runApp(
    const ProviderScope(
      child: UstaadProviderApp(),
    ),
  );
}

class UstaadProviderApp extends StatelessWidget {
  const UstaadProviderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Ustaad Connect Provider',
      theme: AppTheme.lightTheme,
      routerConfig: appRouter,
      debugShowCheckedModeBanner: false,
    );
  }
}
