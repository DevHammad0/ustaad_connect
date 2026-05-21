class EstimateModel {
  final String requestId;
  final double minCost;
  final double maxCost;
  final String? note;
  final String status;

  const EstimateModel({
    required this.requestId,
    required this.minCost,
    required this.maxCost,
    this.note,
    this.status = 'Pending',
  });

  Map<String, dynamic> toJson() {
    return {
      'requestId': requestId,
      'minCost': minCost,
      'maxCost': maxCost,
      'note': note,
      'status': status,
    };
  }
}
