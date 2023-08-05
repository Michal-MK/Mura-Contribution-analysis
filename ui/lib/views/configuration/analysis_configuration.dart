// ignore_for_file: constant_identifier_names

import 'package:flutter/material.dart';
import 'package:flutter_ui/business/analysis.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/business/state/analysis_state.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/controllers/contributor_grouping_controller.dart';
import 'package:flutter_ui/ui/contributor_grouping.dart';
import 'package:flutter_ui/ui/settings_group.dart';
import 'package:flutter_ui/views/configuration/commit_picker_entry.dart';
import 'package:flutter_ui/views/configuration/folder_picker_entry.dart';
import 'package:flutter_ui/views/configuration/simple_text_entry.dart';
import 'package:flutter_ui/views/configuration/toggle_entry.dart';
import 'package:provider/provider.dart';

class AnalysisConfigurationPage extends StatefulWidget {
  const AnalysisConfigurationPage({super.key});

  @override
  State<AnalysisConfigurationPage> createState() => _AnalysisConfigurationPageState();
}

class _AnalysisConfigurationPageState extends State<AnalysisConfigurationPage> {
  late TextEditingController repositoryController;
  late TextEditingController headCommitController;
  late TextEditingController rootCommitController;
  late TextEditingController outputPathController;
  late TextEditingController ignoredExtensionsController;
  late TextEditingController sqContainerExitTimeoutController;
  late TextEditingController sqLoginController;
  late TextEditingController sqPasswordController;
  late TextEditingController sqPortController;
  late ContributorGroupingController contributorGroupingController;

