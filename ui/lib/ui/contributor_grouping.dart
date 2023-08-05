import 'package:flutter/material.dart';
import 'package:flutter_ui/business/model/contributor.dart';
import 'package:flutter_ui/business/state/analysis_state.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/controllers/contributor_grouping_controller.dart';
import 'package:flutter_ui/ui/m_contributor.dart';
import 'package:flutter_ui/views/configuration/host_page.dart';
import 'package:flutter_ui/views/home_content.dart';
import 'package:provider/provider.dart';

class MContributorGrouping extends StatefulWidget {
  final bool Function() visibleCondition;
  final ContributorGroupingController controller;

  const MContributorGrouping({
    required this.visibleCondition,
    required this.controller,
    super.key,
  });

  @override
  State<MContributorGrouping> createState() => _MContributorGroupingState();
}

class _MContributorGroupingState extends State<MContributorGrouping> {
  static const double widthChangeThreshold = 1600.0;
  Size mediaQuery = const Size(0, 0);
  bool get isHor => mediaQuery.width > widthChangeThreshold;
  Expanded? sizedWidget; // Used to get the width of the widget for dragging
  double sizedWidgetWidth = 0.0;

  @override
  void didChangeDependencies() {
    AnalysisController analysisController = context.read<AnalysisController>();
    analysisController.addListener(() {
      // Populate positions
      var preScanContributors = analysisController.getPreScanContributors();
      for (var i = 0; i < preScanContributors.length; i++) {
        widget.controller.positions[i] = [ContributorData(Contributor(name: preScanContributors[i].name, email: preScanContributors[i].email), true)];

        // Populate aliases
        for (var j = 1; j < preScanContributors[i].aliases.length; j++) {
          widget.controller.positions[i]!.add(ContributorData(Contributor(name: preScanContributors[i].aliases[j].name, email: preScanContributors[i].aliases[j].email), false));
        }
      }
      bucket.writeState(context, widget.controller.positions);
    });
    widget.controller.positions = bucket.readState(context) ?? {};
    mediaQuery = MediaQuery.sizeOf(context);
    super.didChangeDependencies();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.visibleCondition()) {
      return const SizedBox.shrink();
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // Ensure all widgets are sized
      if (sizedWidget != null) {
        sizedWidgetWidth = ((sizedWidget!.key as GlobalKey).currentContext?.size?.width ?? 16.0) - 16.0;
      }
    });
    return Consumer<AnalysisController>(
      builder: (context, value, child) {
        return Padding(
          padding: const EdgeInsets.only(bottom: ConfigurationHostPage.ENTRY_PADDING),
          child: Container(
            decoration: BoxDecoration(
              color: MColors.gray5,
              borderRadius: BorderRadius.circular(8.0),
            ),
            height: mediaQuery.width > widthChangeThreshold ? 320 : null,
            child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: Column(
                crossAxisAlignment: isHor ? CrossAxisAlignment.stretch : CrossAxisAlignment.start,
                children: [
                  Text("Contributor Grouping", style: TSLarge.muni.entry),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16.0),
                    child: Text("Drag and drop contributors to group them together. The first contributor in each group will be used as the primary contributor. This can be overridden by \"Starring\" a contributor.",
                        style: TSMedium.italic.entry),
                  ),
                  if (mediaQuery.width > widthChangeThreshold) horizontal() else ...vertical(),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  List<Widget> vertical() {
    List<Widget> ret = [];
    for (var i = 0; i < widget.controller.positions.length; i++) {
      ret.add(
        Padding(
          padding: const EdgeInsets.all(2.0),
          child: SizedBox(
            height: 87,
            child: dragTarget(i),
          ),
        ),
      );
    }
    ret.add(addNewGroup());

    return ret;
  }

  Widget horizontal() {
    return Expanded(
      child: Row(
        mainAxisAlignment: MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (var i = 0; i < widget.controller.positions.length; i++)
            sizedWidget = Expanded(
              key: GlobalKey(),
              child: Padding(
                padding: const EdgeInsets.all(2.0),
                child: dragTarget(i),
              ),
            ),
          addNewGroup(),
        ],
      ),
    );
  }

  Widget addNewGroup() {
    return Padding(
      padding: const EdgeInsets.all(2.0),
      child: SizedBox(
        width: isHor ? 160 : null,
        height: isHor ? null : 87,
        child: DragTarget<ContributorData>(
          onAccept: (data) {
            handlePosition(data, widget.controller.positions.length);
          },
          builder: (context, candidateData, rejectedData) {
            return Container(
              decoration: BoxDecoration(
                color: MColors.gray6,
                borderRadius: BorderRadius.circular(8.0),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24.0),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.add_outlined, size: 32.0, color: MColors.gray1),
                      Text("New group", style: TSMedium.bold.g1),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  DragTarget<ContributorData> dragTarget(int i) {
    return DragTarget<ContributorData>(
      onAccept: (data) {
        handlePosition(data, i);
      },
      builder: (context, candidateData, rejectedData) {
        return Container(
          decoration: BoxDecoration(
            color: MColors.gray6,
            borderRadius: BorderRadius.circular(8.0),
          ),
          child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: isHor
                  ? Column(
                      mainAxisAlignment: MainAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        for (var j = 0; j < widget.controller.positions[i]!.length; j++) contributor(i, j),
                        const Spacer(),
                      ],
                    )
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.start,
                      children: [
                        for (var j = 0; j < widget.controller.positions[i]!.length; j++) contributor(i, j),
                        const Spacer(),
                      ],
                    )),
        );
      },
    );
  }

  Padding contributor(int i, int j) {
    return Padding(
      padding: EdgeInsets.only(bottom: isHor ? 8.0 : 0.0, right: isHor ? 0.0 : 8.0),
      child: Draggable<ContributorData>(
        data: widget.controller.positions[i]![j],
        feedback: SizedBox(
          width: isHor ? sizedWidgetWidth : 220,
          height: isHor ? null : 87 - 16,
          child: Material(
            color: Colors.transparent,
            child: MContributor(contributorData: widget.controller.positions[i]![j], positionIndex: i, makePrimary: null),
          ),
        ),
        childWhenDragging: Opacity(
          opacity: 0.5,
          child: SizedBox(
            width: isHor ? sizedWidgetWidth : 220,
            child: MContributor(contributorData: widget.controller.positions[i]![j], positionIndex: i, makePrimary: null),
          ),
        ),
        child: SizedBox(
          width: isHor ? null : 220,
          child: MContributor(contributorData: widget.controller.positions[i]![j], positionIndex: i, makePrimary: makePrimary),
        ),
      ),
    );
  }

  void handlePosition(ContributorData data, int newPosition) {
    setState(() {
      int? shiftedIndex;
      var positions = widget.controller.positions;

      // Remove from previous position
      for (var j = 0; j < positions.length; j++) {
        if (positions[j]!.contains(data)) {
          positions[j]!.remove(data);
          if (positions[j]!.isEmpty) {
            // Shift all positions down
            for (var k = j; k < positions.length - 1; k++) {
              positions[k] = positions[k + 1]!;
            }
            // Remove last position
            positions.remove(positions.length - 1);
            shiftedIndex = j;
          } else {
            // Ensure primary contributor in case it was just removed
            positions[j]![0].isPrimary = true;
          }
          break;
        }
      }
      if (shiftedIndex != null && newPosition > shiftedIndex) {
        // Account for shifting
        newPosition--;
      }
      if (newPosition >= positions.length) {
        // Add to end and make primary
        positions[positions.length] = [data..isPrimary = true];
      } else {
        // Add to new position and remove primary status (since the group already has a primary contributor)
        positions[newPosition]!.add(data..isPrimary = false);
      }
    });
  }

  void makePrimary(ContributorData data, int incomingPosition) {
    setState(() {
      if (data.isPrimary) {
        return;
      }
      for (var k = 0; k < widget.controller.positions[incomingPosition]!.length; k++) {
        widget.controller.positions[incomingPosition]![k].isPrimary = false;
      }
      data.isPrimary = true;
    });
  }
}

class ContributorData {
  final Contributor contributor;
  bool isPrimary = false;

  ContributorData(this.contributor, this.isPrimary);
}
