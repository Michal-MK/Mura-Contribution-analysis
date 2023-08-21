import 'package:flutter/material.dart';
import 'package:flutter_ui/business/state/analysis_state.dart';
import 'package:flutter_ui/ui/vertical_tabbarview.dart';
import 'package:flutter_ui/views/configuration/host_page.dart';
import 'package:flutter_ui/views/pages/about_page.dart';
import 'package:flutter_ui/views/pages/commits_page.dart';
import 'package:flutter_ui/views/pages/text_dump_page.dart';
import 'package:provider/provider.dart';

final PageStorageBucket bucket = PageStorageBucket();

class HomeContent extends StatefulWidget {
  final TabController tabController;

  const HomeContent({
    required this.tabController,
    super.key,
  });

  @override
  State<HomeContent> createState() => _HomeContentState();
}

class _HomeContentState extends State<HomeContent> {
  @override
  Widget build(BuildContext context) {
    return Consumer<AnalysisController>(
      builder: (context, value, child) {
        return PageStorage(
          bucket: bucket,
          child: ChangeNotifierProvider.value(
            value: widget.tabController,
            child: VerticalTabBarView(
              controller: widget.tabController,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                const AboutPage(),
                const ConfigurationHostPage(),
                for (int i = 0; i < 15; i++)
                  if(i == 1) ...[
                    CommitsPage(content: value.sections.elementAtOrNull(i))
                  ] else ...[
                    TextDumpPage(
                      content: value.sections.elementAtOrNull(i),
                    ),
                  ]
              ],
            ),
          ),
        );
      },
    );
  }
}