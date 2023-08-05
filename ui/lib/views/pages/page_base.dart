import 'package:flutter/material.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/text_styles.dart';

class PageBase extends StatelessWidget {
  
  final Widget child;
  final String title;
  
  const PageBase({
    required this.child,
    this.title = "",
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: MColors.background,
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 16.0),
              child: Text(title, style: TSExtraLarge.muni.primary),
            ),
            Expanded(child: child),
          ],
        ),
      ),
    );
  }
}
