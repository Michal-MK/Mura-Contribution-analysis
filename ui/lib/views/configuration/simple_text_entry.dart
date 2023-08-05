import 'package:fluent_ui/fluent_ui.dart';
import 'package:flutter/services.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/views/configuration/host_page.dart';

class SimpleTextEntry extends StatefulWidget {
  final String placeholder;
  final String? description;
  final TextEditingController controller;
  final bool Function() visibleCondition;
  final bool numbersOnly;

  const SimpleTextEntry({
    required this.placeholder,
    this.description,
    required this.controller,
    required this.visibleCondition,
    this.numbersOnly = false,
    super.key,
  });

  @override
  State<SimpleTextEntry> createState() => _SimpleTextEntryState();
}

class _SimpleTextEntryState extends State<SimpleTextEntry> {
  @override
  Widget build(BuildContext context) {
    if (!widget.visibleCondition()) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: ConfigurationHostPage.ENTRY_PADDING),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(widget.placeholder, style: TSLarge.muni.entry),
          if (widget.description != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Text(widget.description!, style: TSMedium.italic.entry),
            ),
          TextBox(
            placeholder: widget.placeholder,
            inputFormatters: [
              if (widget.numbersOnly) FilteringTextInputFormatter.digitsOnly,
            ],
            controller: widget.controller,
          ),
        ],
      ),
    );
  }
}
