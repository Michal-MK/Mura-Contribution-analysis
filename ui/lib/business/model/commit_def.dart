class CommitDef {
// "Commit: 00f0e3eae41fcb00348f5b3426452f5bea566b5a - Msg: "Initial commit" by 👨‍💻 Jan Bartošek"
  static final RegExp commitRegex = RegExp(r'Commit: (?<hash>.{40}) - Msg: "(?<message>.*)" - Date: `(?<date>.*)` by 👨‍💻 (?<authorName>.*)', dotAll: true);

  final String authorName;
  final String hash;
  final String message;
  final DateTime date;

  const CommitDef(this.authorName, this.hash, this.message, this.date);

  static CommitDef from(List<String> aliases) {
    var match = commitRegex.firstMatch(aliases.join("\n"));

    return CommitDef(
      match!.namedGroup('authorName')!,
      match.namedGroup('hash')!,
      match.namedGroup('message')!,
      DateTime.parse(match.namedGroup('date')!),
    );
  }
}
