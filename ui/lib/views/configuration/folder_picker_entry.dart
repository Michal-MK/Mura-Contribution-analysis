import 'package:file_picker/file_picker.dart';
import 'package:fluent_ui/fluent_ui.dart';
import 'package:flutter/material.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/views/configuration/host_page.dart';

class FolderPickerEntry extends StatefulWidget {
  final TextEditingController controller;
  final bool Function() visibleCondition;
  final String placeholder;
  final String? description;
  final void Function(String?)? onSelected;

  const FolderPickerEntry({
    required this.controller,
    required this.placeholder,
    required this.visibleCondition,
    this.onSelected,
    this.description,
    super.key,  
  });

  @override
  State<FolderPickerEntry> createState() => _FolderPickerEntryState();
}

class _FolderPickerEntryState extends State<FolderPickerEntry> {

  @override
  void initState() {
    super.initState();
  }

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
          Row(
            children: [
              Expanded(
                child: TextBox(
                  placeholder: widget.placeholder,
                  controller: widget.controller,
                  onEditingComplete: () {
                    widget.onSelected?.call(widget.controller.text);
                  },
                ),
              ),
              const SizedBox(width: 16.0),
              ElevatedButton(
                child: Text('Browse'),
                onPressed: () {
                  FilePicker.platform.getDirectoryPath().then((value) {
                    setState(() {
                      widget.controller.text = value ?? '';
                      widget.onSelected?.call(widget.controller.text);
                    });
                  });
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}
