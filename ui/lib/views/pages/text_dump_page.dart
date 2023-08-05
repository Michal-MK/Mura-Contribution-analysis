import 'package:flutter/material.dart';
import 'package:flutter_ui/business/state/analysis_state.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/views/pages/page_base.dart';

class TextDumpPage extends StatelessWidget {
  final AnalysisSection? content;

  const TextDumpPage({
    required this.content,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return PageBase(
      title: content?.content.length != null ? content!.content[1] : "",
      child: SelectableRegion(
        focusNode: FocusNode(),
        selectionControls: MaterialTextSelectionControls(),
        child: ListView.builder(
          itemCount: content?.content.length != null ? content!.content.length - 4 : 0,
          itemBuilder: (context, index) {
            var actIndex = index + 2;
            return Text(content?.content[actIndex] ?? "", style: TSMedium.std.g1);
          },
        ),
      ),
    );
  }
}
