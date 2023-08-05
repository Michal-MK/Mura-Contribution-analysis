import 'package:flutter/material.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/views/home_content.dart';
import 'package:flutter_ui/views/mura_status_bar.dart';
import 'package:flutter_ui/views/side_menu_panel.dart';
import 'package:provider/provider.dart';

class MuraHome extends StatefulWidget {
  const MuraHome({super.key, required this.title});
  final String title;
  static const double collapsedWidth = 72;

  @override
  State<MuraHome> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MuraHome> with SingleTickerProviderStateMixin {
  late final TabController tabController = TabController(length: 17, vsync: this);

  static const expandedThreshold = 800;
  Size mediaQuery = const Size(0, 0);
  bool get isExpanded => mediaQuery.width > expandedThreshold;

  @override
  void didChangeDependencies() {
    mediaQuery = MediaQuery.sizeOf(context);
    setState(() {
      
    });
    super.didChangeDependencies();
  }

  @override
  Widget build(BuildContext context) {
    var _ = context.watch<MuraConfiguration>();

    return Scaffold(
      body: Consumer<MuraConfiguration>(
        builder: (ctx, muraConfig, _) {
          return Stack(
            children: [
              Positioned(
                left: isExpanded ? 360 : MuraHome.collapsedWidth,
                right: 0,
                top: 0,
                bottom: 24,
                child: HomeContent(
                  tabController: tabController,
                ),
              ),
              Positioned(
                bottom: 0,
                left: isExpanded ? 360 : MuraHome.collapsedWidth,
                right: 0,
                height: 24,
                child: MuraStatusBar(),
              ),
              Positioned(
                left: 0,
                width: isExpanded ? 360 : MuraHome.collapsedWidth,
                top: 0,
                bottom: 0,
                child: SideMenuPanel(
                  tabController: tabController,
                  isExpanded: isExpanded,
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
