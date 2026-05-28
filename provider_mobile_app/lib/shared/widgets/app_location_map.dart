import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../core/constants/app_colors.dart';

class AppLocationMap extends StatefulWidget {
  final LatLng center;
  final LatLng marker;
  final double zoom;
  final double height;
  final String? label;
  final ValueChanged<LatLng>? onTap;

  const AppLocationMap({
    super.key,
    required this.center,
    required this.marker,
    this.zoom = 13,
    this.height = 220,
    this.label,
    this.onTap,
  });

  @override
  State<AppLocationMap> createState() => _AppLocationMapState();
}

class _AppLocationMapState extends State<AppLocationMap> {
  late final MapController _mapController;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
  }

  @override
  void didUpdateWidget(covariant AppLocationMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.center.latitude != oldWidget.center.latitude ||
        widget.center.longitude != oldWidget.center.longitude) {
      // Use post-frame callback to ensure the map controller is ready
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          _mapController.move(widget.center, widget.zoom);
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: SizedBox(
        height: widget.height,
        child: Stack(
          children: [
            FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: widget.center,
                initialZoom: widget.zoom,
                onTap: widget.onTap == null ? null : (_, point) => widget.onTap!(point),
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.ustaad.provider',
                ),
                MarkerLayer(
                  markers: [
                    Marker(
                      point: widget.marker,
                      width: 54,
                      height: 54,
                      child: const _PinMarker(),
                    ),
                  ],
                ),
              ],
            ),
            if (widget.label != null)
              Positioned(
                top: 12,
                left: 12,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: AppColors.darkTeal.withValues(alpha: 0.88),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    child: Text(
                      widget.label!,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _PinMarker extends StatelessWidget {
  const _PinMarker();

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: AppColors.error,
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white, width: 3),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.18),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: const Icon(Icons.location_on, color: Colors.white, size: 18),
        ),
      ],
    );
  }
}
