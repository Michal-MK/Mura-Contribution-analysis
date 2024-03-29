import 'package:flutter/material.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/icons.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/ui/contributor_grouping.dart';

class MContributor extends StatelessWidget {
  final ContributorData contributorData;
  final Widget? trailing;

  const MContributor({
    required this.contributorData,
    this.trailing,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [MColors.highlight, MColors.gray5],
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
        ),
        borderRadius: BorderRadius.circular(8.0),
      ),
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        MIcons.contributor,
                        style: TSLarge.bold.g1,
                      ),
                      Expanded(
                        child: Text(contributorData.contributor.name, overflow: TextOverflow.ellipsis, maxLines: 1),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 4.0),
                        child: Icon(Icons.email, size: 20.0),
                      ),
                      Expanded(
                        child: Text(contributorData.contributor.email, overflow: TextOverflow.ellipsis, maxLines: 1),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            trailing ?? const SizedBox.shrink(),
          ],
        ),
      ),
    );
  }
}
