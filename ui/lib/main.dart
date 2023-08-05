import 'package:fluent_ui/fluent_ui.dart' show AccentColor, FluentTheme, FluentThemeData;
import 'package:flutter/material.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/business/state/analysis_state.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/views/home.dart';
import 'package:provider/provider.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (context) => AnalysisController()),
        ChangeNotifierProvider(create: (context) => MuraConfiguration()..init()),
      ],
      child: FluentTheme(
        data: FluentThemeData(
          accentColor: AccentColor.swatch({"normal" : MColors.primary})
        ),
        child: MaterialApp(
          title: 'MURA',
          theme: ThemeData(
            colorScheme: ColorScheme.fromSeed(seedColor: MColors.primary),
            switchTheme: SwitchThemeData(
              thumbColor: MaterialStateProperty.resolveWith((state) => state.contains(MaterialState.selected) ? MColors.primary : MColors.textDark),
              trackColor: MaterialStateProperty.all(MColors.primary.withOpacity(0.33)),
            )
          ),
          home: const MuraHome(title: 'MURA Home Page'),
        ),
      ),
    );
  }
}
