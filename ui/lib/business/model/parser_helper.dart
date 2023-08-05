import 'package:flutter_ui/business/state/analysis_state.dart';

extension ModelParserHelper on List<String> {
  static const String separator = "=====";

  List<String> strip() {
    var lastSeparator = lastIndexWhere((l) => l.contains(separator));
    return skip(2) //
        .take(lastSeparator - 2)
        .toList();
  }
}

extension AnalysisSectionHelper on List<AnalysisSection> {
  AnalysisSection getSection(String title) {
    return firstWhere((w) => w.title.toLowerCase().contains(title.toLowerCase()));
  }
}
