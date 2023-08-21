import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_ui/business/model/commit_def.dart';
import 'package:flutter_ui/business/state/analysis_state.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/text_styles.dart';

class CommitsPage extends StatelessWidget {
  final AnalysisSection? content;
  late final List<CommitDef> commits;
  late final List<String> rest;

  CommitsPage({
    required this.content,
    super.key,
  }) {
    commits = (content?.rawContent.split('\n').skip(2).takeWhile((value) => !value.contains("⬆️")).toList() ?? [])
        .map(
          (e) => CommitDef.from([e]),
        )
        .toList()
      ..sort((a, b) => b.date.compareTo(a.date));

    rest = (content?.rawContent.split('\n').skip(2).skipWhile((value) => !value.contains("⬆️")).toList() ?? []);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 16.0),
          child: Text(
            "Commits",
            style: TSExtraLarge.muni.primary,
          ),
        ),
        Expanded(
          child: CustomScrollView(
            slivers: [
              SliverList.builder(
                itemCount: commits.length,
                itemBuilder: (context, index) {
                  return Container(
                    height: 48,
                    decoration: UnderlineTabIndicator(
                      borderSide: BorderSide(color: MColors.gray1, width: 1),
                      insets: EdgeInsets.zero,
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(width: 32),
                        if (index == 0 || index == commits.length - 1)
                          Transform.rotate(
                            angle: index != 0 ? pi : 0,
                            child: Stack(
                              children: [
                                Padding(
                                  padding: const EdgeInsets.only(top: 24.0),
                                  child: Container(
                                    width: 24,
                                    decoration: BoxDecoration(
                                      color: MColors.gray1,
                                    ),
                                  ),
                                ),
                                Center(
                                  child: Container(
                                    width: 24,
                                    height: 24,
                                    decoration: BoxDecoration(
                                      color: MColors.highlight,
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        if (index > 0 && index < commits.length - 1)
                          Container(
                            width: 24,
                            decoration: BoxDecoration(
                              color: MColors.gray1,
                            ),
                            child: Center(child: Container(width: 8, height: 8, color: MColors.highlight)),
                          ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: MCommitSmall(commit: commits[index]),
                        ),
                      ],
                    ),
                  );
                },
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 16.0),
                  child: Text(
                    "Commit details",
                    style: TSExtraLarge.muni.primary,
                  ),
                ),
              ),
              SliverList.builder(
                itemCount: rest.length,
                itemBuilder: (context, index) {
                  return Container(
                    height: 48,
                    color: MColors.randomColor(),
                    child: Center(
                      child: Text(rest[index]),
                    ),
                  );
                },
              )
            ],
          ),
        ),
      ],
    );
  }
}

class MCommitSmall extends StatelessWidget {
  final CommitDef commit;

  const MCommitSmall({
    required this.commit,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        RichText(
          text: TextSpan(
            children: [
              TextSpan(text: "Commit hash: "),
              TextSpan(text: commit.hash, style: TSMedium.bold.g1),
              TextSpan(text: " by "),
              TextSpan(text: commit.authorName, style: TSMedium.bold.primary),
            ],
            style: TSMedium.std.g1,
          ),
        ),
        RichText(
          text: TextSpan(
            children: [
              TextSpan(text: "On: "),
              TextSpan(text: commit.date.toString(), style: TSMedium.std.primary),
            ],
            style: TSMedium.std.g1,
          ),
        ),
      ],
    );
  }
}
