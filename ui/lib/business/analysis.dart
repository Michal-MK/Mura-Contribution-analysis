import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_ui/business/configuration/configuration.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/business/state/analysis_state.dart';

class Analysis {
  static Future<AnalysisResult> run(AnalysisController controller, MuraConfiguration toolConfig, AnalysisConfiguration analysisConfig) async {
    controller.sections.clear();
    controller.prescanSections.clear();
    controller.collectionChanged();

    controller.analysisStart();

    var utf8 = Encoding.getByName("utf-8");
    var result = await Process.start(
      toolConfig.pyPath,
      workingDirectory: toolConfig.muraPath,
      [
        toolConfig.muraPath + r"\mura.py",
        ...["-r", analysisConfig.repository],
        analysisConfig.noSonarQube ? "--no-sonarqube" : "",
        analysisConfig.noGraphs ? "--no-graphs" : "",
        ...["--head", analysisConfig.headCommit],
        ...["--root", analysisConfig.rootCommit],
        analysisConfig.outputPath.isEmpty ? "" : "--output-path",
        analysisConfig.outputPath,
        analysisConfig.anonymousMode ? "--anonymous-mode" : "",
        analysisConfig.ignoreWhitespaceChanges ? "--ignore-whitespace-changes" : "",
        analysisConfig.ignoreRemoteRepo ? "--ignore-remote-repo" : "",
        ...["--sq-login", analysisConfig.sqLogin],
        ...["--sq-password", analysisConfig.sqPassword],
        ...["--sq-port", analysisConfig.sqPort.toString()],
        analysisConfig.sqNoPersistence ? "--sq-no-persistence" : "",
        analysisConfig.sqKeepAnalysisContainer ? "--sq-keep-analysis-container" : "",
        analysisConfig.prescanMode ? "--prescan-mode" : "",
        analysisConfig.contributorMap.isNotEmpty ? "--contributor-map" : "", ...analysisConfig.constructContributorMap(),
      ]..retainWhere((element) => element.isNotEmpty),
      environment: {"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "True"},
    );
    result.exitCode.then((value) {
      if (value == 0) {
        controller.repositoryValidated();
      }
      controller.analysisEnd();
    });
    result.stdout.transform(utf8!.decoder).listen((s) => consumer(controller, s));
    result.stderr.transform(utf8.decoder).listen(errConsumer);
    return AnalysisResult();
  }

  static String title = "";
  static String outBuffer = "";

  static void consumer(AnalysisController controller, String s) {
    for (String line in s.split('\n')) {
      if (line.contains('\r')) {
        // Remove carriage return on Windows
        line = line.replaceAll('\r', '');
      }

      if (line.isEmpty) continue;

      if (kDebugMode) {
        print(line);
      }

      if (line.contains(" +")) {
        // Header
        if (s[s.indexOf(" +") + 2] == '\r' || s[s.indexOf(" +") + 2] == '\n') {
          // Internal Header, no special action
          continue;
        } else {
          // On a new header, clear the buffer and try to parse the title
          outBuffer = "";
          title = s.substring(s.indexOf(" +") + 2).split('\n').first;
        }
      } else if (line.contains("  ")) {
        // End of section
        var section = AnalysisSection(title, outBuffer);
        if (controller.config.prescanMode) {
          controller.prescanSections.add(section);
        } else {
          controller.sections.add(section);
        }
        controller.collectionChanged();
        outBuffer = "";
        continue;
      }
      outBuffer += "$line\n";
    }
  }

  static void errConsumer(String s) {
    print(s);
  }
}

class AnalysisResult {
  // final ProcessResult result;

  AnalysisResult();

  // bool get success => result.exitCode == 0;

  // String get output => result.stdout.toString();

  // List<String> get lines => output.split("\n");

  // String get error => result.stderr.toString();
}
