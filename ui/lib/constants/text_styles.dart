import 'package:flutter/painting.dart';
import 'package:flutter_ui/constants/colors.dart';

class TSXXL {
  static const TextStyle std = TextStyle(
    fontWeight: FontWeight.w300,
    fontSize: 32,
  );
  static const TextStyle bold = TextStyle(
    fontWeight: FontWeight.w500,
    fontSize: 32,
  );
  static const TextStyle muni = TextStyle(
    fontWeight: FontWeight.bold,
    fontFamily: "MUNI",
    fontSize: 32,
  );
}

class TSExtraLarge {
  static const TextStyle std = TextStyle(
    fontWeight: FontWeight.w300,
    fontSize: 24,
  );
  static const TextStyle bold = TextStyle(
    fontWeight: FontWeight.w500,
    fontSize: 24,
  );
  static const TextStyle muni = TextStyle(
    fontWeight: FontWeight.bold,
    fontFamily: "MUNI",
    fontSize: 24,
  );
}

class TSLarge {
  static const TextStyle std = TextStyle(
    fontWeight: FontWeight.w300,
    fontSize: 20,
  );
  static const TextStyle bold = TextStyle(
    fontWeight: FontWeight.w500,
    fontSize: 20,
  );
  static const TextStyle muni = TextStyle(
    fontWeight: FontWeight.bold,
    fontFamily: "MUNI",
    fontSize: 20,
  );
}

class TS18 {
  static const TextStyle std = TextStyle(
    fontWeight: FontWeight.w300,
    fontSize: 18,
  );
  static const TextStyle bold = TextStyle(
    fontWeight: FontWeight.w500,
    fontSize: 18,
  );
}

class TSMedium {
  static const TextStyle std = TextStyle(
    fontWeight: FontWeight.w300,
    fontSize: 16,
  );
  static const TextStyle bold = TextStyle(
    fontWeight: FontWeight.w500,
    fontSize: 16,
  );
  static const TextStyle italic = TextStyle(
    fontWeight: FontWeight.w300,
    fontStyle: FontStyle.italic,
    fontSize: 16,
  );
  static const TextStyle muni = TextStyle(
    fontWeight: FontWeight.w300,
    fontFamily: "MUNI",
    fontSize: 16,
  );
}

class TSSmall {
  static const TextStyle bold = TextStyle(
    fontWeight: FontWeight.w500,
    fontSize: 14,
  );

  static const TextStyle std = TextStyle(
    fontWeight: FontWeight.w300,
    fontSize: 14,
  );
}

class TSExtraSmall {
  static const TextStyle std = TextStyle(
    fontWeight: FontWeight.w300,
    fontSize: 12,
  );

  static const TextStyle bold = TextStyle(
    fontWeight: FontWeight.w500,
    fontSize: 12,
  );
}

extension TS on TextStyle {
  TextStyle get primary => copyWith(
        color: MColors.primary,
      );

  TextStyle get highlight => copyWith(
        color: MColors.highlight,
      );

  TextStyle get entry => copyWith(
        color: MColors.entryLeadingTextColor,
      );

  TextStyle get g4 => copyWith(
        color: MColors.gray7,
      );

  TextStyle get g3 => copyWith(
        color: MColors.gray6,
      );

  TextStyle get g2 => copyWith(
        color: MColors.gray5,
      );

  TextStyle get g1 => copyWith(
        color: MColors.gray1,
      );
}
