import 'package:flutter/material.dart';
import 'package:fluent_ui/fluent_ui.dart' as fluent_ui;
import 'package:flutter_ui/business/formatters/decimal_input_formatter.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/views/configuration/host_page.dart';

class WeightInputEntry extends StatelessWidget {
  final String title;
  final String description;
  final TextEditingController controller;
  final bool allowNegative;

  const WeightInputEntry({
    required this.title,
    required this.description,
    required this.controller,
    this.allowNegative = false,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: ConfigurationHostPage.ENTRY_PADDING),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 8,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(title, style: TSLarge.muni.primary),
                Text(description, style: TSMedium.italic.primary),
              ],
            ),
          ),
          const SizedBox(width: 16.0),
          Expanded(
            flex: 2,
            child: fluent_ui.TextBox(
              controller: controller,
              textAlign: TextAlign.end,
              onTap: () {
                controller.selection = TextSelection(baseOffset: 0, extentOffset: controller.text.length);
              },
              inputFormatters: [
                DecimalNumberFormatter(allowSign: allowNegative),
              ],
            ),
          ),
        ],
      ),
    );
  }
}