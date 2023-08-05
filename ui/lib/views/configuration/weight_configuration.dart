import 'package:flutter/material.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/business/model/weight_config_file.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/ui/settings_group.dart';
import 'package:flutter_ui/views/configuration/weight_input_entry.dart';
import 'package:provider/provider.dart';
import 'package:path/path.dart' as p;

class WeightConfigurationPage extends StatefulWidget {
  const WeightConfigurationPage({super.key});

  @override
  State<WeightConfigurationPage> createState() => _WeightConfigurationPageState();
}

class _WeightConfigurationPageState extends State<WeightConfigurationPage> {
  TextEditingController weightController = TextEditingController();

  late Future<List<ConfigFile>> configFiles;

  @override
  void didChangeDependencies() {
    configFiles = fetchConfigurationFiles(context.read<MuraConfiguration>().muraPath);
    super.didChangeDependencies();
  }

  Future<List<ConfigFile>> fetchConfigurationFiles(String muraPath) async {
    String baseConfigPath = p.join(muraPath, "configuration_data", "configuration.txt");
    String semanticWeightsPath = p.join(muraPath, "lang-semantics", "semantic_weights");
    String rulesPath = p.join(muraPath, "configuration_data", "rules.txt");

    List<ConfigFile> ret = [];

    try {
      for (var configFile in [
        WeightConfigFile(filePath: baseConfigPath),
        WeightConfigFile(filePath: semanticWeightsPath),
        RuleConfigFile(filePath: rulesPath),
      ]) {
        ret.add(await configFile.load());
      }
    } catch (e) {
      print(e);
    }

    return ret;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: MColors.background,
      body: Padding(
        padding: const EdgeInsets.only(left: 16.0),
        child: FutureBuilder(
          future: configFiles,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.done) {
              return SingleChildScrollView(
                child: Padding(
                  padding: const EdgeInsets.only(right: 16.0),
                  child: Column(
                    children: [
                      const SizedBox(height: 16.0),
                      for (int j = 0; j < snapshot.data!.length; j++)
                        SettingsGroup(
                          title: snapshot.data![j].title,
                          description: snapshot.data![j].description,
                          visibleCondition: () => true,
                          children: buildChildren(snapshot.data![j]),
                        ),
                      const SizedBox(height: 16.0),
                    ],
                  ),
                ),
              );
            }
            return const Center(child: CircularProgressIndicator.adaptive());
          },
        ),
      ),
    );
  }

  List<Widget> buildChildren(ConfigFile configFile) {
    List<Widget> children = [];
    if (configFile is WeightConfigFile) {
      for (int i = 0; i < configFile.root!.components.length; i++) {
        children.add(
          WeightInputEntry(
            title: configFile.root!.components[i].description,
            description: configFile.root!.components[i].title.split('\n').map((e) => e.replaceFirst("# ", "")).join('\n'),
            controller: TextEditingController(
              text: configFile.root!.components[i].value.toString(),
            ),
          ),
        );
      }
    }
    if (configFile is RuleConfigFile) {
      for (int i = 0; i < configFile.rules.length; i++) {
        children.add(Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(configFile.rules[i].rawText),
          ],
        ));
      }
    }
    return children;
  }
}
