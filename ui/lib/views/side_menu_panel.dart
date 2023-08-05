import 'package:flutter/material.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/icons.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:provider/provider.dart';

class SideMenuPanel extends StatefulWidget {
  final TabController tabController;
  final bool isExpanded;

  const SideMenuPanel({
    required this.tabController,
    required this.isExpanded,
    super.key,
  });

  @override
  State<SideMenuPanel> createState() => _SideMenuPanelState();
}

class _SideMenuPanelState extends State<SideMenuPanel> {
  int selectedTabIndex = 0;

  void onPressed(int tabIndex) {
    setState(() {
      widget.tabController.animateTo(tabIndex);
      selectedTabIndex = tabIndex;
    });
  }

  @override
  Widget build(BuildContext context) {
    var _ = context.watch<MuraConfiguration>();

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [MColors.highlight, widget.isExpanded ? MColors.sideMenuDrawerNeutralColor : MColors.highlight],
          stops: const [0.5, 1.0],
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
        ),
        boxShadow: [
          BoxShadow(
            color: MColors.shadowColor,
            blurRadius: 6,
          ),
        ],
      ),
      child: SingleChildScrollView(
        child: Column(
          children: [
            const SizedBox(
              height: 8,
            ),
            SizedBox(
              height: 32,
              child: Text("MURA", style: widget.isExpanded ? TSXXL.muni.primary : TSMedium.muni.primary),
            ),
            ListTile(
              title: Text(
                "Setup",
                textAlign: widget.isExpanded ? TextAlign.left : TextAlign.center,
                style: widget.isExpanded ? TSLarge.bold.primary : TSExtraSmall.bold.primary,
              ),
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.info,
              title: "About",
              tabIndex: 0,
              isSelected: selectedTabIndex == 0,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.settings,
              title: "Configuration",
              tabIndex: 1,
              isSelected: selectedTabIndex == 1,
              showSeparator: false,
              isExpanded: widget.isExpanded,
            ),
            const SizedBox(
              height: 16,
            ),
            ListTile(
              title: Text(
                "Results",
                style: widget.isExpanded ? TSLarge.bold.primary : TSExtraSmall.bold.primary,
                textAlign: widget.isExpanded ? TextAlign.left : TextAlign.center,
              ),
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.contributor,
              title: "Contributors",
              tabIndex: 2,
              isSelected: selectedTabIndex == 2,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.commit,
              title: "Commits",
              tabIndex: 3,
              isSelected: selectedTabIndex == 3,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.fileStats,
              title: "File statistics",
              tabIndex: 4,
              isSelected: selectedTabIndex == 4,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.percentage,
              title: "File ownership (Percentage)",
              tabIndex: 5,
              isSelected: selectedTabIndex == 5,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.dirTree,
              title: "File ownership dir-tree",
              tabIndex: 6,
              isSelected: selectedTabIndex == 6,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.file,
              title: "Line distribution",
              tabIndex: 7,
              isSelected: selectedTabIndex == 7,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.crossroad,
              title: "Unmerged commits",
              tabIndex: 8,
              isSelected: selectedTabIndex == 8,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.cube,
              title: "Syntax + Semantics (SonarQube)",
              tabIndex: 9,
              isSelected: selectedTabIndex == 9,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.syntax,
              title: "Local Syntax",
              tabIndex: 10,
              isSelected: selectedTabIndex == 10,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.semantics,
              title: "Local Semantics",
              tabIndex: 11,
              isSelected: selectedTabIndex == 11,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.lines,
              title: "Constructs",
              tabIndex: 12,
              isSelected: selectedTabIndex == 12,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.time,
              title: "Hours",
              tabIndex: 13,
              isSelected: selectedTabIndex == 13,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.remoteRepo,
              title: "Remote Repository",
              tabIndex: 14,
              isSelected: selectedTabIndex == 14,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.violatedRules,
              title: "Rules",
              tabIndex: 15,
              isSelected: selectedTabIndex == 15,
              isExpanded: widget.isExpanded,
            ),
            MuraMenuTile(
              onPressed: onPressed,
              icon: MIcons.percent,
              title: "Summary",
              tabIndex: 16,
              isSelected: selectedTabIndex == 16,
              isExpanded: widget.isExpanded,
              showSeparator: false,
            ),
            const SizedBox(
              height: 32,
            ),
          ],
        ),
      ),
    );
  }
}

class MuraMenuTile extends StatelessWidget {
  const MuraMenuTile({
    required this.icon,
    required this.title,
    required this.tabIndex,
    required this.isSelected,
    this.showSeparator = true,
    required this.onPressed,
    this.isExpanded = true,
    super.key,
  });

  final String icon;
  final String title;
  final int tabIndex;
  final bool isSelected;
  final bool showSeparator;
  final void Function(int) onPressed;
  final bool isExpanded;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        MenuItemButton(
          leadingIcon: Row(
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                width: isSelected
                    ? isExpanded
                        ? 6
                        : 2
                    : 0,
                height: 24,
                margin: const EdgeInsets.only(right: 8),
                decoration: BoxDecoration(
                  color: MColors.primary,
                  borderRadius: const BorderRadius.all(Radius.circular(4)),
                ),
              ),
              Text(
                icon,
                style: isExpanded ? null : TSExtraLarge.bold.primary.copyWith(fontSize: 27.0),
                textAlign: TextAlign.center,
              ),
            ],
          ),
          child: Text(
            isExpanded ? title : "",
            style: TSMedium.bold.primary,
          ),
          onPressed: () => onPressed(tabIndex),
        ),
        if (showSeparator)
          Container(
            height: 1,
            color: MColors.gray5,
            margin: EdgeInsets.only(right: 16.0, left: isExpanded ? 42.0 : 16.0),
          )
      ],
    );
  }
}
