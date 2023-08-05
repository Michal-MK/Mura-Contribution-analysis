import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_ui/business/model/commit_def.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/ui/m_commit.dart';
import 'package:flutter_ui/views/configuration/simple_text_entry.dart';

class CommitSelection extends StatefulWidget {
  final List<CommitDef> commits;
  final String title;

  const CommitSelection({
    required this.commits,
    required this.title,
    super.key,
  });

  @override
  State<CommitSelection> createState() => _CommitSelectionState();
}

class _CommitSelectionState extends State<CommitSelection> {
  String oldFilter = "";
  TextEditingController controller = TextEditingController();

  ScrollController scrollController = ScrollController();


  late List<CommitDef> filteredCommits = widget.commits;

  @override
  void initState() {
    controller.addListener(() {
      if (controller.text != oldFilter) {
        setState(() {
          oldFilter = controller.text;
          if (controller.text.isEmpty) {
            filteredCommits = widget.commits;
            return;
          }
          filteredCommits = widget.commits
              .where(
                (w) =>
                    w.hash.contains(controller.text) ||
                    w.authorName.contains(controller.text) ||
                    w.date.toString().contains(controller.text) ||
                    w.message.toLowerCase().contains(
                          controller.text.toLowerCase(),
                        ),
              )
              .toList();
        });
      }
    });
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return FocusScope(
      child: KeyboardListener(
        autofocus: true,
        focusNode: FocusNode(),
        onKeyEvent: (value) {
          if(value.logicalKey == LogicalKeyboardKey.end) {
            scrollController.jumpTo(scrollController.position.maxScrollExtent);
          }
          if(value.logicalKey == LogicalKeyboardKey.home) {
            scrollController.jumpTo(scrollController.position.minScrollExtent);
          }
        },
        child: Container(
          color: MColors.gray7,
          margin: const EdgeInsets.only(left: 360),
          child: Material(
            color: Colors.transparent,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(widget.title, style: TSExtraLarge.muni.primary),
                  const SizedBox(height: 16.0),
                  SimpleTextEntry(
                    placeholder: "Search",
                    controller: controller,
                    visibleCondition: () => true,
                  ),
                  Expanded(
                    child: ListView.builder(
                      controller: scrollController,
                      itemCount: filteredCommits.length,
                      itemBuilder: (context, index) {
                        var commit = filteredCommits[index];
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 1.0),
                          child: MCommit(
                            commit: commit,
                            last: index == filteredCommits.length - 1,
                            first: index == 0,
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
