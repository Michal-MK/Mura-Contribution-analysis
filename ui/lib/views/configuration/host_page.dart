import 'package:flutter/material.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/views/configuration/analysis_configuration.dart';
import 'package:flutter_ui/views/configuration/mura_configuration.dart';
import 'package:flutter_ui/views/configuration/weight_configuration.dart';
import 'package:provider/provider.dart';

class ConfigurationHostPage extends StatefulWidget {
  static const double ENTRY_PADDING = 24.0;

  const ConfigurationHostPage({super.key});

  @override
  State<ConfigurationHostPage> createState() => _ConfigurationHostPageState();
}

class _ConfigurationHostPageState extends State<ConfigurationHostPage> with SingleTickerProviderStateMixin {
  late final TabController configurationTabController = TabController(length: 3, vsync: this);

  @override
  Widget build(BuildContext context) {
    var _ = context.watch<MuraConfiguration>();

    return Column(
      children: [
        Material(
          color: MColors.gray6,
          child: TabBar(
            controller: configurationTabController,
            labelColor: MColors.tabBarSelectedLabelColor,
            unselectedLabelColor: MColors.gray1,
            indicatorColor: MColors.highlight,
            tabs: [
              Tab(
                text: "Analysis configuration",
              ),
              Tab(
                text: "Mura configuration",
              ),
              Tab(
                text: "Weight configuration",
              ),
            ],
          ),
        ),
        Container(height: 2, color: MColors.primary),
        Expanded(
          child: TabBarView(
            controller: configurationTabController,
            physics: NeverScrollableScrollPhysics(),
            children: const [
              AnalysisConfigurationPage(),
              MuraConfigurationPage(),
              WeightConfigurationPage(),
            ],
          ),
        ),
      ],
    );
  }
}
