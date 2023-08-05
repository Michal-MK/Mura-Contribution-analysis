import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_ui/constants/colors.dart';
import 'package:url_launcher/url_launcher.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: MColors.background,
      child: Markdown(
        onTapLink: (text, href, title) => launchUrl(Uri.parse(href!)),
        styleSheet: MarkdownStyleSheet(
          a: TextStyle(
            color: MColors.primary,
          ),
          p: TextStyle(
            color: MColors.gray1,
          ),
          h1: TextStyle(
            color: MColors.gray1,
          ),
          h2: TextStyle(
            color: MColors.gray1,
          ),
          h3: TextStyle(
            color: MColors.gray1,
          ),
          h4: TextStyle(
            color: MColors.gray1,
          ),
          h5: TextStyle(
            color: MColors.gray1,
          ),
          h6: TextStyle(
            color: MColors.gray1,
          ),
        ),
        data: """
# Moth - Mura
MUNI OpenSource Tutoring Helper - Masaryk University Repository Analyzer

This tool was created as a part of the thesis *"Measuring Software Development Contributions using Git"* thesis at Masaryk University.
The goal of this tool is to analyze git repositories of students and provide useful information to tutor about their work.

The implementation is originally written in Python 3.9 and uses the following libraries without which the tool would not be possible:
- [Levenshtein](https://pypi.org/project/python-Levenshtein/) - for calculating Levenshtein distance for syntactic analysis
- [GitPython](https://gitpython.readthedocs.io/en/stable/) - for git operations
- [python-gitlab](https://python-gitlab.readthedocs.io/en/stable/) - for interfacing with GitLab
- [PyGithub](https://pygithub.readthedocs.io/en/latest/) - for interfacing with GitHub
- [matplotlib](https://matplotlib.org/) - for plotting various graphs
- [notebook](https://jupyter.org/) - for the front-end you are currently using
- [python-sonarqube-api](https://python-sonarqube-api.readthedocs.io/) - for interfacing with SonarQube Community Edition
- [docker](https://www.docker.com/) - for managing docker containers for SonarQube
- [Unidecode](https://pypi.org/project/Unidecode/) - for converting unicode characters to ASCII - user for contributor name normalization

You are currently using the Flutter frontend.
- [flutter_markdown](https://pub.dev/packages/flutter_markdown) - for rendering this page
- [url_launcher](https://pub.dev/packages/url_launcher) - for opening links in browser
- [provider](https://pub.dev/packages/provider) - for state management
- [file_picker](https://pub.dev/packages/file_picker) - for native file/folder pickers
- [path](https://pub.dev/packages/path) - for path manipulation
- [shared_preferences](https://pub.dev/packages/shared_preferences) - for storing configuration
- [fluent_ui](https://pub.dev/packages/fluent_ui) - for Windows Fluent UI look for some widgets
""",
      ),
    );
  }
}
