import 'package:flutter/material.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/ui/contributor/m_contributor.dart';
import 'package:flutter_ui/ui/contributor_grouping.dart';

class MContributorGroupingEntry extends StatelessWidget {
  final ContributorData contributorData;
  final int positionIndex;
  final void Function(ContributorData contributorData, int positionIndex)? makePrimary;

  const MContributorGroupingEntry({
    required this.contributorData,
    required this.positionIndex,
    required this.makePrimary,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return MContributor(
      contributorData: contributorData,
      trailing: IconButton(
        icon: Icon(
          contributorData.isPrimary ? Icons.star : Icons.star_border,
          color: contributorData.isPrimary ? MColors.highlight : MColors.gray1,
        ),
        onPressed: () => makePrimary?.call(contributorData, positionIndex),
      ),
    );
  }
}