  @override
  void didChangeDependencies() {
    var config = context.read<AnalysisController>().config;

    repositoryController = TextEditingController(text: config.repository);
    headCommitController = TextEditingController(text: config.headCommit);
    rootCommitController = TextEditingController(text: config.rootCommit);
    outputPathController = TextEditingController(text: config.outputPath);

    ignoredExtensionsController = TextEditingController(text: config.ignoredExtensions.join(', '));

    sqContainerExitTimeoutController = TextEditingController(text: config.sqContainerExitTimeout.toString());
    sqLoginController = TextEditingController(text: config.sqLogin);
    sqPasswordController = TextEditingController(text: config.sqPassword);
    sqPortController = TextEditingController(text: config.sqPort.toString());

    contributorGroupingController = ContributorGroupingController();

    super.didChangeDependencies();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AnalysisController>(
      builder: (context, analysisController, child) {
        return FocusScope(
          child: Scaffold(
            backgroundColor: MColors.background,
            body: Stack(
              children: [
                Positioned.fill(
                  child: ListView(
                    padding: const EdgeInsets.all(16.0),
                    children: [
                      FolderPickerEntry(
                        controller: repositoryController,
                        placeholder: "Repository",
                        description: "Select the repository to analyze. Either by pasting in the path, or by browsing for it.",
                        visibleCondition: () => true,
                        onSelected: (String? path) {
                          analysisController.config.repository = path ?? '';
                          analysisController.config.prescanMode = true;
                          Analysis.run(analysisController, context.read<MuraConfiguration>(), analysisController.config).then((value) {
                            setState(() {});
                          });
                        },
                      ),
                      CommitPickerEntry(
                        analysisController: analysisController,
                        controller: headCommitController,
                        placeholder: "Head Commit",
                        description: "Select the HEAD commit to analyze. Either by pasting in the commit hash, or by selecting it.",
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      CommitPickerEntry(
                        analysisController: analysisController,
                        controller: rootCommitController,
                        placeholder: "Root Commit",
                        description: "Select the root (first) commit to analyze. Either by pasting in the commit hash, or by selecting it.",
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      MContributorGrouping(
                        key: const PageStorageKey("MContributorGrouping"),
                        controller: contributorGroupingController,
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      FolderPickerEntry(
                        controller: outputPathController,
                        description: "Select the output path for the analysis. Either by pasting in the path, or by browsing for it. If not provided, a temporary directory will be used.",
                        placeholder: "Output Path",
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      ToggleEntry(
                        title: "Anonymous Mode",
                        description: "If enabled, the analysis will be run in anonymous mode. This means that no contributor names will appear, instead they will be replaced by generic \"Anonymous #n\".",
                        valueGetter: () => analysisController.config.anonymousMode,
                        valueSetter: (v) => analysisController.config.anonymousMode = v,
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      SettingsGroup(
                        title: "SonarQube",
                        description: "SonarQube is a tool for static code analysis. Docker is required to run SonarQube.",
                        visibleCondition: () => analysisController.repositoryValid,
                        children: [
                          ToggleEntry(
                            title: "Disable SonarQube Analysis",
                            description: "If enabled, the analysis will not use SonarQube.",
                            valueGetter: () => analysisController.config.noSonarQube,
                            valueSetter: (v) {
                              analysisController.config.noSonarQube = v;
                              setState(() {});
                            },
                            visibleCondition: () => analysisController.repositoryValid,
                          ),
                          ToggleEntry(
                            title: "SonarQube Non-Persistent Mode",
                            description: "If enabled, the analysis will not persist the SonarQube container. In most cases, this should be left disabled.",
                            valueGetter: () => analysisController.config.sqNoPersistence,
                            valueSetter: (v) => analysisController.config.sqNoPersistence = v,
                            visibleCondition: () => !analysisController.config.noSonarQube,
                          ),
                          ToggleEntry(
                            title: "Keep SonarQube Analysis Container",
                            description: "If enabled, the analysis will not remove the SonarQube container after the analysis is complete. This is useful in case the container exits abnormally for debugging purposes.",
                            valueGetter: () => analysisController.config.sqKeepAnalysisContainer,
                            valueSetter: (v) => analysisController.config.sqKeepAnalysisContainer = v,
                            visibleCondition: () => !analysisController.config.noSonarQube,
                          ),
                          SimpleTextEntry(
                            placeholder: "SonarQube Container Exit Timeout (ms)",
                            controller: sqContainerExitTimeoutController,
                            visibleCondition: () => !analysisController.config.noSonarQube,
                            numbersOnly: true,
                          ),
                          SimpleTextEntry(
                            placeholder: "SonarQube Login",
                            controller: sqLoginController,
                            visibleCondition: () => !analysisController.config.noSonarQube,
                          ),
                          SimpleTextEntry(
                            placeholder: "SonarQube Password",
                            controller: sqPasswordController,
                            visibleCondition: () => !analysisController.config.noSonarQube,
                          ),
                          SimpleTextEntry(
                            placeholder: "SonarQube Port",
                            controller: sqPortController,
                            visibleCondition: () => !analysisController.config.noSonarQube,
                            numbersOnly: true,
                          ),
                        ],
                      ),
                      ToggleEntry(
                        title: "Ignore Whitespace Changes",
                        description: "If enabled, the analysis will ignore whitespace-only changes in the repository. Ownership will not change. Common whitespace changes include indentation and line endings.",
                        valueGetter: () => analysisController.config.ignoreWhitespaceChanges,
                        valueSetter: (v) => analysisController.config.ignoreWhitespaceChanges = v,
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      SimpleTextEntry(
                        placeholder: 'Ignored Extensions',
                        description: 'Extensions to ignore when analyzing the repository. Extensions should be separated by ",".',
                        controller: ignoredExtensionsController,
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      SizedBox(height: 16.0),
                      ToggleEntry(
                        title: "Ignore Remote Repository",
                        description: "If enabled, the analysis will ignore the remote repository. (Issues and PullRequests will not be fetched.)",
                        valueGetter: () => analysisController.config.ignoreRemoteRepo,
                        valueSetter: (v) => analysisController.config.ignoreRemoteRepo = v,
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      ToggleEntry(
                        title: "Disable Graphs",
                        valueGetter: () => analysisController.config.noGraphs,
                        valueSetter: (v) => analysisController.config.noGraphs = v,
                        visibleCondition: () => analysisController.repositoryValid,
                      ),
                      if (analysisController.repositoryValid)
                        ElevatedButton(
                          child: Text('Run Analysis'),
                          onPressed: () async {
                            var muraConfig = context.read<MuraConfiguration>();
                            var tabs = context.read<TabController>();

                            await validate(analysisController);
                            await Analysis.run(analysisController, muraConfig, analysisController.config);
                            tabs.animateTo(2);
                          },
                        ),
                    ],
                  ),
                ),
                if (analysisController.analysisRunning)
                  Positioned.fill(
                    child: Container(
                      color: Colors.black.withOpacity(0.6),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          CircularProgressIndicator(
                            color: MColors.highlight,
                          ),
                          const SizedBox(
                            height: 16.0,
                          ),
                          Text(
                            analysisController.config.prescanMode ? "Checking repository..." : "Running Analysis...",
                            style: TSMedium.std.highlight,
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<bool> validate(AnalysisController analysisController) async {
    analysisController.config.repository = repositoryController.text;
    analysisController.config.headCommit = headCommitController.text;
    analysisController.config.rootCommit = rootCommitController.text;
    analysisController.config.outputPath = outputPathController.text;

    analysisController.config.sqContainerExitTimeout = int.parse(sqContainerExitTimeoutController.text);
    analysisController.config.sqLogin = sqLoginController.text;
    analysisController.config.sqPassword = sqPasswordController.text;
    analysisController.config.sqPort = int.parse(sqPortController.text);

    analysisController.config.contributorMap = contributorGroupingController.positions.entries.map((e) => e.value).toList();

    analysisController.config.prescanMode = false;

    return true;
  }
}
