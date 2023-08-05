import 'package:flutter_ui/ui/contributor_grouping.dart';

class AnalysisConfiguration {
  bool anonymousMode = false;
  bool ignoreWhitespaceChanges = true;
  bool ignoreRemoteRepo = false;
  bool noGraphs = false;
  bool prescanMode = false;

  String repository = '';
  String headCommit = 'HEAD';
  String rootCommit = 'ROOT';
  String outputPath = '';

  List<List<ContributorData>> contributorMap = [];
  int hourEstimatePerContributor = 24;

  bool noSonarQube = false;
  bool sqNoPersistence = false;
  bool sqKeepAnalysisContainer = false;
  int sqContainerExitTimeout = 120;
  String sqLogin = 'admin';
  String sqPassword = 'admin';
  int sqPort = 8080;

  List<String> ignoredExtensions = [];

  List<String> constructContributorMap() {
    List<String> result = [];
    for (var i = 0; i < contributorMap.length; i++) {
      ContributorData primary = contributorMap[i].firstWhere((w) => w.isPrimary);
      for (var other in contributorMap[i]) {
        if (other == primary) continue;
        result.add('${primary.contributor.name}:${other.contributor.name}');
      }
    }
    return result;
  }
}
