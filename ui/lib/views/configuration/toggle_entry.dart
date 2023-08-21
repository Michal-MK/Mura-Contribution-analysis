import 'package:fluent_ui/fluent_ui.dart' show ToggleSwitch;
import 'package:flutter/material.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/views/configuration/host_page.dart';

class ToggleEntry extends StatefulWidget {
  final String title;
  final String? description;
  final bool Function() valueGetter;
  final void Function(bool) valueSetter;
  final bool Function() visibleCondition;

  const ToggleEntry({
    required this.title,
    this.description,
    required this.valueGetter,
    required this.valueSetter,
    required this.visibleCondition,
    super.key,
  });

  @override
  State<ToggleEntry> createState() => _ToggleEntryState();
}

class _ToggleEntryState extends State<ToggleEntry> {
  @override
  Widget build(BuildContext context) {
    if (!widget.visibleCondition()) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: ConfigurationHostPage.ENTRY_PADDING),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 4),
        onTap: () {
          setState(() {
            widget.valueSetter(!widget.valueGetter());
          });
        },
        title: Text(
          widget.title,
          style: TSLarge.muni.entry,
        ),
        subtitle: Text(
          widget.description ?? '',
          style: TSMedium.italic.entry,
        ),
        trailing: SizedBox(
          width: 60,
          height: 36,
          child: ToggleSwitch(
            thumb: Padding(
              padding: const EdgeInsets.all(4.0),
              child: Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  color: widget.valueGetter() ? MColors.highlight : MColors.textDark,
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            checked: widget.valueGetter(),
            onChanged: (value) {
              setState(() {
                widget.valueSetter(value);
              });
            },
          ),
        ),
      ),
    );
  }
}
