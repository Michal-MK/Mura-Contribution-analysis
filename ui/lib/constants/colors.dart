import 'dart:ui';

class MColors {
  static Color primary = Color(0xff0000dc);
  static Color highlight = Color(0xfff2d45c);
  static Color gray1 = Color(0xff000000);
  static Color gray3 = Color(0xff444444);
  static Color gray5 = Color(0xffaaaaaa);
  static Color gray6 = Color(0xffdcdcdc);
  static Color gray7 = Color(0xfffafafa);
  static Color textLight = Color(0xffffffff);
  static Color textDark = Color(0xff000000);

  static Color background = gray7;
  static Color shadowColor = gray1;

  static Color sideMenuDrawerNeutralColor = gray5;
  static Color entryLeadingTextColor = primary;
  static Color tabBarSelectedLabelColor = primary;
}

class LightTheme {
  static const Color primary = Color(0xff0000dc);
  static const Color highlight = Color(0xfff2d45c);
  static const Color gray1 = Color(0xff000000);
  static const Color gray3 = Color(0xff444444);
  static const Color gray5 = Color(0xffaaaaaa);
  static const Color gray6 = Color(0xffdcdcdc);
  static const Color gray7 = Color(0xfffafafa);
  static const Color textLight = Color(0xffffffff);
  static const Color textDark = Color(0xff000000);

  void apply() {
    MColors.primary = primary;
    MColors.highlight = highlight;
    MColors.gray1 = gray1;
    MColors.gray3 = gray3;
    MColors.gray5 = gray5;
    MColors.gray6 = gray6;
    MColors.gray7 = gray7;
    MColors.textLight = textLight;
    MColors.textDark = textDark;

    MColors.background = gray7;
    MColors.shadowColor = gray1;

    MColors.sideMenuDrawerNeutralColor = gray5;
    MColors.entryLeadingTextColor = primary;
    MColors.tabBarSelectedLabelColor = primary;
  }
}

class DarkTheme {
  static const Color primary = Color(0xff0000dc);
  static const Color highlight = Color(0xfff2d45c);
  static const Color gray1 = Color(0xfffafafa);
  static const Color gray3 = Color(0xffdcdcdc);
  static const Color gray5 = Color(0xffaaaaaa);
  static const Color gray6 = Color(0xff444444);
  static const Color gray7 = Color(0xff000000);
  static const Color textLight = Color(0xff000000);
  static const Color textDark = Color(0xffffffff);

  void apply() {
    MColors.primary = primary;
    MColors.highlight = highlight;
    MColors.gray1 = gray1;
    MColors.gray3 = gray3;
    MColors.gray5 = gray5;
    MColors.gray6 = gray6;
    MColors.gray7 = gray7;
    MColors.textLight = textLight;
    MColors.textDark = textDark;

    MColors.background = gray6;
    MColors.shadowColor = gray7;

    MColors.sideMenuDrawerNeutralColor = gray6;
    MColors.entryLeadingTextColor = textDark;
    MColors.tabBarSelectedLabelColor = highlight;
  }
}