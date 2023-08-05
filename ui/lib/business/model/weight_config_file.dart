import 'dart:io';

import 'package:path/path.dart' as p;

abstract class ConfigFile {
  String path;
  bool loaded = false;

  String title;
  String description;

  ConfigFile({
    required this.path,
    required this.title,
    this.description = "",
  });

  Future save();

  Future<ConfigFile> load();
}

class WeightConfigFile extends ConfigFile {
  Compound? root;

  WeightConfigFile({
    required String filePath,
  }) : super(
          path: filePath,
          title: "Weight Configuration",
          description: "This configuration file contains the weights for the different components of the MURA algorithm.",
        );

  @override
  Future save() async {}

  @override
  Future<WeightConfigFile> load() async {
    String content = await File.fromUri(p.toUri(path)).readAsString();
    root = parseRoot(content);
    loaded = root != null;
    return this;
  }

  Compound? parseRoot(String content) {
    var lines = content.split("\r\n");
    int index = 0;

    String currentTitle = "";
    String propName = "";
    String value;
    Compound root = Compound("Root", "");
    bool valueAdded = false;

    for (index; index < lines.length; index++) {
      var line = lines[index];
      if (line.isEmpty) {
        currentTitle = "";
        valueAdded = false;
        continue;
      }

      if (line.startsWith("#")) {
        if (valueAdded) {
          valueAdded = false;
          currentTitle = "";
        }
        currentTitle += line + "\n";
      } else {
        var split = line.split("=");
        propName = split[0];
        value = split[1];
        root.components.add(Component(title: currentTitle.trim(), description: propName, value: double.parse(value.trim().replaceAll("_", ""))));
        valueAdded = true;
      }
    }
    return root;
  }
}

class Compound extends Component {
  List<Component> components = [];

  Compound(
    String title,
    String description,
  ) : super(
          title: title,
          description: description,
        );
}

class Component {
  String title;
  String description;
  double value;

  Component({
    required this.title,
    required this.description,
    this.value = 0,
  });
}

class RuleConfigFile extends ConfigFile {

  List<RuleDef> rules = [];

  RuleConfigFile({
    required String filePath,
  }) : super(
          path: filePath,
          title: "Rule Configuration",
        );

  @override
  Future save() async {}

  @override
  Future<RuleConfigFile> load() async {
    String content = await File.fromUri(p.toUri(path)).readAsString();
    rules = parseRules(content);
    description = rules.last.title;
    loaded = rules.isNotEmpty;
    return this;
  }

  List<RuleDef> parseRules(String content) {
    var lines = content.split("\r\n");
    int index = 0;

    String currentTitle = "";
    String rawText = "";
    List<RuleDef> rules = [];

    for (index; index < lines.length; index++) {
      var line = lines[index];
      if (line.isEmpty) {
        currentTitle = "";
        rawText = "";
        continue;
      }

      if (line.startsWith("#")) {
        currentTitle += line + "\n";
        rawText = "";
      } else {
        rawText += line + "\n";
        rules.add(RuleDef(title: currentTitle.trim(), rawText: rawText.trim()));
      }
    }
    return rules;
  }
}

class RuleDef {
  String rawText;
  String title;

  RuleDef({
    required this.rawText,
    required this.title,
  });
}