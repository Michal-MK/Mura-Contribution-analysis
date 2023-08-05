import 'package:flutter/material.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MuraConfiguration extends ChangeNotifier {
  late SharedPreferences preferences;

  static const String lightTheme = "light";
  static const String darkTheme = "dark";

  Future init() async {
    preferences = await SharedPreferences.getInstance();
    if (theme == darkTheme) {
      DarkTheme().apply();
    } else {
      LightTheme().apply();
    }
    notifyListeners();
  }

  String get muraPath => preferences.getString("muraPath") ?? "";
  set muraPath(String value) => preferences.setString("muraPath", value);

  String get pyPath => preferences.getString("pyPath") ?? "";
  set pyPath(String value) => preferences.setString("pyPath", value);

  String get theme => preferences.getString("theme") ?? lightTheme;
  set theme(String value) {
    preferences.setString("theme", value);
    if (theme == darkTheme) {
      DarkTheme().apply();
    } else {
      LightTheme().apply();
    }
    notifyListeners();
  }
}
