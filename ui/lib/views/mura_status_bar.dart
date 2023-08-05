import 'package:flutter/material.dart';
import 'package:flutter_ui/constants/colors.dart';

class MuraStatusBar extends StatelessWidget {
  const MuraStatusBar({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: MColors.gray7,
        border: Border(
          top: BorderSide(
            color: MColors.shadowColor,
            width: 1,
          ),
        ),
      ),
    );
  }
}
