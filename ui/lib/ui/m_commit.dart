import 'package:flutter/material.dart';
import 'package:flutter_ui/business/model/commit_def.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/icons.dart';
import 'package:flutter_ui/constants/text_styles.dart';

class MCommit extends StatelessWidget {
  final CommitDef commit;
  final bool last;
  final bool first;

  const MCommit({
    required this.commit,
    required this.last,
    required this.first,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
        decoration: BoxDecoration(
          color: MColors.gray6,
          borderRadius: BorderRadius.circular(8.0),
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(8.0),
          child: InkWell(
            onTapUp: (details) {
              Navigator.pop(context, commit);
            },
            child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Text(
                              "Commit hash:",
                              style: TSMedium.std.primary,
                            ),
                            SizedBox(width: 8.0),
                            Text(
                              commit.hash,
                              style: TSMedium.bold.g1,
                            ),
                            if (first)
                              Padding(
                                padding: const EdgeInsets.only(left: 8.0),
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: MColors.highlight,
                                    borderRadius: BorderRadius.circular(8.0),
                                  ),
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 8.0),
                                    child: Text(
                                      "HEAD",
                                      style: TSMedium.bold.g1,
                                    ),
                                  ),
                                ),
                              ),
                            if (last)
                              Padding(
                                padding: const EdgeInsets.only(left: 8.0),
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: MColors.highlight,
                                    borderRadius: BorderRadius.circular(8.0),
                                  ),
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 8.0),
                                    child: Text(
                                      "ROOT",
                                      style: TSMedium.bold.g1,
                                    ),
                                  ),
                                ),
                              ),
                          ],
                        ),
                        Row(
                          children: [
                            Text(
                              "Author name:",
                              style: TSMedium.std.primary,
                            ),
                            SizedBox(width: 8.0),
                            Text(MIcons.contributor),
                            Text(
                              commit.authorName,
                              style: TSMedium.bold.g1,
                            ),
                          ],
                        ),
                        Row(
                          children: [
                            Text(
                              "Date:",
                              style: TSMedium.std.primary,
                            ),
                            SizedBox(width: 8.0),
                            Text(
                              commit.date.toString(),
                              style: TSMedium.bold.g1,
                            ),
                          ],
                        ),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "Message:",
                              style: TSMedium.std.primary,
                            ),
                            SizedBox(width: 8.0),
                            Text(
                              commit.message,
                              style: TSMedium.italic.g1,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  IgnorePointer(
                    child: SizedBox(
                      width: 48.0,
                      height: 48.0,
                      child: IconButton(
                        icon: Icon(
                          Icons.select_all,
                          size: 36.0,
                        ),
                        onPressed: () {},
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ));
  }
}
