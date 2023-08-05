import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/views/configuration/folder_picker_entry.dart';
import 'package:provider/provider.dart';
import 'package:path/path.dart' as p;

class MuraConfigurationPage extends StatefulWidget {
  const MuraConfigurationPage({super.key});

  @override
  State<MuraConfigurationPage> createState() => _MuraConfigurationPageState();
}

class _MuraConfigurationPageState extends State<MuraConfigurationPage> {
  TextEditingController muraPathController = TextEditingController();
  TextEditingController pyPathController = TextEditingController();

  @override
  void didChangeDependencies() {
    var muraConfig = context.read<MuraConfiguration>();

    muraPathController.text = muraConfig.muraPath;
    pyPathController.text = muraConfig.pyPath;
    
    super.didChangeDependencies();
  }

  @override
  Widget build(BuildContext context) {
    var muraConfig = context.watch<MuraConfiguration>();

    return Scaffold(
      backgroundColor: MColors.background,
      body: Stack(
        children: [
          Positioned.fill(
            child: ListView(
              padding: const EdgeInsets.all(16.0),
              children: [
                FolderPickerEntry(
                  controller: muraPathController,
                  placeholder: "MURA Base path",
                  description: "Path to the Python analyzer",
                  visibleCondition: () => true,
                  onSelected: (path) async {
                    muraConfig.muraPath = path ?? "";
                    if (path != null) {
                      if (await Directory(path).exists()) {
                        String muraDir = p.join(path, "venv", (Platform.isWindows ? "Scripts" : "bin"));
                        if (await Directory(muraDir).exists()) {
                          setState(() {
                            pyPathController.text = p.join(muraDir, Platform.isWindows ? "python.exe" : "python");
                            muraConfig.pyPath = pyPathController.text;
                          });
                        }
                      }
                    }
                  },
                ),
                FolderPickerEntry(
                  controller: pyPathController,
                  placeholder: "Interpreter path",
                  description: "Path to the Python interpreter used by MURA",
                  visibleCondition: () => true,
                  onSelected: (path) {
                    muraConfig.pyPath = path ?? "";
                  },
                ),
                ElevatedButton.icon(
                  onPressed: () {
                    var muraState = context.read<MuraConfiguration>();
                    muraState.theme = muraState.theme == MuraConfiguration.lightTheme //
                        ? MuraConfiguration.darkTheme
                        : MuraConfiguration.lightTheme;
                  },
                  icon: Icon(
                    context.read<MuraConfiguration>().theme == MuraConfiguration.darkTheme //
                        ? Icons.sunny
                        : Icons.nightlight_round,
                  ),
                  label: const Text("Theme", style: TSMedium.std),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
