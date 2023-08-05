import 'package:flutter/material.dart';
import 'package:flutter_ui/business/configuration/mura_configuration.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:flutter_ui/constants/text_styles.dart';
import 'package:flutter_ui/views/configuration/host_page.dart';
import 'package:provider/provider.dart';

class SettingsGroup extends StatefulWidget {
  final String title;
  final String? description;
  final bool Function() visibleCondition;
  final List<Widget> children;

  const SettingsGroup({
    required this.title,
    this.description,
    required this.visibleCondition,
    required this.children,
    super.key,
  });

  @override
  State<SettingsGroup> createState() => _SettingsGroupState();
}

class _SettingsGroupState extends State<SettingsGroup> {
  bool isExpanded = false;

  @override
  Widget build(BuildContext context) {
    var _ = context.read<MuraConfiguration>();

    if (!widget.visibleCondition()) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: ConfigurationHostPage.ENTRY_PADDING),
      child: Container(
        decoration: BoxDecoration(
          color: MColors.gray5,
          borderRadius: BorderRadius.all(const Radius.circular(8.0)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(8.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4.0),
                          child: Text(
                            widget.title,
                            style: TSExtraLarge.muni.entry,
                          ),
                        ),
                        if (widget.description != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8.0),
                            child: Text(
                              widget.description!,
                              style: TSMedium.italic.entry,
                            ),
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () {
                      setState(() {
                        isExpanded ^= true;
                      });
                    },
                    icon: Icon(isExpanded ? Icons.arrow_downward : Icons.arrow_upward),
                  ),
                  SizedBox(width: 16),
                ],
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8.0),
                child: Column(
                  children: isExpanded ? widget.children : [],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
