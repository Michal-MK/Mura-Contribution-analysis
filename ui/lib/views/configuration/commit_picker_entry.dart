import 'package:flutter/material.dart';
import 'package:fluent_ui/fluent_ui.dart' as fluent_ui;
import 'package:flutter_ui/business/state/analysis_state.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/ui/commit_selection.dart';
import 'package:flutter_ui/views/configuration/host_page.dart';

class CommitPickerEntry extends StatelessWidget {
  final AnalysisController analysisController;
  final String placeholder;
  final bool Function() visibleCondition;
  final String? description;
  final TextEditingController controller;

  const CommitPickerEntry({
    required this.analysisController,
    required this.controller,
    required this.placeholder,
    required this.visibleCondition,
    this.description,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    if (!visibleCondition()) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: ConfigurationHostPage.ENTRY_PADDING),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(placeholder, style: TSLarge.muni.entry),
          if (description != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Text(description!, style: TSMedium.italic.entry),
            ),
          Row(
            children: [
              Expanded(
                child: fluent_ui.TextBox(
                  placeholder: placeholder,
                  controller: controller,
                ),
              ),
              const SizedBox(width: 16.0),
              ElevatedButton(
                child: Text('Select'),
                onPressed: () async {
                  var commit = await showDialog(
                    context: context,
                    builder: (context) => CommitSelection(
                      title: placeholder,
                      commits: analysisController.getPreScanCommits(),
                    ),
                  );
                  if (commit != null) {
                    controller.text = commit.hash;
                  }
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}
