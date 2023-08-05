import 'package:flutter/material.dart';
import 'package:flutter_ui/business/configuration/configuration.dart';
import 'package:flutter_ui/business/model/commit_def.dart';
import 'package:flutter_ui/business/model/contributor.dart';
import 'package:flutter_ui/business/model/parser_helper.dart';

class AnalysisController extends ChangeNotifier {
  List<AnalysisSection> sections = [];
  List<AnalysisSection> prescanSections = [];

  AnalysisConfiguration config = AnalysisConfiguration();

  bool analysisRunning = false;

  bool _repositoryValid = false;
  bool get repositoryValid => _repositoryValid;

  void repositoryValidated() {
    _repositoryValid = true;
    notifyListeners();
  }

  void collectionChanged() {
    notifyListeners();
  }

  List<Contributor> getPreScanContributors() {
    if (prescanSections.isEmpty) return [];
    return prescanSections //
        .getSection("contributors")
        .content
        .strip()
        .map((m) {
      var cleaned = m.replaceAll(" ([])", "");
      var aliases = cleaned.split(RegExp(r'[(\[,\])]')).where((element) => element.isNotEmpty).toList();
      return Contributor.from(aliases);
    }).toList();
  }

  void analysisStart() {
    analysisRunning = true;
    if (config.prescanMode) {
      _repositoryValid = false;
    }
    notifyListeners();
  }

  void analysisEnd() {
    analysisRunning = false;
    notifyListeners();
  }

  List<CommitDef> getPreScanCommits() {
    if (prescanSections.isEmpty) return [];
    return prescanSections //
        .getSection("commits")
        .content
        .strip()
        .map((m) => CommitDef.from([m])).toList();
  }
}

class AnalysisSection {
  String title;
  String rawContent;

  List<String> get content => rawContent.split('\n');

  AnalysisSection(this.title, this.rawContent);
}
